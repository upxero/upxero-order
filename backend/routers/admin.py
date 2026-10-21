import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from models import AdminActiveReq, AdminConfirmReq, AdminLegacyReq, AdminRejectReq, AdminRestaurantReq, ProfileReq
from routers.restaurants import apply_profile_update
from security import hash_password, require_roles
from services.audit import audit
from services.deletion import anonymise_user, delete_restaurant_data, purge_restaurant
from services import whop
from services.entitlements import PRO_STATUSES, effective_plan
from utils import now_iso, oid, serialize, unique_slug

router = APIRouter(prefix="/admin", tags=["admin"])

super_only = require_roles("super_admin")


def _default_hours():
    base = {"closed": False, "open": "11:30", "close": "21:30"}
    return {d: dict(base) for d in
            ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}


@router.get("/restaurants")
async def list_restaurants(user: dict = Depends(super_only)):
    restaurants = await db.restaurants.find({"deletedAt": None}).sort("createdAt", -1).to_list(1000)
    pending = set(await db.deletion_requests.distinct("restaurantId", {"status": "pending"}))
    out = []
    for r in restaurants:
        data = serialize(r)
        data["orderCount"] = await db.orders.count_documents({"restaurantId": str(r["_id"])})
        data["userCount"] = await db.users.count_documents({"restaurantId": str(r["_id"])})
        data["pendingDeletion"] = str(r["_id"]) in pending
        data["plan"] = effective_plan(r)
        out.append(data)
    return out


USER_FIELDS = ("email", "name", "role", "isActive", "createdAt", "deletedAt")
RETENTION_DAYS = int(os.environ["DELETION_RETENTION_DAYS"])


def _purge_eligible_at(r: dict) -> datetime:
    return datetime.fromisoformat(r["deletedAt"]) + timedelta(days=RETENTION_DAYS)


@router.get("/restaurants/archived")
async def archived_restaurants(user: dict = Depends(super_only)):
    rs = await db.restaurants.find({"deletedAt": {"$ne": None}}).sort("deletedAt", -1).to_list(1000)
    now = datetime.now(timezone.utc)
    out = []
    for r in rs:
        eligible = _purge_eligible_at(r)
        out.append({
            "id": str(r["_id"]), "name": r.get("name"), "slug": r.get("slug"),
            "deletedAt": r["deletedAt"], "purgedAt": r.get("purgedAt"),
            "purgeEligibleAt": eligible.isoformat(),
            "canPurge": not r.get("purgedAt") and now >= eligible,
            "orderCount": await db.orders.count_documents({"restaurantId": str(r["_id"])}),
        })
    return {"retentionDays": RETENTION_DAYS, "restaurants": out}


@router.post("/restaurants/{restaurant_id}/purge")
async def purge_archived_restaurant(restaurant_id: str, payload: AdminConfirmReq, user: dict = Depends(super_only)):
    r = await _restaurant_or_404(restaurant_id)
    if not r.get("deletedAt"):
        raise HTTPException(status_code=400, detail="Alleen verwijderde (gearchiveerde) restaurants kunnen definitief worden gewist.")
    if payload.confirmText.strip().lower() != (r.get("name") or "").strip().lower():
        raise HTTPException(status_code=400, detail="De bevestigingstekst komt niet overeen")
    if r.get("purgedAt"):
        return {"message": "Restaurant is al definitief gewist", "alreadyPurged": True}
    if datetime.now(timezone.utc) < _purge_eligible_at(r):
        raise HTTPException(status_code=400, detail="Definitief wissen kan pas na afloop van de bewaartermijn.")
    summary = await purge_restaurant(r)
    await audit(user, r["_id"], "restaurant.purged", summary)
    return {"message": "Restaurant definitief gewist", "summary": summary}


async def _restaurant_or_404(restaurant_id: str) -> dict:
    r = await db.restaurants.find_one({"_id": oid(restaurant_id)})
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant niet gevonden")
    return r


def _not_deleted(r: dict):
    if r.get("deletedAt"):
        raise HTTPException(status_code=400, detail="Dit restaurant is verwijderd en kan niet meer worden gewijzigd.")


