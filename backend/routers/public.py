import hashlib
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from zoneinfo import ZoneInfo

from db import db
from models import AcceptInviteReq, PublicOrderReq, QuoteReq
from security import (create_access_token, create_refresh_token, hash_password,
                      set_auth_cookies)
from services.distance import geocode, haversine_km
from services.email import send_new_order_email, send_order_received_customer_email
from services.notifications import notify_new_order
from services.storage import open_file
from utils import (derive_status_token, hash_status_token, next_order_number,
                   now_iso, oid, serialize)

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
        "logo": (f"/api/public/restaurant/{r['slug']}/logo?v={r['logoFileId']}"
                 if r.get("logoFileId") else r.get("logo", "")),
        "menuFileUrl": (f"/api/public/restaurant/{r['slug']}/menu-file?v={r['menuFileId']}"
                        if r.get("menuFileId") else ""),
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
        "items": [_public_item(i, slug) for i in items],
    }


def _public_item(it: dict, slug: str) -> dict:
    """Serialize a menu item for public display and resolve its image URL.

    GridFS-backed images become a restaurant-scoped backend route; legacy URL
    images pass through unchanged. The internal file id is never exposed.
    """
    d = serialize(it)
    fid = it.get("imageFileId")
    if fid:
        d["image"] = f"/api/public/restaurant/{slug}/menu-item/{d['id']}/image?v={fid}"
    d.pop("imageFileId", None)
    return d


def _file_response(data: bytes, meta: dict, inline_name: str = None) -> Response:
    headers = {"Cache-Control": "public, max-age=86400"}
    if inline_name:
        safe = inline_name.replace('"', "").replace("\n", "")[:120]
        headers["Content-Disposition"] = f'inline; filename="{safe}"'
    return Response(content=data, media_type=meta.get("contentType", "application/octet-stream"), headers=headers)


@router.get("/restaurant/{slug}/logo")
async def public_logo(slug: str):
    r = await db.restaurants.find_one({"slug": slug})
    if not r or not r.get("logoFileId"):
        raise HTTPException(status_code=404, detail="Logo niet gevonden")
    data, meta = await open_file(r["logoFileId"])
    return _file_response(data, meta)


@router.get("/restaurant/{slug}/menu-item/{item_id}/image")
async def public_menu_item_image(slug: str, item_id: str):
    r = await db.restaurants.find_one({"slug": slug})
    if not r:
        raise HTTPException(status_code=404, detail="Niet gevonden")
    item = await db.menu_items.find_one({"_id": oid(item_id), "restaurantId": str(r["_id"])})
    if not item or not item.get("imageFileId"):
        raise HTTPException(status_code=404, detail="Afbeelding niet gevonden")
    data, meta = await open_file(item["imageFileId"])
    return _file_response(data, meta)


@router.get("/restaurant/{slug}/menu-file")
async def public_menu_file(slug: str):
    r = await db.restaurants.find_one({"slug": slug})
    if not r or not r.get("menuFileId"):
        raise HTTPException(status_code=404, detail="Menukaart niet gevonden")
    data, meta = await open_file(r["menuFileId"])
    return _file_response(data, meta, inline_name=r.get("menuFileName") or "menukaart")


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
async def create_public_order(slug: str, payload: PublicOrderReq, background_tasks: BackgroundTasks):
    r = await db.restaurants.find_one({"slug": slug, "isActive": True})
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant niet gevonden")
    rid = str(r["_id"])

    # Idempotency: duplicate submission returns the original order.
    if payload.idempotencyKey:
        existing = await db.orders.find_one({"restaurantId": rid, "idempotencyKey": payload.idempotencyKey})
        if existing:
            return _order_result_with_token(existing)

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
        "estimatedMinutes": None,
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
                return _order_result_with_token(existing)
        raise HTTPException(status_code=500, detail="De bestelling kon niet worden opgeslagen. Probeer het opnieuw.")
    order["_id"] = res.inserted_id
    # Secure customer status token: HMAC-derived from the order id (stable and
    # regenerable), only its SHA-256 hash is persisted. Expires after 30 days.
    status_token = derive_status_token(str(res.inserted_id))
    token_hash = hash_status_token(status_token)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    await db.orders.update_one(
        {"_id": res.inserted_id},
        {"$set": {"statusTokenHash": token_hash, "statusTokenExpiresAt": expires_at}},
    )
    order["statusTokenHash"] = token_hash
    order["statusTokenExpiresAt"] = expires_at
    await notify_new_order(rid, order_number)
    _lang = r.get("defaultLanguage", "nl")
    if r.get("orderEmailsEnabled", True) and r.get("email"):
        background_tasks.add_task(send_new_order_email, r["email"], r["name"], serialize(order), _lang)
    cust_email = (payload.customer.email or "").strip()
    if cust_email and r.get("customerEmailsEnabled", True):
        background_tasks.add_task(send_order_received_customer_email, cust_email, r["name"], serialize(order), status_token, _lang)
    return _order_result_with_token(order)


def _order_result_with_token(order_doc: dict) -> dict:
    """Serialize an order for the client and attach a usable status token.

    New orders derive the token from their id; legacy orders fall back to any
    stored plaintext token. The hash is never exposed.
    """
    result = serialize(order_doc)
    result.pop("statusTokenHash", None)
    result.pop("statusToken", None)
    result["statusToken"] = order_doc.get("statusToken") or derive_status_token(str(order_doc["_id"]))
    return result


