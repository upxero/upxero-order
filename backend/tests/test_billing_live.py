# Stage 2 Free/Pro billing - LIVE API regression (public URL). Uses TEST_ data only; cleans up at end.
import os
import uuid
import concurrent.futures as cf
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import bcrypt
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]
BASE_URL = BASE_URL.strip().strip('"').rstrip("/")
API = f"{BASE_URL}/api"


def _env(k):
    for line in open("/app/backend/.env"):
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip().strip('"')


mdb = MongoClient(_env("MONGO_URL"))[_env("DB_NAME")]
SUPER = ("mike.upxero@gmail.com", "Upxero!Admin2025")
OWNER = ("owner@demo.upxero.com", "Demo!2025")
STAFF = ("staff@demo.upxero.com", "Demo!2025")
MONTH = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Brussels")).strftime("%Y-%m")
ALWAYS = {d: {"closed": False, "open": "00:00", "close": "00:00"} for d in
          ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}


def login(email, pw):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)


def super_token():
    # Super admin password was rotated by the real owner -> mint an access token (no DB change).
    import jwt
    from datetime import timedelta
    u = mdb.users.find_one({"email": SUPER[0], "role": "super_admin"})
    return jwt.encode({"sub": str(u["_id"]), "email": u["email"], "ver": u.get("tokenVersion", 0),
                       "exp": datetime.now(timezone.utc) + timedelta(minutes=30), "type": "access"},
                      _env("JWT_SECRET"), algorithm="HS256")


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def ctx():
    rnd = uuid.uuid4().hex[:8]
    email = f"test_billing_{rnd}@upxerotest.com"
    r = requests.post(f"{API}/auth/register", json={"restaurantName": f"TEST_Billing {rnd}", "name": "TEST Owner",
                                                     "email": email, "password": "Test!2025x", "language": "nl"}, timeout=20)
    assert r.status_code in (200, 201), r.text
    tok = r.json()["token"]
    me = requests.get(f"{API}/restaurant/me", headers=hdr(tok), timeout=20).json()
    sup_tok = super_token()
    c = {"tok": tok, "rid": me["id"], "slug": me["slug"], "me": me, "email": email, "rnd": rnd,
         "super": sup_tok, "items": [], "staff_email": f"test_billing_staff_{rnd}@upxerotest.com"}
    yield c
    rid = c["rid"]
    mdb.order_usage.delete_many({"restaurantId": rid})
    mdb.billing_checkouts.delete_many({"restaurantId": rid})
    mdb.users.delete_many({"email": {"$regex": f"{rnd}@upxerotest.com$"}})
    mdb.staff_invitations.delete_many({"restaurantId": rid})


# ---- Plan / status ----
def test_free_plan_status(ctx):
    assert ctx["me"]["plan"] == "free"
    assert "subscription" not in ctx["me"] or not (ctx["me"].get("subscription") or {}).get("legacy")
    s = requests.get(f"{API}/billing/status", headers=hdr(ctx["tok"]), timeout=20)
    assert s.status_code == 200
    d = s.json()
    assert d["plan"] == "free" and d["legacy"] is False and d["checkoutAvailable"] is False
    assert d["usage"]["monthlyOrderLimit"] == 30 and d["usage"]["activeProductLimit"] == 20
    assert d["usage"]["ordersThisMonth"] == 0 and d["usage"]["activeProducts"] == 0
    assert d["usage"]["month"] == MONTH


def test_profile_put_route_exists(ctx):
    # regression: @router.put("/profile") decorator was missing
    me = ctx["me"]
    body = {k: me.get(k, "") for k in ["name", "description", "phone", "email", "street", "houseNumber", "postalCode", "city"]}
    body.update({"country": "BE", "name": me["name"]})
    r = requests.put(f"{API}/restaurant/profile", json=body, headers=hdr(ctx["tok"]), timeout=20)
    assert r.status_code != 404, "PUT /api/restaurant/profile route missing"
    assert r.status_code in (200, 422), r.text


