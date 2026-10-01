import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from db import db
from models import (DeliveryReq, InviteStaffReq, OpeningHoursReq, ProfileReq,
                    SettingsReq, StaffActiveReq)
from security import require_roles, restaurant_id_of
from services.distance import geocode
from services.email import send_staff_invitation_email
from utils import now_iso, oid, serialize

router = APIRouter(prefix="/restaurant", tags=["restaurant"])

admin_only = require_roles("restaurant_admin")
any_staff = require_roles("restaurant_admin", "restaurant_staff")


@router.get("/me")
async def my_restaurant(user: dict = Depends(any_staff)):
    r = await db.restaurants.find_one({"_id": restaurant_id_of(user)})
    return serialize(r)


@router.put("/profile")
async def update_profile(payload: ProfileReq, user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    data = payload.model_dump()
    # Geocode the restaurant address once when it changes.
    current = await db.restaurants.find_one({"_id": rid})
    addr = f"{data['street']} {data['houseNumber']}, {data['postalCode']} {data['city']}, {data['country']}"
    addr_changed = any(
        current.get(k, "") != data.get(k, "")
        for k in ("street", "houseNumber", "postalCode", "city")
    )
    if addr_changed and data["street"] and data["city"]:
        coords = await geocode(addr)
        if coords:
            data["latitude"], data["longitude"] = coords
    data["updatedAt"] = now_iso()
    await db.restaurants.update_one({"_id": rid}, {"$set": data})
    r = await db.restaurants.find_one({"_id": rid})
    return serialize(r)


@router.put("/delivery")
async def update_delivery(payload: DeliveryReq, user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    zones = [z.model_dump() for z in payload.zones]
    for i, z in enumerate(zones):
        if not z.get("id"):
            z["id"] = f"zone-{i+1}"
        if z["maxDistance"] <= z["minDistance"]:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Maximale afstand moet groter zijn dan minimale afstand")
    data = {
        "deliveryEnabled": payload.deliveryEnabled,
        "deliveryZones": zones,
        "freeDeliveryEnabled": payload.freeDeliveryEnabled,
        "freeDeliveryThreshold": round(float(payload.freeDeliveryThreshold), 2),
        "updatedAt": now_iso(),
    }
    await db.restaurants.update_one({"_id": rid}, {"$set": data})
    r = await db.restaurants.find_one({"_id": rid})
    return serialize(r)


@router.put("/opening-hours")
async def update_hours(payload: OpeningHoursReq, user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    hours = {day: getattr(payload, day).model_dump() for day in
             ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
    await db.restaurants.update_one({"_id": rid}, {"$set": {"openingHours": hours, "updatedAt": now_iso()}})
    r = await db.restaurants.find_one({"_id": rid})
    return serialize(r)


@router.put("/settings")
async def update_settings(payload: SettingsReq, user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    await db.restaurants.update_one(
        {"_id": rid},
        {"$set": {"orderingEnabled": payload.orderingEnabled,
                  "pickupEnabled": payload.pickupEnabled,
                  "orderEmailsEnabled": payload.orderEmailsEnabled,
                  "updatedAt": now_iso()}},
    )
    r = await db.restaurants.find_one({"_id": rid})
    return serialize(r)


# ---------- Staff management (restaurant_admin only, tenant-scoped) ----------

INVITE_DAYS = 7


@router.get("/staff")
async def list_staff(user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    now = datetime.now(timezone.utc)
    users = await db.users.find(
        {"restaurantId": rid, "role": "restaurant_staff"}
    ).sort("createdAt", -1).to_list(500)
    staff = []
    for u in users:
        d = serialize(u)
        d.pop("passwordHash", None)
        staff.append(d)
    invs = await db.staff_invitations.find(
        {"restaurantId": rid, "used": False, "revoked": False, "expires_at": {"$gt": now}}
    ).sort("createdAt", -1).to_list(500)
    invitations = [
        {"id": str(i["_id"]), "email": i["email"],
         "createdAt": i.get("createdAt").isoformat() if hasattr(i.get("createdAt"), "isoformat") else i.get("createdAt"),
         "expiresAt": i.get("expires_at").isoformat() if hasattr(i.get("expires_at"), "isoformat") else i.get("expires_at")}
        for i in invs
    ]
    return {"staff": staff, "invitations": invitations}


@router.post("/staff/invite")
async def invite_staff(payload: InviteStaffReq, background_tasks: BackgroundTasks,
                       user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    rid_str = str(rid)
    email = payload.email.lower().strip()

    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Er bestaat al een account met dit e-mailadres.")

    now = datetime.now(timezone.utc)
    # Revoke any earlier pending invite for this email+restaurant (clean re-invite).
    await db.staff_invitations.update_many(
        {"restaurantId": rid_str, "email": email, "used": False, "revoked": False},
        {"$set": {"revoked": True}},
    )
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await db.staff_invitations.insert_one({
        "token_hash": token_hash,
        "restaurantId": rid_str,
        "email": email,
        "invitedBy": str(user["_id"]),
        "role": "restaurant_staff",
        "expires_at": now + timedelta(days=INVITE_DAYS),
        "used": False,
        "revoked": False,
        "createdAt": now,
    })
    r = await db.restaurants.find_one({"_id": rid})
    background_tasks.add_task(send_staff_invitation_email, email, token, r["name"], user.get("name", ""))
    return {"message": "Uitnodiging verstuurd.", "email": email}


@router.patch("/staff/{user_id}/active")
async def set_staff_active(user_id: str, payload: StaffActiveReq, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    target = await db.users.find_one(
        {"_id": oid(user_id), "restaurantId": rid, "role": "restaurant_staff"}
    )
    if not target:
        raise HTTPException(status_code=404, detail="Medewerker niet gevonden")
    update = {"$set": {"isActive": payload.isActive, "updatedAt": now_iso()}}
    if not payload.isActive:
        # Deactivation invalidates existing staff sessions immediately.
        update["$inc"] = {"tokenVersion": 1}
    await db.users.update_one({"_id": oid(user_id), "restaurantId": rid}, update)
    updated = await db.users.find_one({"_id": oid(user_id)})
    d = serialize(updated)
    d.pop("passwordHash", None)
    return d


@router.delete("/staff/invitations/{invitation_id}")
async def revoke_invitation(invitation_id: str, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    result = await db.staff_invitations.update_one(
        {"_id": oid(invitation_id), "restaurantId": rid, "used": False},
        {"$set": {"revoked": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Uitnodiging niet gevonden")
    return {"message": "Uitnodiging ingetrokken."}
