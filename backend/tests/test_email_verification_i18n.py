"""Iteration 10: email verification (tokens, resend, rate limit), register/forgot language,
existing accounts unaffected, reset-password regression, staff invite regression."""
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
UA = {"User-Agent": "Mozilla/5.0 TestAgent"}
OWNER = {"email": "owner@demo.upxero.com", "password": "Demo!2025"}
SUPER = {"email": "mike.upxero@gmail.com", "password": "Upxero!Admin2025"}

mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
EMAIL = f"delivered+t10api{uuid.uuid4().hex[:6]}@resend.dev"
PWD = "TestPass!123"


def _h(t):
    return hashlib.sha256(t.encode()).hexdigest()


def _login(creds):
    s = requests.Session()
    s.headers.update(UA)
    r = s.post(f"{API}/auth/login", json=creds)
    assert r.status_code == 200, r.text
    return s, r.json()


def _insert_token(uid, email, hours=24, used=False):
    raw = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    mdb.email_verification_tokens.insert_one({
        "token_hash": _h(raw), "user_id": uid, "email": email,
        "expires_at": now + timedelta(hours=hours), "used": used, "created_at": now})
    return raw


@pytest.fixture(scope="module")
def reg():
    s = requests.Session()
    s.headers.update(UA)
    r = s.post(f"{API}/auth/register", json={
        "restaurantName": "TEST_Verify API Resto", "name": "TEST Verifier",
        "email": EMAIL, "password": PWD, "language": "nl"})
    assert r.status_code == 200, r.text
    data = r.json()
    yield s, data
    u = mdb.users.find_one({"email": EMAIL})
    if u:
        mdb.email_verification_tokens.delete_many({"user_id": str(u["_id"])})
        mdb.email_verification_requests.delete_many({"user_id": str(u["_id"])})
        mdb.password_reset_tokens.delete_many({"user_id": str(u["_id"])})
        mdb.restaurants.delete_one({"_id": ObjectId(u["restaurantId"])})
        mdb.users.delete_one({"_id": u["_id"]})
    mdb.password_reset_requests.delete_many({"email": EMAIL})


# Register stores language + unverified flag
def test_register_language_and_unverified(reg):
    s, data = reg
    assert data["user"]["emailVerified"] is False
    assert data["user"]["language"] == "nl"
    assert "passwordHash" not in data["user"]
    me = s.get(f"{API}/auth/me").json()
    assert me["restaurant"]["defaultLanguage"] == "nl"
    assert me["user"]["emailVerified"] is False
    # a token was issued and stored hashed
    tok = mdb.email_verification_tokens.find_one({"user_id": data["user"]["id"]})
    assert tok and len(tok["token_hash"]) == 64 and tok["used"] is False


def test_register_default_language_en():
    email = f"TEST_noLang_{uuid.uuid4().hex[:6]}@example.com".lower()
    r = requests.post(f"{API}/auth/register", headers=UA, json={
        "restaurantName": "TEST_NoLang Resto", "name": "TEST NoLang", "email": email, "password": PWD})
    try:
        assert r.status_code == 200, r.text
        assert r.json()["user"]["language"] == "en"
        rest = mdb.restaurants.find_one({"_id": ObjectId(r.json()["user"]["restaurantId"])})
        assert rest["defaultLanguage"] == "en"
    finally:
        u = mdb.users.find_one({"email": email})
        if u:
            mdb.email_verification_tokens.delete_many({"user_id": str(u["_id"])})
            mdb.restaurants.delete_one({"_id": ObjectId(u["restaurantId"])})
            mdb.users.delete_one({"_id": u["_id"]})


def test_register_invalid_language_422():
    r = requests.post(f"{API}/auth/register", headers=UA, json={
        "restaurantName": "TEST_x", "name": "TEST x", "email": "TEST_bad@example.com",
        "password": PWD, "language": "fr"})
    assert r.status_code == 422


# Verify-email token lifecycle
def test_verify_invalid_and_expired(reg):
    _, data = reg
    uid = data["user"]["id"]
    assert requests.post(f"{API}/auth/verify-email", json={"token": "x" * 40}).status_code == 400
    assert requests.post(f"{API}/auth/verify-email", json={"token": "short"}).status_code == 422
    expired = _insert_token(uid, EMAIL, hours=-1)
    r = requests.post(f"{API}/auth/verify-email", json={"token": expired})
    assert r.status_code == 400
    used = _insert_token(uid, EMAIL, used=True)
    assert requests.post(f"{API}/auth/verify-email", json={"token": used}).status_code == 400
    assert mdb.users.find_one({"email": EMAIL})["emailVerified"] is False


