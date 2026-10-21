import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

from db import db
from security import require_roles, restaurant_id_of
from services import whop
from services.entitlements import entitlements, effective_plan, month_key, orders_used
from services.audit import audit

log = logging.getLogger("upxero.billing")
router = APIRouter(tags=["billing"])
admin_only = require_roles("restaurant_admin")
any_staff = require_roles("restaurant_admin", "restaurant_staff")

PRICE_LABEL = "$9.99 USD / month"
RESYNC_AFTER = timedelta(hours=6)
SYNC_COOLDOWN = timedelta(seconds=30)
HANDLED_PREFIXES = ("membership.", "payment.", "refund.")


async def _restaurant(user: dict) -> dict:
    r = await db.restaurants.find_one({"_id": restaurant_id_of(user)})
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant niet gevonden")
    return r


async def _sync_restaurant(r: dict) -> str:
    sub = r.get("subscription") or {}
    if sub.get("whopMembershipId"):
        return await whop.apply_membership(await whop.get_membership(sub["whopMembershipId"]))
    # No webhook yet: look for a membership created from one of this restaurant's checkouts.
    rid = str(r["_id"])
    refs = set(await db.billing_checkouts.distinct("ref", {"restaurantId": rid}))
    if not refs:
        return "none"
    for m in await whop.list_memberships():
        meta = m.get("metadata") or {}
        if meta.get("restaurant_id") == rid and meta.get("checkout_ref") in refs:
            return await whop.apply_membership(await whop.get_membership(m["id"]))
    return "none"


async def _background_resync(rid):
    r = await db.restaurants.find_one({"_id": rid})
    try:
        await _sync_restaurant(r)
    except whop.WhopError:
        pass  # keep last verified state


@router.get("/billing/status")
async def billing_status(background_tasks: BackgroundTasks, user: dict = Depends(admin_only)):
    r = await _restaurant(user)
    rid = str(r["_id"])
    sub = r.get("subscription") or {}
    last = sub.get("lastSyncedAt")
    if (sub.get("whopMembershipId") and whop.api_configured()
            and (not last or datetime.fromisoformat(last) < datetime.now(timezone.utc) - RESYNC_AFTER)):
        background_tasks.add_task(_background_resync, r["_id"])
    plan = effective_plan(r)
    ent = entitlements(r)
    return {
        "plan": plan,
        "legacy": bool(sub.get("legacy")),
        "status": sub.get("whopStatus"),
        "renewalPeriodEnd": sub.get("renewalPeriodEnd"),
        "cancelAtPeriodEnd": bool(sub.get("cancelAtPeriodEnd")),
        "manageUrl": sub.get("manageUrl"),
        "lastSyncedAt": last,
        "price": PRICE_LABEL,
        "entitlements": ent,
        "usage": {
            "month": month_key(),
            "ordersThisMonth": await orders_used(rid),
            "monthlyOrderLimit": ent["max_monthly_orders"],
            "activeProducts": await db.menu_items.count_documents({"restaurantId": rid, "isAvailable": True}),
            "activeProductLimit": ent["max_active_products"],
        },
        "checkoutAvailable": plan == "free" and whop.checkout_configured(),
    }


@router.post("/billing/checkout")
async def start_checkout(user: dict = Depends(admin_only)):
    r = await _restaurant(user)
    if effective_plan(r) != "free":
        raise HTTPException(status_code=400, detail="Dit restaurant heeft al een actief abonnement.")
    if not whop.checkout_configured():
        raise HTTPException(status_code=503, detail="Abonnementen zijn nog niet geconfigureerd.")
    base = os.environ["FRONTEND_URL"].rstrip("/")
    ref = secrets.token_urlsafe(24)
    rid = str(r["_id"])
    await db.billing_checkouts.insert_one({
        "ref": ref, "restaurantId": rid, "userId": str(user["_id"]),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    try:
        data = await whop.create_checkout(rid, ref, f"{base}/dashboard/abonnement?checkout=done")
    except whop.WhopError:
        await db.billing_checkouts.delete_one({"ref": ref})
        raise HTTPException(status_code=502, detail="Afrekenen bij Whop is momenteel niet beschikbaar. Probeer het later opnieuw.")
    await db.billing_checkouts.update_one({"ref": ref}, {"$set": {"whopCheckoutId": data.get("id")}})
    await audit(user, r["_id"], "subscription.checkout_started")
    return {"purchaseUrl": data.get("purchase_url")}


@router.post("/billing/sync")
async def sync_now(user: dict = Depends(admin_only)):
    r = await _restaurant(user)
    if not whop.api_configured():
        raise HTTPException(status_code=503, detail="Abonnementen zijn nog niet geconfigureerd.")
    now = datetime.now(timezone.utc)
    claimed = await db.restaurants.update_one(
        {"_id": r["_id"], "$or": [{"billingSyncRequestedAt": None},
                                  {"billingSyncRequestedAt": {"$lt": (now - SYNC_COOLDOWN).isoformat()}}]},
        {"$set": {"billingSyncRequestedAt": now.isoformat()}},
    )
    if claimed.modified_count == 0:
        raise HTTPException(status_code=429, detail="Te veel verzoeken. Probeer het over een paar minuten opnieuw.")
    try:
        result = await _sync_restaurant(r)
    except whop.WhopError:
        raise HTTPException(status_code=502, detail="Whop is momenteel niet bereikbaar. Probeer het later opnieuw.")
    r = await db.restaurants.find_one({"_id": r["_id"]})
    return {"result": result, "plan": effective_plan(r)}


@router.post("/webhooks/whop")
async def whop_webhook(request: Request):
    raw = await request.body()
    if not whop.cfg("WHOP_WEBHOOK_SECRET"):
        return JSONResponse({"detail": "not configured"}, status_code=503)
    try:
        whop.verify_webhook(raw, request.headers)
    except ValueError:
        return JSONResponse({"detail": "invalid signature"}, status_code=400)
    import json
    try:
        event = json.loads(raw)
    except ValueError:
        return JSONResponse({"detail": "invalid body"}, status_code=400)
    wid = request.headers.get("webhook-id")
    typ = str(event.get("type", ""))
    try:
        await db.whop_events.insert_one({"_id": wid, "type": typ, "status": "processing",
                                         "receivedAt": datetime.now(timezone.utc).isoformat()})
    except DuplicateKeyError:
        return {"ok": True, "duplicate": True}
    result = "ignored:type"
    if typ.startswith(HANDLED_PREFIXES):
        mid = whop.membership_id_from_event(event)
        result = "ignored:no_membership"
        if mid:
            try:
                result = await whop.apply_membership(await whop.get_membership(mid))
            except whop.WhopError:
                # Let Whop retry later; drop the claim so the retry is processed.
                await db.whop_events.delete_one({"_id": wid})
                return JSONResponse({"detail": "upstream unavailable"}, status_code=503)
    await db.whop_events.update_one({"_id": wid}, {"$set": {"status": "processed", "result": result}})
    return {"ok": True}