@router.get("/restaurants/{restaurant_id}")
async def restaurant_detail(restaurant_id: str, user: dict = Depends(super_only)):
    r = await _restaurant_or_404(restaurant_id)
    rid = str(r["_id"])
    users = await db.users.find({"restaurantId": rid}).sort("createdAt", 1).to_list(500)
    safe_users = [
        {"id": str(u["_id"]), **{k: u.get(k) for k in USER_FIELDS}, "emailVerified": u.get("emailVerified", True)}
        for u in users
    ]
    owner = next((u for u in safe_users if u["role"] == "restaurant_admin" and not u.get("deletedAt")), None)
    requests = await db.deletion_requests.find({"restaurantId": rid}).sort("createdAt", -1).to_list(100)
    logs = await db.audit_logs.find({"restaurantId": rid}).sort("createdAt", -1).to_list(50)
    return {
        "restaurant": serialize(r),
        "plan": effective_plan(r),
        "owner": owner,
        "users": safe_users,
        "orderCount": await db.orders.count_documents({"restaurantId": rid}),
        "deletionRequests": [serialize(x) for x in requests],
        "auditLog": [serialize(x) for x in logs],
    }


@router.patch("/restaurants/{restaurant_id}/legacy")
async def set_legacy_plan(restaurant_id: str, payload: AdminLegacyReq, user: dict = Depends(super_only)):
    r = await _restaurant_or_404(restaurant_id)
    _not_deleted(r)
    sub = r.get("subscription") or {}
    if payload.legacy and sub.get("whopStatus") in PRO_STATUSES:
        raise HTTPException(status_code=409, detail="Dit restaurant heeft een actief betaald abonnement. Laat dit eerst opzeggen voordat je gratis Pro toekent.")
    if bool(sub.get("legacy")) != payload.legacy:
        await db.restaurants.update_one({"_id": r["_id"]}, {"$set": {"subscription.legacy": payload.legacy}})
        await audit(user, r["_id"], "subscription.legacy_set" if payload.legacy else "subscription.legacy_removed")
    r = await db.restaurants.find_one({"_id": r["_id"]})
    return {"legacy": payload.legacy, "plan": effective_plan(r)}


@router.get("/billing/whop-plans")
async def whop_plans(user: dict = Depends(super_only)):
    if not whop.api_configured():
        raise HTTPException(status_code=503, detail="WHOP_API_KEY ontbreekt in de backendconfiguratie.")
    try:
        plans = await whop.list_plans()
    except whop.WhopError as e:
        raise HTTPException(status_code=502, detail=f"Whop API fout ({e.status}). Controleer de API-sleutelrechten (plan:basic:read).")
    keys = ("id", "title", "plan_type", "billing_period", "renewal_price", "initial_price", "currency", "visibility")
    return [{k: p.get(k) for k in keys} for p in plans]


@router.patch("/restaurants/{restaurant_id}/active")
async def set_restaurant_active(restaurant_id: str, payload: AdminActiveReq, user: dict = Depends(super_only)):
    r = await _restaurant_or_404(restaurant_id)
    _not_deleted(r)
    if r.get("isActive", True) != payload.isActive:
        await db.restaurants.update_one({"_id": r["_id"]}, {"$set": {"isActive": payload.isActive, "updatedAt": now_iso()}})
        await audit(user, r["_id"], "restaurant.activated" if payload.isActive else "restaurant.deactivated")
    return {"isActive": payload.isActive}


@router.put("/restaurants/{restaurant_id}")
async def admin_update_restaurant(restaurant_id: str, payload: ProfileReq, user: dict = Depends(super_only)):
    r = await _restaurant_or_404(restaurant_id)
    _not_deleted(r)
    data = payload.model_dump()
    data.pop("logo", None)
    changed = sorted(k for k, v in data.items() if r.get(k, "") != v)
    updated = await apply_profile_update(r["_id"], data)
    if changed:
        await audit(user, r["_id"], "restaurant.updated", {"fields": changed})
    return updated


