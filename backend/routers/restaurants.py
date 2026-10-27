import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from fastapi import (APIRouter, BackgroundTasks, Depends, File, HTTPException,
                     UploadFile)

from db import db
from models import (DeletionRequestReq, DeliveryReq, InviteStaffReq,
                    OpeningHoursReq, ProfileReq, SettingsReq, StaffActiveReq)
from security import require_roles, restaurant_id_of, verify_password
from services.audit import audit
from services.distance import geocode
from services.email import send_staff_invitation_email
from services.entitlements import effective_plan, require
from services.storage import (IMAGE_MIMES, MENU_FILE_MIMES, delete_file,
                              save_upload)
from utils import now_iso, oid, serialize

router = APIRouter(prefix="/restaurant", tags=["restaurant"])

admin_only = require_roles("restaurant_admin")
any_staff = require_roles("restaurant_admin", "restaurant_staff")


@router.get("/me")
async def my_restaurant(user: dict = Depends(any_staff)):
    r = await db.restaurants.find_one({"_id": restaurant_id_of(user)})
    d = serialize(r)
    d["plan"] = effective_plan(r)
    return d


@router.put("/profile")
async def update_profile(payload: ProfileReq, user: dict = Depends(admin_only)):
    return await apply_profile_update(restaurant_id_of(user), payload.model_dump())


async def apply_profile_update(rid, data: dict) -> dict:
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


# ---------- Logo (restaurant_admin only, GridFS, 5 MB images) ----------

LOGO_MAX = 5 * 1024 * 1024
MENU_FILE_MAX = 10 * 1024 * 1024