def _public_order_view(order: dict, restaurant: dict) -> dict:
    """Minimal, safe projection for the customer status page — no internal ids/tokens."""
    items = [{
        "productName": it.get("productName"),
        "quantity": it.get("quantity"),
        "selectedOptions": [{"optionName": o.get("optionName")} for o in it.get("selectedOptions", [])],
        "lineTotal": it.get("lineTotal"),
    } for it in order.get("items", [])]
    da = order.get("deliveryAddress") or None
    addr = None
    if da:
        addr = {k: da.get(k) for k in ("street", "houseNumber", "postalCode", "city", "extra")}
    return {
        "orderNumber": order.get("orderNumber"),
        "restaurantName": restaurant["name"] if restaurant else "",
        "language": (restaurant.get("defaultLanguage", "nl") if restaurant else "en"),
        "orderType": order.get("orderType"),
        "status": order.get("status"),
        "estimatedMinutes": order.get("estimatedMinutes"),
        "estimatedTime": order.get("estimatedTime"),
        "items": items,
        "subtotal": order.get("subtotal"),
        "deliveryFee": order.get("deliveryFee"),
        "total": order.get("total"),
        "deliveryAddress": addr,
        "notes": order.get("notes"),
        "createdAt": order.get("createdAt"),
        "updatedAt": order.get("updatedAt"),
    }


@router.get("/order-status/{token}")
async def order_status(token: str):
    order = await db.orders.find_one({"statusTokenHash": hash_status_token(token)})
    if not order:
        # Legacy fallback: orders created before token hashing stored plaintext.
        order = await db.orders.find_one({"statusToken": token})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    expires = order.get("statusTokenExpiresAt")
    if not expires and order.get("createdAt"):
        try:
            expires = (datetime.fromisoformat(order["createdAt"]) + timedelta(days=30)).isoformat()
        except ValueError:
            expires = None
    if expires:
        try:
            expired = datetime.now(timezone.utc) > datetime.fromisoformat(expires)
        except ValueError:
            expired = False
        if expired:
            raise HTTPException(status_code=410, detail="Deze link is verlopen.")
    r = await db.restaurants.find_one({"_id": ObjectId(order["restaurantId"])})
    return _public_order_view(order, r)


@router.get("/orders/{order_id}")
async def public_order_confirmation(order_id: str):
    order = await db.orders.find_one({"_id": oid(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    r = await db.restaurants.find_one({"_id": ObjectId(order["restaurantId"])})
    data = serialize(order)
    data.pop("statusToken", None)
    data.pop("statusTokenHash", None)
    data["restaurantName"] = r["name"] if r else ""
    data["restaurantSlug"] = r["slug"] if r else ""
    data["language"] = (r.get("defaultLanguage", "nl") if r else "en")
    return data


# ---------- Staff invitation acceptance (no auth) ----------

_INVALID_INVITE = "Deze uitnodiging is ongeldig, verlopen of al gebruikt."


@router.get("/invitation/{token}")
async def get_invitation(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    inv = await db.staff_invitations.find_one(
        {"token_hash": token_hash, "used": False, "revoked": False, "expires_at": {"$gt": now}}
    )
    if not inv:
        raise HTTPException(status_code=404, detail=_INVALID_INVITE)
    r = await db.restaurants.find_one({"_id": ObjectId(inv["restaurantId"])})
    # Never echo the token or any id the client could use to target another tenant.
    return {"email": inv["email"], "restaurantName": r["name"] if r else ""}


@router.post("/invitation/accept")
async def accept_invitation(payload: AcceptInviteReq, response: Response):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    # Atomically claim the invitation so a double-submit cannot consume it twice.
    inv = await db.staff_invitations.find_one_and_update(
        {"token_hash": token_hash, "used": False, "revoked": False, "expires_at": {"$gt": now}},
        {"$set": {"used": True, "usedAt": now}},
    )
    if not inv:
        raise HTTPException(status_code=400, detail=_INVALID_INVITE)

    # restaurantId and email come ONLY from the stored invitation — never the request.
    email = inv["email"]
    restaurant_id = inv["restaurantId"]
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Er bestaat al een account met dit e-mailadres.")

    ts = now_iso()
    user = {
        "email": email,
        "passwordHash": hash_password(payload.password),
        "name": payload.name.strip(),
        "role": "restaurant_staff",
        "restaurantId": restaurant_id,
        "isActive": True,
        "tokenVersion": 0,
        "createdAt": ts,
        "updatedAt": ts,
    }
    res = await db.users.insert_one(user)
    user["_id"] = res.inserted_id

    # Clean up any other pending invites for this email.
    await db.staff_invitations.update_many(
        {"email": email, "used": False, "revoked": False},
        {"$set": {"revoked": True}},
    )

    access = create_access_token(str(res.inserted_id), email, 0)
    refresh = create_refresh_token(str(res.inserted_id), 0)
    set_auth_cookies(response, access, refresh)
    public = serialize(user)
    public.pop("passwordHash", None)
    return {"user": public, "token": access}
