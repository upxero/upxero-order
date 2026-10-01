from fastapi import APIRouter, Depends, HTTPException

from db import db
from models import AdminRestaurantReq
from security import hash_password, require_roles
from utils import now_iso, serialize, unique_slug

router = APIRouter(prefix="/admin", tags=["admin"])

super_only = require_roles("super_admin")


def _default_hours():
    base = {"closed": False, "open": "11:30", "close": "21:30"}
    return {d: dict(base) for d in
            ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}


@router.get("/restaurants")
async def list_restaurants(user: dict = Depends(super_only)):
    restaurants = await db.restaurants.find({}).sort("createdAt", -1).to_list(1000)
    out = []
    for r in restaurants:
        data = serialize(r)
        data["orderCount"] = await db.orders.count_documents({"restaurantId": str(r["_id"])})
        data["userCount"] = await db.users.count_documents({"restaurantId": str(r["_id"])})
        out.append(data)
    return out


@router.get("/users")
async def list_users(user: dict = Depends(super_only)):
    users = await db.users.find({}).sort("createdAt", -1).to_list(1000)
    result = []
    for u in users:
        d = serialize(u)
        d.pop("passwordHash", None)
        result.append(d)
    return result


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
    return serialize(restaurant)