# ---- Product limit ----
def test_product_limit(ctx):
    h = hdr(ctx["tok"])
    cat = requests.post(f"{API}/menu/categories", json={"name": "TEST_Cat", "sortOrder": 0, "isActive": True}, headers=h, timeout=20)
    assert cat.status_code == 200, cat.text
    ctx["cat"] = cat.json()["id"]
    for i in range(20):
        r = requests.post(f"{API}/menu/items", json={"categoryId": ctx["cat"], "name": f"TEST_Item{i}", "price": 5.0}, headers=h, timeout=20)
        assert r.status_code == 200, (i, r.text)
        ctx["items"].append(r.json()["id"])
    r21 = requests.post(f"{API}/menu/items", json={"categoryId": ctx["cat"], "name": "TEST_Item21", "price": 5.0}, headers=h, timeout=20)
    assert r21.status_code == 403
    off = requests.post(f"{API}/menu/items", json={"categoryId": ctx["cat"], "name": "TEST_Off", "price": 5.0, "isAvailable": False}, headers=h, timeout=20)
    assert off.status_code == 200 and off.json()["isAvailable"] is False
    off_id = off.json()["id"]
    a = requests.patch(f"{API}/menu/items/{off_id}/availability", json={"isAvailable": True}, headers=h, timeout=20)
    assert a.status_code == 403
    # PUT activating inactive item also blocked
    p = requests.put(f"{API}/menu/items/{off_id}", json={"categoryId": ctx["cat"], "name": "TEST_Off", "price": 5.0, "isAvailable": True}, headers=h, timeout=20)
    assert p.status_code == 403
    d = requests.patch(f"{API}/menu/items/{ctx['items'][0]}/availability", json={"isAvailable": False}, headers=h, timeout=20)
    assert d.status_code == 200
    a2 = requests.patch(f"{API}/menu/items/{off_id}/availability", json={"isAvailable": True}, headers=h, timeout=20)
    assert a2.status_code == 200 and a2.json()["isAvailable"] is True
    e = requests.put(f"{API}/menu/items/{ctx['items'][1]}", json={"categoryId": ctx["cat"], "name": "TEST_Item1 edited", "price": 6.5, "isAvailable": True}, headers=h, timeout=20)
    assert e.status_code == 200 and e.json()["name"] == "TEST_Item1 edited"
    s = requests.get(f"{API}/billing/status", headers=h, timeout=20).json()
    assert s["usage"]["activeProducts"] == 20
    ctx["item"] = ctx["items"][1]


# ---- Delivery on Free ----
def test_delivery_blocked_on_free(ctx):
    h = hdr(ctx["tok"])
    r = requests.put(f"{API}/restaurant/delivery", json={"deliveryEnabled": True, "zones": [{"minDistance": 0, "maxDistance": 10, "deliveryFee": 2, "minimumOrderAmount": 0}]}, headers=h, timeout=20)
    assert r.status_code == 403
    assert requests.put(f"{API}/restaurant/settings", json={"orderingEnabled": True, "pickupEnabled": True}, headers=h, timeout=20).status_code == 200
    assert requests.put(f"{API}/restaurant/opening-hours", json=ALWAYS, headers=h, timeout=20).status_code == 200
    mdb.restaurants.update_one({"_id": ObjectId(ctx["rid"])}, {"$set": {"deliveryEnabled": True, "latitude": 50.85, "longitude": 4.35,
                                "deliveryZones": [{"id": "z1", "minDistance": 0, "maxDistance": 50, "deliveryFee": 2, "minimumOrderAmount": 0, "enabled": True}]}})
    pub = requests.get(f"{API}/public/restaurant/{ctx['slug']}", timeout=20).json()
    assert pub["restaurant"]["deliveryEnabled"] is False
    items = [{"productId": ctx["item"], "quantity": 1}]
    addr = {"street": "Grote Markt", "houseNumber": "1", "postalCode": "1000", "city": "Brussel"}
    q = requests.post(f"{API}/public/restaurant/{ctx['slug']}/quote", json={"orderType": "delivery", "items": items, "deliveryAddress": addr}, timeout=20)
    assert q.status_code == 400
    o = requests.post(f"{API}/public/restaurant/{ctx['slug']}/orders", json={"orderType": "delivery", "items": items, "deliveryAddress": addr,
                      "customer": {"name": "TEST C", "phone": "0470000000", "email": "cust@upxerotest.com"}}, timeout=20)
    assert o.status_code == 400
    assert mdb.order_usage.find_one({"_id": f"{ctx['rid']}:{MONTH}"}) is None  # rejected order consumed no quota


def _order(ctx, key=None):
    body = {"orderType": "pickup", "items": [{"productId": ctx["item"], "quantity": 1}],
            "customer": {"name": "TEST C", "phone": "0470000000", "email": "cust@upxerotest.com"}}
    if key:
        body["idempotencyKey"] = key
    return requests.post(f"{API}/public/restaurant/{ctx['slug']}/orders", json=body, timeout=30)


