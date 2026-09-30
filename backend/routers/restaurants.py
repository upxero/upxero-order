from bson import ObjectId
from fastapi import APIRouter, Depends

from db import db
from models import DeliveryReq, OpeningHoursReq, ProfileReq, SettingsReq
from security import require_roles, restaurant_id_of
from services.distance import geocode
from utils import now_iso, serialize

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
                  "pickupEnabled": payload.pickupEnabled, "updatedAt": now_iso()}},
    )
    r = await db.restaurants.find_one({"_id": rid})
    return serialize(r)
