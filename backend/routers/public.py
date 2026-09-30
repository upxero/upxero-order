from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from zoneinfo import ZoneInfo

from db import db
from models import PublicOrderReq, QuoteReq
from services.distance import geocode, haversine_km
from services.notifications import notify_new_order
from utils import next_order_number, now_iso, oid, serialize

router = APIRouter(prefix="/public", tags=["public"])

TZ = ZoneInfo("Europe/Brussels")
DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def compute_is_open(restaurant: dict) -> bool:
    hours = restaurant.get("openingHours") or {}
    now = datetime.now(TZ)
    day = DAY_KEYS[now.weekday()]
    today = hours.get(day)
    if not today or today.get("closed"):
        return False
    try:
        o_h, o_m = map(int, today["open"].split(":"))
        c_h, c_m = map(int, today["close"].split(":"))
    except (ValueError, KeyError):
        return False
    open_min = o_h * 60 + o_m
    close_min = c_h * 60 + c_m
    cur = now.hour * 60 + now.minute
    if close_min <= open_min:  # crosses midnight
        return cur >= open_min or cur < close_min
    return open_min <= cur < close_min


def _public_restaurant(r: dict) -> dict:
    return {
        "id": str(r["_id"]),
        "name": r["name"],
        "slug": r["slug"],
        "logo": r.get("logo", ""),
        "description": r.get("description", ""),
        "phone": r.get("phone", ""),
        "city": r.get("city", ""),
        "street": r.get("street", ""),
        "houseNumber": r.get("houseNumber", ""),
        "postalCode": r.get("postalCode", ""),
        "openingHours": r.get("openingHours", {}),
        "pickupEnabled": r.get("pickupEnabled", False),
        "deliveryEnabled": r.get("deliveryEnabled", False),
        "orderingEnabled": r.get("orderingEnabled", False),
        "deliveryZones": [z for z in r.get("deliveryZones", []) if z.get("enabled", True)],
        "freeDeliveryEnabled": r.get("freeDeliveryEnabled", False),
        "freeDeliveryThreshold": r.get("freeDeliveryThreshold", 0),
        "defaultLanguage": r.get("defaultLanguage", "nl"),
        "isOpen": compute_is_open(r),
        "hasLocation": r.get("latitude") is not None and r.get("longitude") is not None,
    }


@router.get("/restaurant/{slug}")
async def get_public_restaurant(slug: str):
    r = await db.restaurants.find_one({"slug": slug, "isActive": True})
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant niet gevonden")
    rid = str(r["_id"])
    cats = await db.menu_categories.find({"restaurantId": rid, "isActive": True}).sort("sortOrder", 1).to_list(500)
    items = await db.menu_items.find({"restaurantId": rid}).sort("sortOrder", 1).to_list(1000)
    return {
        "restaurant": _public_restaurant(r),
        "categories": [serialize(c) for c in cats],
        "items": [serialize(i) for i in items],
    }


def _resolve_items(order_items, menu_by_id):
    """Recompute line items server-side from authoritative menu data."""
    snapshot = []
    subtotal = 0.0
    for oi in order_items:
        item = menu_by_id.get(oi.productId)
        if not item:
            raise HTTPException(status_code=400, detail="Een product in je bestelling bestaat niet meer")
        if not item.get("isAvailable", True):
            raise HTTPException(status_code=400, detail=f"'{item['name']}' is momenteel niet beschikbaar")
        unit_price = float(item["price"])
        groups = {g["id"]: g for g in item.get("optionGroups", [])}
        selected_snapshot = []
        option_total = 0.0
        # validate required groups
        chosen_by_group = {}
        for sel in oi.selectedOptions:
            chosen_by_group.setdefault(sel.groupId, []).append(sel.optionId)
        for g in item.get("optionGroups", []):
            chosen = chosen_by_group.get(g["id"], [])
            if g.get("required") and not chosen:
                raise HTTPException(status_code=400, detail=f"Maak een keuze voor '{g['name']}' bij '{item['name']}'")
            if not g.get("multiple") and len(chosen) > 1:
                raise HTTPException(status_code=400, detail=f"Slechts één keuze toegestaan voor '{g['name']}'")
        for sel in oi.selectedOptions:
            g = groups.get(sel.groupId)
            if not g:
                raise HTTPException(status_code=400, detail="Ongeldige optie geselecteerd")
            opt = next((o for o in g["options"] if o["id"] == sel.optionId), None)
            if not opt:
                raise HTTPException(status_code=400, detail="Ongeldige optie geselecteerd")
            option_total += float(opt["price"])
            selected_snapshot.append({
                "groupId": g["id"], "groupName": g["name"],
                "optionId": opt["id"], "optionName": opt["name"], "price": float(opt["price"]),
            })
        line_total = round((unit_price + option_total) * oi.quantity, 2)
        subtotal += line_total
        snapshot.append({
            "productId": oi.productId,
            "productName": item["name"],
            "quantity": oi.quantity,
            "unitPrice": unit_price,
            "selectedOptions": selected_snapshot,
            "optionPrices": round(option_total, 2),
            "lineTotal": line_total,
        })
    return snapshot, round(subtotal, 2)


