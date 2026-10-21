# Stage 3: subscription status for seeded Pro, admin legacy (Complimentary Pro) toggle 409/authz/audit, admin list plan,
# public monthlyLimitReached + no delivery on Free. LIVE API, TEST_ data only, Whop never called.
import os
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import jwt
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]
API = f"{BASE_URL.strip().strip(chr(34)).rstrip('/')}/api"


def _env(k):
    for line in open("/app/backend/.env"):
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip().strip('"')


mdb = MongoClient(_env("MONGO_URL"))[_env("DB_NAME")]
MONTH = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Brussels")).strftime("%Y-%m")
ALWAYS = {d: {"closed": False, "open": "00:00", "close": "00:00"} for d in
          ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
LIMIT_EN_NL = "Dit restaurant kan tijdelijk geen nieuwe online bestellingen aannemen. Neem rechtstreeks contact op met het restaurant."


def hdr(t):
    return {"Authorization": f"Bearer {t}"}


def super_token():
    # super admin password rotated by real owner -> mint access token (no DB change)
    u = mdb.users.find_one({"email": "mike.upxero@gmail.com", "role": "super_admin"})
    return jwt.encode({"sub": str(u["_id"]), "email": u["email"], "ver": u.get("tokenVersion", 0),
                       "exp": datetime.now(timezone.utc) + timedelta(minutes=30), "type": "access"},
                      _env("JWT_SECRET"), algorithm="HS256")


@pytest.fixture(scope="module")
def ctx():
    rnd = uuid.uuid4().hex[:8]
    email = f"test_s3_{rnd}@upxerotest.com"
    r = requests.post(f"{API}/auth/register", json={"restaurantName": f"TEST_S3 {rnd}", "name": "TEST Owner",
                                                     "email": email, "password": "Test!2025x"}, timeout=20)
    assert r.status_code in (200, 201), r.text
    tok = r.json()["token"]
    me = requests.get(f"{API}/restaurant/me", headers=hdr(tok), timeout=20).json()
    c = {"tok": tok, "rid": me["id"], "slug": me["slug"], "email": email, "super": super_token()}
    yield c
    rid = c["rid"]
    for col in ["order_usage", "billing_checkouts", "audit_logs", "menu_items", "menu_categories"]:
        mdb[col].delete_many({"restaurantId": {"$in": [rid, ObjectId(rid)]}})
    mdb.users.delete_many({"email": email})
    mdb.restaurants.delete_one({"_id": ObjectId(rid)})


def test_free_billing_status(ctx):
    d = requests.get(f"{API}/billing/status", headers=hdr(ctx["tok"]), timeout=20).json()
    assert d["plan"] == "free" and d["checkoutAvailable"] is False
    assert d["usage"]["monthlyOrderLimit"] == 30 and d["usage"]["activeProductLimit"] == 20


def test_seeded_pro_status(ctx):
    end = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    mdb.restaurants.update_one({"_id": ObjectId(ctx["rid"])}, {"$set": {"subscription": {
        "whopMembershipId": f"mem_test_{ctx['rid']}", "whopStatus": "active", "renewalPeriodEnd": end,
        "cancelAtPeriodEnd": False, "manageUrl": "https://whop.com/billing/manage/mem_test1",
        "lastSyncedAt": datetime.now(timezone.utc).isoformat()}}})
    d = requests.get(f"{API}/billing/status", headers=hdr(ctx["tok"]), timeout=20).json()
    print(d)
    assert d["plan"] == "pro" and d["status"] == "active"
    assert d["manageUrl"] == "https://whop.com/billing/manage/mem_test1"
    assert d["renewalPeriodEnd"] == end
    assert d["usage"]["monthlyOrderLimit"] in (None, 0) and d["usage"]["activeProductLimit"] in (None, 0)


def test_legacy_409_when_paid_active(ctx):
    r = requests.patch(f"{API}/admin/restaurants/{ctx['rid']}/legacy", json={"legacy": True}, headers=hdr(ctx["super"]), timeout=20)
    assert r.status_code == 409, r.text
    assert mdb.restaurants.find_one({"_id": ObjectId(ctx["rid"])})["subscription"].get("legacy") in (None, False)
    mdb.restaurants.update_one({"_id": ObjectId(ctx["rid"])}, {"$set": {"subscription": {}}})


def test_legacy_authz(ctx):
    url = f"{API}/admin/restaurants/{ctx['rid']}/legacy"
    assert requests.patch(url, json={"legacy": True}, timeout=20).status_code == 401
    assert requests.patch(url, json={"legacy": True}, headers=hdr(ctx["tok"]), timeout=20).status_code == 403
    o = requests.post(f"{API}/auth/login", json={"email": "owner@demo.upxero.com", "password": "Demo!2025"}, timeout=20)
    assert o.status_code == 200
    assert requests.patch(url, json={"legacy": True}, headers=hdr(o.json()["token"]), timeout=20).status_code == 403
    s = requests.post(f"{API}/auth/login", json={"email": "staff@demo.upxero.com", "password": "Demo!2025"}, timeout=20)
    if s.status_code == 200:
        assert requests.patch(url, json={"legacy": True}, headers=hdr(s.json()["token"]), timeout=20).status_code == 403


def test_grant_revoke_legacy_and_audit(ctx):
    url = f"{API}/admin/restaurants/{ctx['rid']}/legacy"
    g = requests.patch(url, json={"legacy": True}, headers=hdr(ctx["super"]), timeout=20)
    assert g.status_code == 200 and g.json()["plan"] == "legacy"
    assert requests.get(f"{API}/billing/status", headers=hdr(ctx["tok"]), timeout=20).json()["plan"] == "legacy"
    lst = requests.get(f"{API}/admin/restaurants", headers=hdr(ctx["super"]), timeout=20).json()
    rows = lst if isinstance(lst, list) else lst.get("restaurants", lst.get("items", []))
    mine = [x for x in rows if x["id"] == ctx["rid"]]
    assert mine and mine[0]["plan"] == "legacy"
    rv = requests.patch(url, json={"legacy": False}, headers=hdr(ctx["super"]), timeout=20)
    assert rv.status_code == 200 and rv.json()["plan"] == "free"
    acts = [a["action"] for a in mdb.audit_logs.find({"restaurantId": {"$in": [ctx["rid"], ObjectId(ctx["rid"])]}})]
    assert "subscription.legacy_set" in acts and "subscription.legacy_removed" in acts


def test_admin_list_plans_real(ctx):
    lst = requests.get(f"{API}/admin/restaurants", headers=hdr(ctx["super"]), timeout=20).json()
    rows = lst if isinstance(lst, list) else lst.get("restaurants", lst.get("items", []))
    by = {x["name"]: x.get("plan") for x in rows}
    print({k: v for k, v in by.items() if not k.startswith("TEST_")})
    assert by.get("Bistro Demo") == "legacy"
    assert by.get("New Edo Sushi") == "legacy"


def test_public_limit_reached_and_no_delivery(ctx):
    h = hdr(ctx["tok"])
    assert requests.put(f"{API}/restaurant/settings", json={"orderingEnabled": True, "pickupEnabled": True}, headers=h, timeout=20).status_code == 200
    assert requests.put(f"{API}/restaurant/opening-hours", json=ALWAYS, headers=h, timeout=20).status_code == 200
    mdb.restaurants.update_one({"_id": ObjectId(ctx["rid"])}, {"$set": {"deliveryEnabled": True}})
    mdb.order_usage.update_one({"_id": f"{ctx['rid']}:{MONTH}"}, {"$set": {"restaurantId": ctx["rid"], "month": MONTH, "count": 30}}, upsert=True)
    p = requests.get(f"{API}/public/restaurant/{ctx['slug']}", timeout=20)
    assert p.status_code == 200, p.text
    rest = p.json().get("restaurant", p.json())
    assert rest["monthlyLimitReached"] is True
    assert rest["deliveryEnabled"] is False
    body = str(p.json()).lower()
    assert "whop" not in body and "subscription" not in body
