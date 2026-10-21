"""Central Free/Pro feature entitlements and the concurrency-safe monthly order quota."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from db import db

# All restaurants are in BE/NL; monthly periods use Brussels calendar months.
BILLING_TZ = ZoneInfo("Europe/Brussels")

FREE = {
    "max_active_products": 20,
    "max_monthly_orders": 30,
    "pickup_enabled": True,
    "delivery_enabled": False,
    "delivery_zones_enabled": False,
    "staff_management_enabled": False,
    "restaurant_email_notifications_enabled": False,
    "customer_email_notifications_enabled": False,
    "discounts_enabled": False,
}
PRO = {
    "max_active_products": None,
    "max_monthly_orders": None,
    "pickup_enabled": True,
    "delivery_enabled": True,
    "delivery_zones_enabled": True,
    "staff_management_enabled": True,
    "restaurant_email_notifications_enabled": True,
    "customer_email_notifications_enabled": True,
    "discounts_enabled": True,
}
PLANS = {"free": FREE, "pro": PRO, "legacy": PRO}

# Whop membership statuses that still grant paid access (past_due: Whop is retrying payment).
PRO_STATUSES = {"trialing", "active", "past_due", "canceling"}


def effective_plan(r: dict) -> str:
    sub = (r or {}).get("subscription") or {}
    if sub.get("legacy"):
        return "legacy"
    if sub.get("whopStatus") in PRO_STATUSES:
        return "pro"
    return "free"


def entitlements(r: dict) -> dict:
    return PLANS[effective_plan(r)]


def has(r: dict, feature: str) -> bool:
    return bool(entitlements(r)[feature])


def require(r: dict, feature: str, detail: str) -> None:
    if not has(r, feature):
        raise HTTPException(status_code=403, detail=detail)


def month_key(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(BILLING_TZ).strftime("%Y-%m")


def _usage_id(rid: str) -> str:
    return f"{rid}:{month_key()}"


async def orders_used(rid: str) -> int:
    doc = await db.order_usage.find_one({"_id": _usage_id(rid)})
    return int(doc["count"]) if doc else 0


async def monthly_limit_reached(r: dict) -> bool:
    limit = entitlements(r)["max_monthly_orders"]
    return limit is not None and await orders_used(str(r["_id"])) >= limit


LIMIT_MSG = "Dit restaurant kan deze maand geen online bestellingen meer ontvangen."


async def reserve_order_slot(r: dict) -> str | None:
    """Atomically count one order (all plans); on Free refuse once the monthly limit is used."""
    limit = entitlements(r)["max_monthly_orders"]
    rid = str(r["_id"])
    uid = _usage_id(rid)
    on_insert = {"restaurantId": rid, "month": uid.split(":")[1]}
    if limit is None:
        await db.order_usage.update_one({"_id": uid}, {"$inc": {"count": 1}, "$setOnInsert": on_insert}, upsert=True)
        return uid
    try:
        await db.order_usage.update_one({"_id": uid}, {"$setOnInsert": {**on_insert, "count": 0}}, upsert=True)
    except DuplicateKeyError:
        pass  # created concurrently
    # Conditional, non-upsert increment: only succeeds while count < limit.
    doc = await db.order_usage.find_one_and_update(
        {"_id": uid, "count": {"$lt": limit}}, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=409, detail=LIMIT_MSG)
    return uid


async def release_order_slot(uid: str | None) -> None:
    if uid:
        await db.order_usage.update_one({"_id": uid, "count": {"$gt": 0}}, {"$inc": {"count": -1}})


PRODUCT_LIMIT_MSG = ("Het Free-abonnement staat maximaal 20 actieve producten toe. "
                     "Upgrade naar Pro of zet eerst een ander product uit.")


async def assert_can_activate_product(r: dict) -> None:
    limit = entitlements(r)["max_active_products"]
    if limit is None:
        return
    active = await db.menu_items.count_documents({"restaurantId": str(r["_id"]), "isAvailable": True})
    if active >= limit:
        raise HTTPException(status_code=403, detail=PRODUCT_LIMIT_MSG)