def test_resend_invalidates_old_token_and_rate_limit(reg):
    s, data = reg
    uid = data["user"]["id"]
    old = _insert_token(uid, EMAIL)
    r = s.post(f"{API}/auth/resend-verification")
    assert r.status_code == 200, r.text
    assert "alreadyVerified" not in r.json()
    assert requests.post(f"{API}/auth/verify-email", json={"token": old}).status_code == 400
    # simulate 2 more recent requests -> next one must be 429
    now = datetime.now(timezone.utc)
    mdb.email_verification_requests.insert_many([{"user_id": uid, "created_at": now} for _ in range(2)])
    r = s.post(f"{API}/auth/resend-verification")
    assert r.status_code == 429
    assert "Te veel verzoeken" in r.json()["detail"]
    mdb.email_verification_requests.delete_many({"user_id": uid})


def test_verify_success_then_reuse(reg):
    s, data = reg
    uid = data["user"]["id"]
    raw = _insert_token(uid, EMAIL)
    r = requests.post(f"{API}/auth/verify-email", json={"token": raw})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == EMAIL
    me = s.get(f"{API}/auth/me").json()
    assert me["user"]["emailVerified"] is True
    assert requests.post(f"{API}/auth/verify-email", json={"token": raw}).status_code == 400
    r = s.post(f"{API}/auth/resend-verification")
    assert r.status_code == 200 and r.json().get("alreadyVerified") is True


# Existing accounts not locked out, count as verified
@pytest.mark.parametrize("creds", [OWNER, SUPER])
def test_existing_accounts_verified(creds):
    s, data = _login(creds)
    assert data["user"].get("emailVerified") is not False
    r = s.post(f"{API}/auth/resend-verification")
    assert r.status_code == 200 and r.json().get("alreadyVerified") is True


def test_resend_requires_auth():
    assert requests.post(f"{API}/auth/resend-verification", headers=UA).status_code == 401


# Forgot password generic response + language
def test_forgot_password_generic(reg):
    a = requests.post(f"{API}/auth/forgot-password", headers=UA, json={"email": EMAIL, "language": "nl"})
    b = requests.post(f"{API}/auth/forgot-password", headers=UA,
                      json={"email": f"TEST_nobody_{uuid.uuid4().hex[:6]}@example.com", "language": "en"})
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()
    assert requests.post(f"{API}/auth/forgot-password", json={"email": EMAIL, "language": "de"}).status_code == 422
    u = mdb.users.find_one({"email": EMAIL})
    tok = mdb.password_reset_tokens.find_one({"user_id": str(u["_id"])})
    assert tok and len(tok["token_hash"]) == 64


def test_reset_password_flow(reg):
    u = mdb.users.find_one({"email": EMAIL})
    raw = secrets.token_urlsafe(32)
    mdb.password_reset_tokens.insert_one({
        "token_hash": _h(raw), "user_id": str(u["_id"]), "email": EMAIL,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "used": False,
        "created_at": datetime.now(timezone.utc)})
    new_pwd = "NewPass!456"
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "password": new_pwd})
    assert r.status_code == 200, r.text
    assert requests.post(f"{API}/auth/reset-password", json={"token": raw, "password": new_pwd}).status_code == 400
    r = requests.post(f"{API}/auth/login", headers=UA, json={"email": EMAIL, "password": new_pwd})
    assert r.status_code == 200


# Staff invite regression
def test_staff_invite_owner():
    s, _ = _login(OWNER)
    inv_email = f"delivered+t10staff{uuid.uuid4().hex[:6]}@resend.dev"
    r = s.post(f"{API}/restaurant/staff/invite", json={"email": inv_email})
    try:
        assert r.status_code == 200, r.text
        assert r.json()["email"] == inv_email
        assert mdb.staff_invitations.find_one({"email": inv_email, "used": False})
    finally:
        mdb.staff_invitations.delete_many({"email": inv_email})