# ---- Monthly order limit ----
def test_monthly_order_limit(ctx):
    first = None
    for i in range(30):
        r = _order(ctx, key=f"TEST-{ctx['rnd']}-{i}")
        assert r.status_code == 200, (i, r.text)
        if i == 0:
            first = r.json()
    r31 = _order(ctx, key=f"TEST-{ctx['rnd']}-31")
    assert r31.status_code == 409
    dup = _order(ctx, key=f"TEST-{ctx['rnd']}-0")
    assert dup.status_code == 200
    fid = first.get("id") or first.get("order", {}).get("id")
    did = dup.json().get("id") or dup.json().get("order", {}).get("id")
    assert fid == did
    assert mdb.order_usage.find_one({"_id": f"{ctx['rid']}:{MONTH}"})["count"] == 30
    assert mdb.orders.count_documents({"restaurantId": ctx["rid"]}) == 30
    pub = requests.get(f"{API}/public/restaurant/{ctx['slug']}", timeout=20).json()
    assert pub["restaurant"]["monthlyLimitReached"] is True
    s = requests.get(f"{API}/billing/status", headers=hdr(ctx["tok"]), timeout=20).json()
    assert s["usage"]["ordersThisMonth"] == 30


def test_order_limit_concurrency(ctx):
    mdb.order_usage.update_one({"_id": f"{ctx['rid']}:{MONTH}"}, {"$set": {"count": 28}})
    with cf.ThreadPoolExecutor(10) as ex:
        res = list(ex.map(lambda i: _order(ctx).status_code, range(10)))
    assert res.count(200) == 2, res
    assert res.count(409) == 8, res
    assert mdb.order_usage.find_one({"_id": f"{ctx['rid']}:{MONTH}"})["count"] == 30


def test_first_order_of_month_race(ctx):
    # No usage doc yet (start of month) -> concurrent upserts must not falsely 409
    mdb.order_usage.delete_one({"_id": f"{ctx['rid']}:{MONTH}"})
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda i: _order(ctx).status_code, range(8)))
    cnt = mdb.order_usage.find_one({"_id": f"{ctx['rid']}:{MONTH}"})["count"]
    print("first-of-month race results", res, "count", cnt)
    assert res.count(200) == 8, f"spurious rejections at first order of month: {res}"


# ---- Staff on Free / legacy toggle ----
def test_staff_gating_and_legacy_toggle(ctx):
    h = hdr(ctx["tok"])
    inv = requests.post(f"{API}/restaurant/staff/invite", json={"email": f"test_billing_inv_{ctx['rnd']}@upxerotest.com"}, headers=h, timeout=20)
    assert inv.status_code == 403
    ts = datetime.now(timezone.utc).isoformat()
    sid = mdb.users.insert_one({"email": ctx["staff_email"], "name": "TEST Staff", "role": "restaurant_staff",
                                "restaurantId": ctx["rid"], "isActive": True, "emailVerified": True, "tokenVersion": 0,
                                "passwordHash": bcrypt.hashpw(b"Staff!2025", bcrypt.gensalt()).decode(),
                                "createdAt": ts, "updatedAt": ts}).inserted_id
    assert login(ctx["staff_email"], "Staff!2025").status_code == 403
    sh = hdr(ctx["super"])
    lg = requests.patch(f"{API}/admin/restaurants/{ctx['rid']}/legacy", json={"legacy": True}, headers=sh, timeout=20)
    assert lg.status_code == 200 and lg.json() == {"legacy": True, "plan": "legacy"}
    sl = login(ctx["staff_email"], "Staff!2025")
    assert sl.status_code == 200
    stok = sl.json()["token"]
    assert requests.get(f"{API}/restaurant/me", headers=hdr(stok), timeout=20).status_code == 200
    assert requests.get(f"{API}/orders", headers=hdr(stok), timeout=20).status_code == 200
    st = requests.get(f"{API}/billing/status", headers=h, timeout=20).json()
    assert st["plan"] == "legacy" and st["usage"]["monthlyOrderLimit"] is None
    inv2 = requests.post(f"{API}/restaurant/staff/invite", json={"email": f"test_billing_inv_{ctx['rnd']}@upxerotest.com"}, headers=h, timeout=20)
    assert inv2.status_code == 200
    # legacy restaurant: limit not enforced (usage is 30+)
    assert _order(ctx).status_code == 200
    assert requests.get(f"{API}/public/restaurant/{ctx['slug']}", timeout=20).json()["restaurant"]["monthlyLimitReached"] is False
    lg2 = requests.patch(f"{API}/admin/restaurants/{ctx['rid']}/legacy", json={"legacy": False}, headers=sh, timeout=20)
    assert lg2.status_code == 200 and lg2.json()["plan"] == "free"
    assert requests.get(f"{API}/restaurant/me", headers=hdr(stok), timeout=20).status_code == 403
    assert requests.get(f"{API}/orders", headers=hdr(stok), timeout=20).status_code == 403
    assert login(ctx["staff_email"], "Staff!2025").status_code == 403
    assert mdb.users.find_one({"_id": sid}) is not None
    assert mdb.staff_invitations.count_documents({"restaurantId": ctx["rid"]}) >= 1
    # re-activating staff on Free blocked; owner can still list staff
    act = requests.patch(f"{API}/restaurant/staff/{sid}/active", json={"isActive": True}, headers=h, timeout=20)
    assert act.status_code == 403
    assert requests.get(f"{API}/restaurant/staff", headers=h, timeout=20).status_code == 200
    mdb.order_usage.update_one({"_id": f"{ctx['rid']}:{MONTH}"}, {"$set": {"count": 30}})
    assert _order(ctx).status_code == 409


