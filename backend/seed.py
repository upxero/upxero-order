"""Seed a super admin and a demo restaurant with a full menu so the entire
order flow can be exercised immediately. Idempotent: safe to run on every boot."""
import os
import uuid

from db import db
from security import hash_password, verify_password
from utils import now_iso, slugify

DEMO_EMAIL = "owner@demo.upxero.com"
DEMO_PASSWORD = "Demo!2025"
DEMO_SLUG = "bistro-demo"


async def seed_data():
    await _seed_super_admin()
    await _seed_demo_restaurant()
    await _write_credentials()


async def _seed_super_admin():
    email = os.environ.get("ADMIN_EMAIL", "admin@upxero.com").lower()
    password = os.environ.get("ADMIN_PASSWORD", "Upxero!Admin2025")
    existing = await db.users.find_one({"email": email})
    ts = now_iso()
    if not existing:
        await db.users.insert_one({
            "email": email, "passwordHash": hash_password(password), "name": "Upxero Admin",
            "role": "super_admin", "restaurantId": None, "isActive": True,
            "createdAt": ts, "updatedAt": ts,
        })
    elif not verify_password(password, existing.get("passwordHash", "")):
        await db.users.update_one({"email": email}, {"$set": {"passwordHash": hash_password(password)}})


def _hours():
    base = {"closed": False, "open": "11:30", "close": "22:00"}
    return {
        "monday": {"closed": True, "open": "11:30", "close": "22:00"},
        "tuesday": dict(base), "wednesday": dict(base), "thursday": dict(base),
        "friday": {"closed": False, "open": "11:30", "close": "23:00"},
        "saturday": {"closed": False, "open": "12:00", "close": "23:00"},
        "sunday": {"closed": False, "open": "00:00", "close": "23:59"},
    }


