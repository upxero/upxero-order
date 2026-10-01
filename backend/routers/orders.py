from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from db import db
from models import EtaReq, StatusReq
from security import require_roles, restaurant_id_of
from services.email import (send_order_eta_customer_email,
                            send_order_status_customer_email)
from services.notifications import notify_status_change
from utils import derive_status_token, now_iso, oid, serialize

router = APIRouter(prefix="/orders", tags=["orders"])

any_staff = require_roles("restaurant_admin", "restaurant_staff")
admin_only = require_roles("restaurant_admin")

STATUSES = ["new", "accepted", "preparing", "ready", "completed", "cancelled"]
DELETABLE = {"completed", "cancelled"}
TRANSITIONS = {
    "new": ["accepted", "cancelled"],
    "accepted": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}
CUSTOMER_NOTIFY = {"accepted", "preparing", "ready", "completed", "cancelled"}
ETA_EDITABLE = {"accepted", "preparing", "ready"}


def _valid_minutes(v) -> bool:
    return isinstance(v, int) and 1 <= v <= 600


def _clean(order: dict) -> dict:
    d = serialize(order)
    d.pop("statusToken", None)
    d.pop("statusTokenHash", None)
    return d


async def _notify_customer(background_tasks, order, restaurant, kind="status"):
    email = ((order.get("customer") or {}).get("email") or "").strip()
    if not (email and restaurant.get("customerEmailsEnabled", True)):
        return
    # Legacy orders carry a plaintext token; new orders derive it from the id.
    token = order.get("statusToken") or derive_status_token(str(order["_id"]))
    lang = restaurant.get("defaultLanguage", "nl")
    fn = send_order_eta_customer_email if kind == "eta" else send_order_status_customer_email
    background_tasks.add_task(fn, email, restaurant["name"], serialize(order), token, lang)


@router.get("")
async def list_orders(status: str = None, user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    query = {"restaurantId": rid}
    if status and status in STATUSES:
        query["status"] = status
    orders = await db.orders.find(query).sort("createdAt", -1).to_list(500)
    return [_clean(o) for o in orders]


@router.get("/stats")
async def stats(user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today = await db.orders.count_documents({"restaurantId": rid, "createdAt": {"$gte": start}})
    new_count = await db.orders.count_documents({"restaurantId": rid, "status": "new"})
    active = await db.orders.count_documents(
        {"restaurantId": rid, "status": {"$in": ["accepted", "preparing", "ready"]}}
    )
    completed_today = await db.orders.count_documents(
        {"restaurantId": rid, "status": "completed", "createdAt": {"$gte": start}}
    )
    r = await db.restaurants.find_one({"_id": restaurant_id_of(user)})
    return {
        "ordersToday": today,
        "newOrders": new_count,
        "activeOrders": active,
        "completedToday": completed_today,
        "orderingEnabled": r.get("orderingEnabled", False),
        "pickupEnabled": r.get("pickupEnabled", False),
        "deliveryEnabled": r.get("deliveryEnabled", False),
    }


@router.get("/{order_id}")
async def get_order(order_id: str, user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    order = await db.orders.find_one({"_id": oid(order_id), "restaurantId": rid})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    return _clean(order)


@router.patch("/{order_id}/status")
async def update_status(order_id: str, payload: StatusReq, background_tasks: BackgroundTasks,
                        user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    if payload.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Ongeldige status")
    order = await db.orders.find_one({"_id": oid(order_id), "restaurantId": rid})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    current = order.get("status", "new")
    if payload.status != current and payload.status not in TRANSITIONS.get(current, []):
        raise HTTPException(status_code=400, detail="Deze statuswijziging is niet toegestaan")

    set_fields = {"status": payload.status, "updatedAt": now_iso()}
    if payload.status == "accepted" and payload.estimatedMinutes is not None:
        set_fields["estimatedMinutes"] = int(payload.estimatedMinutes)

    await db.orders.update_one({"_id": oid(order_id)}, {"$set": set_fields})
    await notify_status_change(rid, order.get("orderNumber"), payload.status)
    updated = await db.orders.find_one({"_id": oid(order_id)})
    if payload.status in CUSTOMER_NOTIFY and payload.status != current:
        restaurant = await db.restaurants.find_one({"_id": restaurant_id_of(user)})
        await _notify_customer(background_tasks, updated, restaurant, kind="status")
    return _clean(updated)


@router.patch("/{order_id}/eta")
async def update_eta(order_id: str, payload: EtaReq, background_tasks: BackgroundTasks,
                     user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    order = await db.orders.find_one({"_id": oid(order_id), "restaurantId": rid})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    if order.get("status") not in ETA_EDITABLE:
        raise HTTPException(status_code=400, detail="Tijd kan alleen worden aangepast voor actieve bestellingen.")
    new_eta = int(payload.estimatedMinutes)
    changed = new_eta != order.get("estimatedMinutes")
    await db.orders.update_one({"_id": oid(order_id)}, {"$set": {"estimatedMinutes": new_eta, "updatedAt": now_iso()}})
    updated = await db.orders.find_one({"_id": oid(order_id)})
    if changed:
        restaurant = await db.restaurants.find_one({"_id": restaurant_id_of(user)})
        await _notify_customer(background_tasks, updated, restaurant, kind="eta")
    return _clean(updated)


@router.delete("/{order_id}")
async def delete_order(order_id: str, user: dict = Depends(admin_only)):
    """Permanently delete a finished order (admin-only, tenant-scoped).

    Only completed/cancelled orders are removable; active orders are protected.
    Order numbers come from an $inc counter, so deletion never reuses/resets them.
    After deletion the customer status link no longer resolves (order is gone).
    """
    rid = str(restaurant_id_of(user))
    order = await db.orders.find_one({"_id": oid(order_id), "restaurantId": rid})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    if order.get("status") not in DELETABLE:
        raise HTTPException(
            status_code=400,
            detail="Alleen afgeronde of geannuleerde bestellingen kunnen worden verwijderd.",
        )
    await db.orders.delete_one({"_id": oid(order_id), "restaurantId": rid})
    return {"message": "Bestelling verwijderd"}
