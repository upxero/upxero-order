from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from models import StatusReq
from security import require_roles, restaurant_id_of
from services.notifications import notify_status_change
from utils import now_iso, oid, serialize

router = APIRouter(prefix="/orders", tags=["orders"])

any_staff = require_roles("restaurant_admin", "restaurant_staff")

STATUSES = ["new", "accepted", "preparing", "ready", "completed", "cancelled"]
TRANSITIONS = {
    "new": ["accepted", "cancelled"],
    "accepted": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}


@router.get("")
async def list_orders(status: str = None, user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    query = {"restaurantId": rid}
    if status and status in STATUSES:
        query["status"] = status
    orders = await db.orders.find(query).sort("createdAt", -1).to_list(500)
    return [serialize(o) for o in orders]


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
    return serialize(order)


@router.patch("/{order_id}/status")
async def update_status(order_id: str, payload: StatusReq, user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    if payload.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Ongeldige status")
    order = await db.orders.find_one({"_id": oid(order_id), "restaurantId": rid})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    current = order.get("status", "new")
    if payload.status != current and payload.status not in TRANSITIONS.get(current, []):
        raise HTTPException(status_code=400, detail="Deze statuswijziging is niet toegestaan")
    await db.orders.update_one(
        {"_id": oid(order_id)},
        {"$set": {"status": payload.status, "updatedAt": now_iso()}},
    )
    await notify_status_change(rid, order.get("orderNumber"), payload.status)
    updated = await db.orders.find_one({"_id": oid(order_id)})
    return serialize(updated)