async def _seed_demo_restaurant():
    if await db.restaurants.find_one({"slug": DEMO_SLUG}):
        return
    ts = now_iso()
    restaurant = {
        "name": "Bistro Demo", "slug": DEMO_SLUG, "logo": "",
        "description": "Verse burgers, frietjes en Belgische klassiekers. Bestel eenvoudig online voor afhalen of bezorgen.",
        "phone": "+32 2 123 45 67", "email": DEMO_EMAIL,
        "street": "Grote Markt", "houseNumber": "1", "postalCode": "1000", "city": "Brussel", "country": "BE",
        "latitude": 50.8467, "longitude": 4.3525,
        "openingHours": _hours(),
        "pickupEnabled": True, "deliveryEnabled": True, "orderingEnabled": True,
        "deliveryZones": [
            {"id": "zone-1", "minDistance": 0, "maxDistance": 3, "deliveryFee": 2.0, "minimumOrderAmount": 15.0, "enabled": True},
            {"id": "zone-2", "minDistance": 3, "maxDistance": 5, "deliveryFee": 3.5, "minimumOrderAmount": 20.0, "enabled": True},
            {"id": "zone-3", "minDistance": 5, "maxDistance": 8, "deliveryFee": 5.0, "minimumOrderAmount": 25.0, "enabled": True},
            {"id": "zone-4", "minDistance": 8, "maxDistance": 10, "deliveryFee": 7.5, "minimumOrderAmount": 35.0, "enabled": True},
        ],
        "freeDeliveryEnabled": True, "freeDeliveryThreshold": 40.0,
        "defaultLanguage": "nl", "isActive": True, "createdAt": ts, "updatedAt": ts,
    }
    res = await db.restaurants.insert_one(restaurant)
    rid = str(res.inserted_id)

    await db.users.insert_one({
        "email": DEMO_EMAIL, "passwordHash": hash_password(DEMO_PASSWORD), "name": "Demo Eigenaar",
        "role": "restaurant_admin", "restaurantId": rid, "isActive": True, "createdAt": ts, "updatedAt": ts,
    })
    await db.users.insert_one({
        "email": "staff@demo.upxero.com", "passwordHash": hash_password(DEMO_PASSWORD), "name": "Demo Medewerker",
        "role": "restaurant_staff", "restaurantId": rid, "isActive": True, "createdAt": ts, "updatedAt": ts,
    })

    cats = [
        {"name": "Burgers", "description": "Vers gebakken burgers", "sortOrder": 1},
        {"name": "Frietjes & Snacks", "description": "Krokante Belgische frieten", "sortOrder": 2},
        {"name": "Dranken", "description": "Frisdranken en meer", "sortOrder": 3},
    ]
    cat_ids = {}
    for c in cats:
        r = await db.menu_categories.insert_one({**c, "restaurantId": rid, "isActive": True, "createdAt": ts, "updatedAt": ts})
        cat_ids[c["name"]] = str(r.inserted_id)

    def grp(name, required, multiple, options):
        return {"id": str(uuid.uuid4()), "name": name, "required": required, "multiple": multiple,
                "options": [{"id": str(uuid.uuid4()), "name": n, "price": p} for n, p in options]}

    items = [
        ("Burgers", "Classic Cheeseburger", "Rundvlees, cheddar, sla, tomaat en huisgemaakte saus.", 11.5,
         "https://images.pexels.com/photos/31176091/pexels-photo-31176091.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
         [grp("Extra's", False, True, [("Extra kaas", 1.5), ("Extra vlees", 2.0), ("Spek", 1.5), ("Pittig", 0.5)])]),
        ("Burgers", "Chicken Deluxe", "Krokante kipfilet, ei, sla en mayonaise.", 12.0,
         "https://images.pexels.com/photos/31176105/pexels-photo-31176105.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
         [grp("Saus", True, False, [("Mayonaise", 0.0), ("Ketchup", 0.0), ("Andalouse", 0.5)]),
          grp("Extra's", False, True, [("Extra kaas", 1.5), ("Spek", 1.5)])]),
        ("Frietjes & Snacks", "Belgische Frieten", "Dubbel gebakken frieten met saus naar keuze.", 4.5,
         "https://images.unsplash.com/photo-1600423276591-26d4d93c4830?crop=entropy&cs=srgb&fm=jpg&q=85",
         [grp("Formaat", True, False, [("Klein", 0.0), ("Medium", 1.0), ("Groot", 2.0)]),
          grp("Saus", False, True, [("Mayonaise", 0.7), ("Ketchup", 0.7), ("Andalouse", 0.7)])]),
        ("Frietjes & Snacks", "Frikandel Speciaal", "Frikandel met mayonaise, ketchup en ui.", 3.5,
         "https://images.unsplash.com/photo-1644162666704-8c4e38e237db?crop=entropy&cs=srgb&fm=jpg&q=85", []),
        ("Dranken", "Cola", "Blikje 33cl.", 2.5, "", [grp("Keuze", True, False, [("Cola", 0.0), ("Cola Zero", 0.0)])]),
        ("Dranken", "Bruiswater", "Fles 50cl.", 2.0, "", []),
    ]
    for i, (cat, name, desc, price, img, groups) in enumerate(items):
        await db.menu_items.insert_one({
            "restaurantId": rid, "categoryId": cat_ids[cat], "name": name, "description": desc,
            "price": price, "image": img, "optionGroups": groups, "sortOrder": i,
            "isAvailable": True, "createdAt": ts, "updatedAt": ts,
        })


async def _write_credentials():
    try:
        content = f"""# Test Credentials — Upxero Ordering

## Super Admin (Upxero platform)
- Email: {os.environ.get('ADMIN_EMAIL')}
- Wachtwoord: {os.environ.get('ADMIN_PASSWORD')}
- Rol: super_admin

## Demo restaurant admin (Bistro Demo)
- Email: {DEMO_EMAIL}
- Wachtwoord: {DEMO_PASSWORD}
- Rol: restaurant_admin

## Demo restaurant staff
- Email: staff@demo.upxero.com
- Wachtwoord: {DEMO_PASSWORD}
- Rol: restaurant_staff

## Public ordering page
- /order/{DEMO_SLUG}

## Auth endpoints
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET  /api/auth/me
- POST /api/auth/refresh
"""
        with open("/app/memory/test_credentials.md", "w") as f:
            f.write(content)
    except Exception:
        pass