@router.post("/logo")
async def upload_logo(file: UploadFile = File(...), user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    file_id, _ = await save_upload(file, rid, "logo", IMAGE_MIMES, LOGO_MAX)
    r = await db.restaurants.find_one({"_id": rid})
    old = r.get("logoFileId") if r else None
    await db.restaurants.update_one({"_id": rid}, {"$set": {"logoFileId": file_id, "updatedAt": now_iso()}})
    if old and old != file_id:
        await delete_file(old)
    return {"message": "Logo geüpload.", "logoFileId": file_id}


@router.delete("/logo")
async def remove_logo(user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    r = await db.restaurants.find_one({"_id": rid})
    old = r.get("logoFileId") if r else None
    await db.restaurants.update_one({"_id": rid}, {"$unset": {"logoFileId": ""}, "$set": {"updatedAt": now_iso()}})
    if old:
        await delete_file(old)
    return {"message": "Logo verwijderd."}

# ---------- Restaurant cover image (JPG/PNG/WebP, 5 MB) ----------

@router.post("/cover")
async def upload_cover(file: UploadFile = File(...), user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)

    file_id, _ = await save_upload(
        file, rid, "cover", IMAGE_MIMES, LOGO_MAX
    )

    r = await db.restaurants.find_one({"_id": rid})
    old = r.get("coverFileId") if r else None

    await db.restaurants.update_one(
        {"_id": rid},
        {"$set": {
            "coverFileId": file_id,
            "updatedAt": now_iso()
        }}
    )

    if old and old != file_id:
        await delete_file(old)

    return {
        "message": "Omslagfoto geüpload.",
        "coverFileId": file_id
    }


@router.delete("/cover")
async def remove_cover(user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)

    r = await db.restaurants.find_one({"_id": rid})
    old = r.get("coverFileId") if r else None

    await db.restaurants.update_one(
        {"_id": rid},
        {
            "$unset": {"coverFileId": ""},
            "$set": {"updatedAt": now_iso()}
        }
    )

    if old:
        await delete_file(old)

    return {"message": "Omslagfoto verwijderd."}
# ---------- Menu file (PDF/JPG/PNG, 10 MB) ----------


@router.post("/menu-file")
async def upload_menu_file(file: UploadFile = File(...), user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    file_id, meta = await save_upload(file, rid, "menu_file", MENU_FILE_MIMES, MENU_FILE_MAX)
    r = await db.restaurants.find_one({"_id": rid})
    old = r.get("menuFileId") if r else None
    await db.restaurants.update_one({"_id": rid}, {"$set": {
        "menuFileId": file_id,
        "menuFileName": meta["originalFilename"] or "menukaart",
        "menuFileType": meta["contentType"],
        "updatedAt": now_iso(),
    }})
    if old and old != file_id:
        await delete_file(old)
    return {"message": "Menukaart geüpload.", "menuFileId": file_id,
            "menuFileName": meta["originalFilename"], "menuFileType": meta["contentType"]}


@router.delete("/menu-file")
async def remove_menu_file(user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    r = await db.restaurants.find_one({"_id": rid})
    old = r.get("menuFileId") if r else None
    await db.restaurants.update_one(
        {"_id": rid},
        {"$unset": {"menuFileId": "", "menuFileName": "", "menuFileType": ""}, "$set": {"updatedAt": now_iso()}},
    )
    if old:
        await delete_file(old)
    return {"message": "Menukaart verwijderd."}


@router.put("/delivery")
async def update_delivery(payload: DeliveryReq, user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    require(await db.restaurants.find_one({"_id": rid}), "delivery_zones_enabled", PRO_DELIVERY_MSG)
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
                  "customerEmailsEnabled": payload.customerEmailsEnabled,
                  "updatedAt": now_iso()}},
    )
    r = await db.restaurants.find_one({"_id": rid})
    return serialize(r)


# ---------- Staff management (restaurant_admin only, tenant-scoped) ----------

INVITE_DAYS = 7
PRO_DELIVERY_MSG = "Bezorging is beschikbaar met Upxero Ordering Pro."
PRO_STAFF_MSG = "Personeelsbeheer is beschikbaar met Upxero Ordering Pro."


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
    require(await db.restaurants.find_one({"_id": rid}), "staff_management_enabled", PRO_STAFF_MSG)

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
    background_tasks.add_task(send_staff_invitation_email, email, token, r["name"], user.get("name", ""), r.get("defaultLanguage") or "en")
    return {"message": "Uitnodiging verstuurd.", "email": email}


@router.patch("/staff/{user_id}/active")
async def set_staff_active(user_id: str, payload: StaffActiveReq, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    target = await db.users.find_one(
        {"_id": oid(user_id), "restaurantId": rid, "role": "restaurant_staff"}
    )
    if not target:
        raise HTTPException(status_code=404, detail="Medewerker niet gevonden")
    if payload.isActive:
        require(await db.restaurants.find_one({"_id": oid(rid)}), "staff_management_enabled", PRO_STAFF_MSG)
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


# ---------- Deletion requests (owner side; processed by platform admin) ----------

@router.get("/deletion-request")
async def my_deletion_request(user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    doc = await db.deletion_requests.find_one({"restaurantId": rid, "status": "pending"})
    return {"request": serialize(doc) if doc else None}


@router.post("/deletion-request")
async def request_deletion(payload: DeletionRequestReq, user: dict = Depends(admin_only)):
    rid = restaurant_id_of(user)
    r = await db.restaurants.find_one({"_id": rid})
    if not verify_password(payload.password, user.get("passwordHash", "")):
        raise HTTPException(status_code=400, detail="Wachtwoord is onjuist")
    expected = r["name"] if payload.type == "restaurant" else user["email"]
    if payload.confirmText.strip().lower() != expected.strip().lower():
        raise HTTPException(status_code=400, detail="De bevestigingstekst komt niet overeen")
    if await db.deletion_requests.find_one({"restaurantId": str(rid), "status": "pending"}):
        raise HTTPException(status_code=400, detail="Er staat al een verwijderverzoek open")
    if payload.type == "account":
        others = await db.users.count_documents({
            "restaurantId": str(rid), "role": "restaurant_admin", "isActive": True, "_id": {"$ne": user["_id"]},
        })
        if others == 0:
            raise HTTPException(status_code=400, detail="Je bent de enige beheerder van dit restaurant. Vraag in plaats daarvan sluiting van het restaurant aan.")
    doc = {
        "restaurantId": str(rid),
        "restaurantName": r["name"],
        "type": payload.type,
        "reason": (payload.reason or "").strip(),
        "requestedBy": str(user["_id"]),
        "requestedByEmail": user["email"],
        "status": "pending",
        "createdAt": now_iso(),
    }
    try:
        res = await db.deletion_requests.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Er staat al een verwijderverzoek open")
    doc["_id"] = res.inserted_id
    await audit(user, rid, "deletion.requested", {"type": payload.type, "requestId": str(res.inserted_id)})
    return {"request": serialize(doc)}


@router.delete("/deletion-request")
async def cancel_deletion_request(user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    doc = await db.deletion_requests.find_one_and_update(
        {"restaurantId": rid, "status": "pending"},
        {"$set": {"status": "cancelled", "processedAt": now_iso()}},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Geen open verwijderverzoek")
    await audit(user, rid, "deletion.cancelled", {"type": doc["type"], "requestId": str(doc["_id"])})
    return {"message": "Verwijderverzoek ingetrokken"}