# ---- Admin endpoint authz ----
def test_admin_billing_endpoints_authz(ctx):
    url = f"{API}/admin/restaurants/{ctx['rid']}/legacy"
    assert requests.patch(url, json={"legacy": True}, timeout=20).status_code == 401
    assert requests.patch(url, json={"legacy": True}, headers=hdr(ctx["tok"]), timeout=20).status_code == 403
    st = login(*STAFF).json()["token"]
    assert requests.patch(url, json={"legacy": True}, headers=hdr(st), timeout=20).status_code == 403
    assert requests.get(f"{API}/admin/billing/whop-plans", timeout=20).status_code == 401
    assert requests.get(f"{API}/admin/billing/whop-plans", headers=hdr(ctx["tok"]), timeout=20).status_code == 403
    wp = requests.get(f"{API}/admin/billing/whop-plans", headers=hdr(ctx["super"]), timeout=20)
    assert wp.status_code == 503
    assert requests.patch(f"{API}/admin/restaurants/{'0'*24}/legacy", json={"legacy": True}, headers=hdr(ctx["super"]), timeout=20).status_code == 404
    assert requests.get(f"{API}/billing/status", headers=hdr(ctx["tok"]), timeout=20).json()["plan"] == "free"


# ---- Billing endpoints authz / not configured ----
def test_billing_endpoints(ctx):
    h = hdr(ctx["tok"])
    for m, p in [("get", "/billing/status"), ("post", "/billing/checkout"), ("post", "/billing/sync")]:
        assert getattr(requests, m)(f"{API}{p}", timeout=20).status_code == 401
    st = login(*STAFF).json()["token"]
    assert requests.get(f"{API}/billing/status", headers=hdr(st), timeout=20).status_code == 403
    assert requests.post(f"{API}/billing/checkout", headers=h, timeout=20).status_code == 503
    assert requests.post(f"{API}/billing/sync", headers=h, timeout=20).status_code == 503
    assert mdb.billing_checkouts.count_documents({"restaurantId": ctx["rid"]}) == 0
    ow = login(*OWNER).json()["token"]
    assert requests.post(f"{API}/billing/checkout", headers=hdr(ow), timeout=20).status_code == 400
    wh = requests.post(f"{API}/webhooks/whop", data=b'{"type":"membership.activated"}',
                       headers={"webhook-id": "msg_x", "webhook-timestamp": "1", "webhook-signature": "v1,abc"}, timeout=20)
    assert wh.status_code == 503


# ---- Bistro Demo (legacy) unaffected ----
def test_bistro_demo_legacy():
    ow = login(*OWNER)
    assert ow.status_code == 200
    h = hdr(ow.json()["token"])
    s = requests.get(f"{API}/billing/status", headers=h, timeout=20).json()
    assert s["plan"] == "legacy" and s["legacy"] is True
    me = requests.get(f"{API}/restaurant/me", headers=h, timeout=20).json()
    assert me["plan"] == "legacy"
    body = {"deliveryEnabled": me.get("deliveryEnabled", False), "zones": me.get("deliveryZones", []),
            "freeDeliveryEnabled": me.get("freeDeliveryEnabled", False), "freeDeliveryThreshold": me.get("freeDeliveryThreshold", 0)}
    d = requests.put(f"{API}/restaurant/delivery", json=body, headers=h, timeout=20)
    assert d.status_code == 200, d.text
    assert login(*STAFF).status_code == 200
    pub = requests.get(f"{API}/public/restaurant/{me['slug']}", timeout=20).json()
    assert pub["restaurant"]["monthlyLimitReached"] is False