def _match_zone(zones, distance_km):
    for z in sorted(zones, key=lambda x: x.get("minDistance", 0)):
        if not z.get("enabled", True):
            continue
        if z["minDistance"] <= distance_km <= z["maxDistance"]:
            return z
    return None


@router.post("/restaurant/{slug}/quote")
async def quote_order(slug: str, payload: QuoteReq):
    r = await db.restaurants.find_one({"slug": slug, "isActive": True})
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant niet gevonden")
    rid = str(r["_id"])
    menu = await db.menu_items.find({"restaurantId": rid}).to_list(1000)
    menu_by_id = {str(m["_id"]): m for m in menu}
    _, subtotal = _resolve_items(payload.items, menu_by_id)

    if payload.orderType == "pickup":
        return {"orderType": "pickup", "subtotal": subtotal, "deliveryFee": 0.0,
                "total": subtotal, "available": True}

    if not r.get("deliveryEnabled"):
        raise HTTPException(status_code=400, detail="Bezorgen is niet beschikbaar.")
    if not payload.deliveryAddress:
        raise HTTPException(status_code=400, detail="Bezorgadres is verplicht")
    if r.get("latitude") is None or r.get("longitude") is None:
        raise HTTPException(status_code=409, detail="Bezorging is nog niet geconfigureerd voor dit restaurant.")

    da = payload.deliveryAddress
    addr = f"{da.street} {da.houseNumber}, {da.postalCode} {da.city}, BE"
    coords = await geocode(addr)
    if not coords:
        return {"orderType": "delivery", "subtotal": subtotal, "available": False,
                "message": "We konden dit adres niet vinden. Controleer je adres."}
    distance = round(haversine_km(r["latitude"], r["longitude"], coords[0], coords[1]), 2)
    zone = _match_zone(r.get("deliveryZones", []), distance)
    if not zone:
        return {"orderType": "delivery", "subtotal": subtotal, "distanceKm": distance,
                "available": False, "message": "Helaas bezorgen we niet op dit adres."}
    fee = float(zone["deliveryFee"])
    if r.get("freeDeliveryEnabled") and subtotal >= float(r.get("freeDeliveryThreshold", 0)) > 0:
        fee = 0.0
    below = subtotal < float(zone["minimumOrderAmount"])
    return {
        "orderType": "delivery", "subtotal": subtotal, "deliveryFee": fee,
        "total": round(subtotal + fee, 2), "distanceKm": distance,
        "minimumOrderAmount": float(zone["minimumOrderAmount"]),
        "belowMinimum": below, "available": True,
    }


