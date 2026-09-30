from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from db import db
from models import ForgotPasswordReq, LoginReq, RegisterReq, ResetPasswordReq
from security import (clear_auth_cookies, create_access_token,
                      create_refresh_token, get_current_user, hash_password,
                      set_auth_cookies, verify_password, _secret, JWT_ALGORITHM)
from services.email import send_password_reset_email
from utils import now_iso, serialize, unique_slug
import jwt
from bson import ObjectId

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def _public_user(user: dict) -> dict:
    u = serialize(user)
    u.pop("passwordHash", None)
    return u


async def _check_lockout(identifier: str):
    doc = await db.login_attempts.find_one({"identifier": identifier})
    if not doc:
        return
    if doc.get("count", 0) >= MAX_ATTEMPTS and doc.get("lockedUntil"):
        locked_until = datetime.fromisoformat(doc["lockedUntil"])
        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Te veel pogingen. Probeer het later opnieuw.")


async def _register_failure(identifier: str, email: str):
    doc = await db.login_attempts.find_one({"identifier": identifier})
    count = (doc.get("count", 0) if doc else 0) + 1
    update = {"count": count, "email": email, "identifier": identifier}
    if count >= MAX_ATTEMPTS:
        update["lockedUntil"] = (datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)).isoformat()
    await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)


@router.post("/register")
async def register(payload: RegisterReq, response: Response):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Dit e-mailadres is al in gebruik")

    slug = await unique_slug(db, payload.restaurantName)
    ts = now_iso()
    restaurant = {
        "name": payload.restaurantName.strip(),
        "slug": slug,
        "logo": "",
        "description": "",
        "phone": "",
        "email": email,
        "street": "", "houseNumber": "", "postalCode": "", "city": "", "country": "BE",
        "latitude": None, "longitude": None,
        "openingHours": _default_hours(),
        "pickupEnabled": True,
        "deliveryEnabled": False,
        "orderingEnabled": False,
        "deliveryZones": [],
        "freeDeliveryEnabled": False,
        "freeDeliveryThreshold": 0,
        "defaultLanguage": "nl",
        "isActive": True,
        "createdAt": ts, "updatedAt": ts,
    }
    res = await db.restaurants.insert_one(restaurant)
    restaurant_id = res.inserted_id

    user = {
        "email": email,
        "passwordHash": hash_password(payload.password),
        "name": payload.name.strip(),
        "role": "restaurant_admin",
        "restaurantId": str(restaurant_id),
        "isActive": True,
        "createdAt": ts, "updatedAt": ts,
    }
    ures = await db.users.insert_one(user)
    user["_id"] = ures.inserted_id

    access = create_access_token(str(ures.inserted_id), email)
    refresh = create_refresh_token(str(ures.inserted_id))
    set_auth_cookies(response, access, refresh)
    return {"user": _public_user(user), "token": access}


@router.post("/login")
async def login(payload: LoginReq, request: Request, response: Response):
    email = payload.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    await _check_lockout(identifier)

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("passwordHash", "")):
        await _register_failure(identifier, email)
        raise HTTPException(status_code=401, detail="Ongeldige inloggegevens")
    if not user.get("isActive", True):
        raise HTTPException(status_code=403, detail="Account is gedeactiveerd")

    await db.login_attempts.delete_many({"identifier": identifier})
    access = create_access_token(str(user["_id"]), email, user.get("tokenVersion", 0))
    refresh = create_refresh_token(str(user["_id"]), user.get("tokenVersion", 0))
    set_auth_cookies(response, access, refresh)
    return {"user": _public_user(user), "token": access}


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"message": "Uitgelogd"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    result = {"user": _public_user(user)}
    if user.get("restaurantId"):
        r = await db.restaurants.find_one({"_id": ObjectId(str(user["restaurantId"]))})
        result["restaurant"] = serialize(r)
    return result


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Geen sessie")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Ongeldig token")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Gebruiker niet gevonden")
        if payload.get("ver", 0) != user.get("tokenVersion", 0):
            raise HTTPException(status_code=401, detail="Sessie verlopen")
        access = create_access_token(str(user["_id"]), user["email"], user.get("tokenVersion", 0))
        response.set_cookie("access_token", access, httponly=True, secure=True,
                            samesite="none", max_age=43200, path="/")
        return {"token": access}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Ongeldig token")


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordReq, background_tasks: BackgroundTasks):
    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)
    generic = {"message": "Als dit e-mailadres bij ons bekend is, hebben we een resetlink verstuurd."}

    # Record the attempt before lookup so unregistered addresses are throttled too.
    await db.password_reset_requests.insert_one({"email": email, "created_at": now})
    per_email = await db.password_reset_requests.count_documents(
        {"email": email, "created_at": {"$gte": now - timedelta(minutes=15)}}
    )
    if per_email > 5:
        return generic
    app_wide = await db.password_reset_requests.count_documents(
        {"created_at": {"$gte": now - timedelta(minutes=10)}}
    )
    if app_wide > 10:
        return generic

    user = await db.users.find_one({"email": email})
    if not user:
        return generic

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await db.password_reset_tokens.insert_one({
        "token_hash": token_hash,
        "user_id": str(user["_id"]),
        "email": email,
        "expires_at": now + timedelta(hours=1),
        "used": False,
        "created_at": now,
    })
    background_tasks.add_task(send_password_reset_email, user["email"], token)
    return generic


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordReq):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    doc = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": token_hash, "used": False, "expires_at": {"$gt": now}},
        {"$set": {"used": True}},
    )
    if not doc:
        raise HTTPException(status_code=400, detail="Deze resetlink is ongeldig of verlopen.")

    user_id = doc["user_id"]
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"passwordHash": hash_password(payload.password), "updatedAt": now_iso()},
         "$inc": {"tokenVersion": 1}},
    )
    await db.password_reset_tokens.delete_many({"user_id": user_id, "used": False})
    await db.login_attempts.delete_many({"email": doc["email"]})
    return {"message": "Je wachtwoord is gewijzigd. Je kunt nu inloggen."}


def _default_hours():
    base = {"closed": False, "open": "11:30", "close": "21:30"}
    return {
        "monday": {"closed": True, "open": "11:30", "close": "21:30"},
        "tuesday": dict(base),
        "wednesday": dict(base),
        "thursday": dict(base),
        "friday": {"closed": False, "open": "11:30", "close": "22:00"},
        "saturday": {"closed": False, "open": "12:00", "close": "22:00"},
        "sunday": {"closed": False, "open": "16:00", "close": "21:30"},
    }