async def _pending_request(request_id: str) -> dict:
    doc = await db.deletion_requests.find_one({"_id": oid(request_id), "status": "pending"})
    if not doc:
        raise HTTPException(status_code=404, detail="Geen open verwijderverzoek")
    return doc


@router.post("/deletion-requests/{request_id}/approve")
async def approve_deletion(request_id: str, payload: AdminConfirmReq, user: dict = Depends(super_only)):
    doc = await _pending_request(request_id)
    r = await _restaurant_or_404(doc["restaurantId"])
    if payload.confirmText.strip().lower() != r["name"].strip().lower():
        raise HTTPException(status_code=400, detail="De bevestigingstekst komt niet overeen")
    if doc["type"] == "restaurant":
        summary = await delete_restaurant_data(r["_id"])
    else:
        target = await db.users.find_one({"_id": oid(doc["requestedBy"]), "restaurantId": doc["restaurantId"]})
        if not target or target.get("deletedAt"):
            raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
        others = await db.users.count_documents({
            "restaurantId": doc["restaurantId"], "role": "restaurant_admin", "isActive": True,
            "_id": {"$ne": target["_id"]},
        })
        if others == 0:
            raise HTTPException(status_code=400, detail="Dit is de enige beheerder van het restaurant. Het account kan niet los worden verwijderd.")
        await anonymise_user(target)
        summary = {"usersAnonymised": 1}
    await db.deletion_requests.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "completed", "processedAt": now_iso(), "processedBy": str(user["_id"]), "summary": summary}},
    )
    await audit(user, r["_id"], "deletion.completed", {"type": doc["type"], "requestId": request_id, **summary})
    return {"message": "Verwijdering uitgevoerd", "summary": summary}


@router.post("/deletion-requests/{request_id}/reject")
async def reject_deletion(request_id: str, payload: AdminRejectReq, user: dict = Depends(super_only)):
    doc = await _pending_request(request_id)
    await db.deletion_requests.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "rejected", "processedAt": now_iso(), "processedBy": str(user["_id"]),
                  "rejectReason": (payload.reason or "").strip()}},
    )
    await audit(user, doc["restaurantId"], "deletion.rejected", {"type": doc["type"], "requestId": request_id})
    return {"message": "Verwijderverzoek afgewezen"}


@router.get("/users")
async def list_users(user: dict = Depends(super_only)):
    users = await db.users.find({}).sort("createdAt", -1).to_list(1000)
    return [{"id": str(u["_id"]), **{k: u.get(k) for k in USER_FIELDS}, "restaurantId": u.get("restaurantId"),
             "emailVerified": u.get("emailVerified", True)} for u in users]


@router.post("/restaurants")
async def create_restaurant(payload: AdminRestaurantReq, user: dict = Depends(super_only)):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Dit e-mailadres is al in gebruik")
    slug = await unique_slug(db, payload.restaurantName)
    ts = now_iso()
    restaurant = {
        "name": payload.restaurantName.strip(), "slug": slug, "logo": "", "description": "",
        "phone": "", "email": email, "street": "", "houseNumber": "", "postalCode": "",
        "city": "", "country": "BE", "latitude": None, "longitude": None,
        "openingHours": _default_hours(), "pickupEnabled": True, "deliveryEnabled": False,
        "orderingEnabled": False, "deliveryZones": [], "freeDeliveryEnabled": False,
        "freeDeliveryThreshold": 0, "defaultLanguage": "en", "isActive": True,
        "createdAt": ts, "updatedAt": ts,
    }
    res = await db.restaurants.insert_one(restaurant)
    owner = {
        "email": email, "passwordHash": hash_password(payload.password),
        "name": payload.ownerName.strip(), "role": "restaurant_admin",
        "restaurantId": str(res.inserted_id), "isActive": True, "createdAt": ts, "updatedAt": ts,
    }
    await db.users.insert_one(owner)
    restaurant["_id"] = res.inserted_id
    await audit(user, res.inserted_id, "restaurant.created", {"ownerEmail": email})
    return serialize(restaurant)