@router.post("/restaurant/{slug}/orders")
async def create_public_order(slug: str, payload: PublicOrderReq):
    r = await db.restaurants.find_one({"slug": slug, "isActive": True})
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant niet gevonden")
    rid = str(r["_id"])

    # Idempotency: duplicate submission returns the original order.
    if payload.idempotencyKey:
        existing = await db.orders.find_one({"restaurantId": rid, "idempotencyKey": payload.idempotencyKey})
        if existing:
            return serialize(existing)

    if not r.get("orderingEnabled"):
        raise HTTPException(status_code=409, detail="Online bestellen is momenteel niet beschikbaar.")
    if not compute_is_open(r):
        raise HTTPException(status_code=409, detail="Het restaurant is momenteel gesloten.")

    if payload.orderType == "pickup" and not r.get("pickupEnabled"):
        raise HTTPException(status_code=400, detail="Afhalen is niet beschikbaar.")
    if payload.orderType == "delivery" and not r.get("deliveryEnabled"):
        raise HTTPException(status_code=400, detail="Bezorgen is niet beschikbaar.")

    # Authoritative menu
    menu = await db.menu_items.find({"restaurantId": rid}).to_list(1000)
    menu_by_id = {str(m["_id"]): m for m in menu}
    items_snapshot, subtotal = _resolve_items(payload.items, menu_by_id)

    delivery_fee = 0.0
    delivery_zone = None
    delivery_address = None
    distance_km = None

    if payload.orderType == "delivery":
        if not payload.deliveryAddress:
            raise HTTPException(status_code=400, detail="Bezorgadres is verplicht")
        if r.get("latitude") is None or r.get("longitude") is None:
            raise HTTPException(status_code=409, detail="Bezorging is nog niet geconfigureerd voor dit restaurant.")
        da = payload.deliveryAddress
        addr = f"{da.street} {da.houseNumber}, {da.postalCode} {da.city}, BE"
        coords = await geocode(addr)
        if not coords:
            raise HTTPException(status_code=400, detail="We konden dit adres niet vinden. Controleer je adres.")
        distance_km = round(haversine_km(r["latitude"], r["longitude"], coords[0], coords[1]), 2)
        zone = _match_zone(r.get("deliveryZones", []), distance_km)
        if not zone:
            raise HTTPException(status_code=400, detail="Helaas bezorgen we niet op dit adres.")
        if subtotal < float(zone["minimumOrderAmount"]):
            amount = ("%.2f" % zone["minimumOrderAmount"]).replace(".", ",")
            raise HTTPException(
                status_code=400,
                detail=f"Voor bezorging in jouw gebied is een minimum bestelling van €{amount} vereist.",
            )
        delivery_fee = float(zone["deliveryFee"])
        if r.get("freeDeliveryEnabled") and subtotal >= float(r.get("freeDeliveryThreshold", 0)) > 0:
            delivery_fee = 0.0
        delivery_zone = {
            "id": zone.get("id"),
            "minDistance": zone["minDistance"],
            "maxDistance": zone["maxDistance"],
            "deliveryFee": float(zone["deliveryFee"]),
            "appliedFee": delivery_fee,
            "distanceKm": distance_km,
        }
        delivery_address = {**da.model_dump(), "latitude": coords[0], "longitude": coords[1]}

    total = round(subtotal + delivery_fee, 2)
    order_number = await next_order_number(db, rid)
    ts = now_iso()
    order = {
        "restaurantId": rid,
        "orderNumber": order_number,
        "customer": payload.customer.model_dump(),
        "orderType": payload.orderType,
        "items": items_snapshot,
        "subtotal": subtotal,
        "deliveryFee": delivery_fee,
        "deliveryZone": delivery_zone,
        "deliveryAddress": delivery_address,
        "distanceKm": distance_km,
        "notes": (payload.notes or "").strip(),
        "total": total,
        "status": "new",
        "paymentMethod": "on_pickup_or_delivery",
        "createdAt": ts,
        "updatedAt": ts,
    }
    if payload.idempotencyKey:
        order["idempotencyKey"] = payload.idempotencyKey
    try:
        res = await db.orders.insert_one(order)
    except Exception:
        # duplicate idempotency key race -> return existing
        if payload.idempotencyKey:
            existing = await db.orders.find_one({"restaurantId": rid, "idempotencyKey": payload.idempotencyKey})
            if existing:
                return serialize(existing)
        raise HTTPException(status_code=500, detail="De bestelling kon niet worden opgeslagen. Probeer het opnieuw.")
    order["_id"] = res.inserted_id
    await notify_new_order(rid, order_number)
    return serialize(order)


@router.get("/orders/{order_id}")
async def public_order_confirmation(order_id: str):
    order = await db.orders.find_one({"_id": oid(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    r = await db.restaurants.find_one({"_id": ObjectId(order["restaurantId"])})
    data = serialize(order)
    data["restaurantName"] = r["name"] if r else ""
    data["restaurantSlug"] = r["slug"] if r else ""
    return data
