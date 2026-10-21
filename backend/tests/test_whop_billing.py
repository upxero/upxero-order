# Whop billing IN-PROCESS tests: webhook verification, membership sync, downgrade/upgrade, email gating, quota races.
# Never calls api.whop.com: services.whop._request / get_membership are monkeypatched. Env set only in this process.
import os
import sys
import asyncio
import base64
import hashlib
import hmac
import json
import time
import uuid

os.environ["WHOP_WEBHOOK_SECRET"] = "ws_test_secret"
os.environ["WHOP_API_KEY"] = "test"
os.environ["WHOP_PLAN_ID"] = "plan_test"
sys.path.insert(0, "/app/backend")

LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)

import bcrypt  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
from bson import ObjectId  # noqa: E402
from pymongo.errors import DuplicateKeyError  # noqa: E402

import server  # noqa: E402
from db import db  # noqa: E402
from services import whop, entitlements as ent  # noqa: E402
import routers.public as rpublic  # noqa: E402
import routers.orders as rorders  # noqa: E402
import routers.restaurants as rrest  # noqa: E402
import routers.auth as rauth  # noqa: E402

BIZ, PROD, PLAN = whop.cfg("WHOP_BUSINESS_ID"), whop.cfg("WHOP_PRODUCT_ID"), "plan_test"
RND = uuid.uuid4().hex[:6]
MEMBERSHIPS = {}
CALLS = {"get_membership": [], "emails": [], "request": []}
S = {}


def run(coro):
    return LOOP.run_until_complete(coro)


async def _fake_get_membership(mid):
    CALLS["get_membership"].append(mid)
    m = MEMBERSHIPS.get(mid)
    if m == "ERR":
        raise whop.WhopError(500, f"/memberships/{mid}")
    if m is None:
        raise whop.WhopError(404, f"/memberships/{mid}")
    return dict(m)


async def _fake_request(method, path, **kw):
    CALLS["request"].append((method, path, kw))
    if path == "/checkout_configurations":
        return {"id": "ch_TEST", "purchase_url": "https://whop.com/checkout/TEST"}
    if path == "/memberships":
        return {"data": [dict(m) for m in MEMBERSHIPS.values() if isinstance(m, dict)]}
    raise AssertionError(f"unexpected Whop call {method} {path}")


def _rec(name):
    def f(*a, **k):
        CALLS["emails"].append(name)
    return f


@pytest.fixture(scope="module", autouse=True)
def patched():
    mp = pytest.MonkeyPatch()
    mp.setattr(whop, "get_membership", _fake_get_membership)
    mp.setattr(whop, "_request", _fake_request)
    for mod, names in [(rpublic, ["send_new_order_email", "send_order_received_customer_email"]),
                       (rorders, ["send_order_status_customer_email", "send_order_eta_customer_email"]),
                       (rrest, ["send_staff_invitation_email"]), (rauth, ["send_verification_email"])]:
        for n in names:
            mp.setattr(mod, n, _rec(n))
    yield
    mp.undo()
    rids = [S[k] for k in ("ridA", "ridB") if k in S]
    run(db.order_usage.delete_many({"restaurantId": {"$in": rids}}))
    run(db.billing_checkouts.delete_many({"restaurantId": {"$in": rids}}))
    run(db.whop_events.delete_many({"_id": {"$regex": f"^TEST_{RND}"}}))
    run(db.users.delete_many({"email": {"$regex": f"{RND}@upxerotest.com$"}}))


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")


async def call(method, path, token=None, **kw):
    async with client() as c:
        h = kw.pop("headers", {})
        if token:
            h["Authorization"] = f"Bearer {token}"
        return await c.request(method, f"/api{path}", headers=h, **kw)


def sign(body: bytes, wid: str, ts: int, secret="ws_test_secret"):
    sig = base64.b64encode(hmac.new(secret.encode(), f"{wid}.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    return {"webhook-id": wid, "webhook-timestamp": str(ts), "webhook-signature": f"v1,{sig}", "content-type": "application/json"}


_n = [0]


def hook(event: dict, wid=None, ts=None, secret="ws_test_secret", body=None):
    _n[0] += 1
    wid = wid or f"TEST_{RND}_msg{_n[0]}"
    raw = body if body is not None else json.dumps(event).encode()
    headers = sign(json.dumps(event).encode() if body is not None else raw, wid, ts or int(time.time()), secret)
    return run(call("POST", "/webhooks/whop", content=raw, headers=headers)), wid


def mem(mid, status, rid=None, ref=None, company=None, product=None, plan=PLAN):
    m = {"id": mid, "status": status, "company": {"id": company or BIZ}, "product": {"id": product or PROD},
         "plan": {"id": plan}, "user": {"id": "user_TEST"}, "metadata": {"restaurant_id": rid, "checkout_ref": ref},
         "renewal_period_end": "2026-02-20T00:00:00Z", "cancel_at_period_end": status == "canceling",
         "manage_url": "https://whop.com/manage/TEST"}
    MEMBERSHIPS[mid] = m
    return m


def plan_of(rid):
    return ent.effective_plan(run(db.restaurants.find_one({"_id": ObjectId(rid)})))


def event_result(wid):
    return (run(db.whop_events.find_one({"_id": wid})) or {}).get("result")


def staff_login():
    return run(call("POST", "/auth/login", json={"email": S["staff_email"], "password": "Staff!2025"})).status_code


# ---------- setup ----------
def test_00_setup():
    for k in ("A", "B"):
        r = run(call("POST", "/auth/register", json={"restaurantName": f"TEST_Whop{k} {RND}", "name": "TEST Owner",
                                                    "email": f"test_whop_{k.lower()}_{RND}@upxerotest.com", "password": "Test!2025x"}))
        assert r.status_code == 200, r.text
        S[f"tok{k}"] = r.json()["token"]
        me = run(call("GET", "/restaurant/me", S[f"tok{k}"])).json()
        S[f"rid{k}"], S[f"slug{k}"] = me["id"], me["slug"]
        assert me["plan"] == "free"
    S["refA"], S["refB"], S["refA2"] = f"ref_A_{RND}", f"ref_B_{RND}", f"ref_A2_{RND}"
    run(db.billing_checkouts.insert_many([{"ref": S["refA"], "restaurantId": S["ridA"]}, {"ref": S["refB"], "restaurantId": S["ridB"]},
                                          {"ref": S["refA2"], "restaurantId": S["ridA"]}]))
    S["staff_email"] = f"test_whop_staff_{RND}@upxerotest.com"
    run(db.users.insert_one({"email": S["staff_email"], "name": "TEST Staff", "role": "restaurant_staff", "restaurantId": S["ridA"],
                             "isActive": True, "emailVerified": True, "tokenVersion": 0,
                             "passwordHash": bcrypt.hashpw(b"Staff!2025", bcrypt.gensalt()).decode()}))
    assert staff_login() == 403


# ---------- signature verification ----------
def test_01_signature_checks():
    ev = {"type": "app.something", "data": {}}
    r, _ = hook(ev)
    assert r.status_code == 200 and r.json() == {"ok": True}
    r, _ = hook(ev, body=json.dumps({"type": "app.tampered"}).encode())
    assert r.status_code == 400
    r, _ = hook(ev, ts=int(time.time()) - 600)
    assert r.status_code == 400
    r, _ = hook(ev, ts=int(time.time()) + 600)
    assert r.status_code == 400
    r, _ = hook(ev, secret="wrong")
    assert r.status_code == 400
    r = run(call("POST", "/webhooks/whop", content=b"{}", headers={"webhook-id": "x"}))
    assert r.status_code == 400
    os.environ["WHOP_WEBHOOK_SECRET"] = ""
    try:
        r, _ = hook(ev)
        assert r.status_code == 503
    finally:
        os.environ["WHOP_WEBHOOK_SECRET"] = "ws_test_secret"


def test_02_activation_and_duplicate():
    mid = f"mem_TEST_{RND}_A1"
    S["midA1"] = mid
    mem(mid, "active", S["ridA"], S["refA"])
    before = len(CALLS["get_membership"])
    ev = {"type": "membership.activated", "data": {"id": mid, "status": "active"}}
    r, wid = hook(ev)
    assert r.status_code == 200
    r2, _ = hook(ev, wid=wid)
    assert r2.json().get("duplicate") is True
    assert len(CALLS["get_membership"]) - before == 1
    assert event_result(wid) == "applied:pro"
    assert plan_of(S["ridA"]) == "pro"
    st = run(call("GET", "/billing/status", S["tokA"])).json()
    assert st["plan"] == "pro" and st["status"] == "active" and st["usage"]["monthlyOrderLimit"] is None
    assert st["manageUrl"] and st["checkoutAvailable"] is False
    assert run(db.audit_logs.find_one({"restaurantId": {"$in": [S["ridA"], ObjectId(S["ridA"])]}, "action": "subscription.changed"})) is not None
    assert staff_login() == 200


def test_03_unlinked_and_foreign():
    cases = [(mem(f"mem_TEST_{RND}_u1", "active", S["ridB"], "ref_unknown"), "ignored:unlinked"),
             (mem(f"mem_TEST_{RND}_u2", "active", S["ridB"], S["refA"]), "ignored:unlinked"),  # ref of other restaurant
             (mem(f"mem_TEST_{RND}_f1", "active", S["ridB"], S["refB"], product="prod_other"), "ignored:foreign"),
             (mem(f"mem_TEST_{RND}_f2", "active", S["ridB"], S["refB"], company="biz_other"), "ignored:foreign"),
             (mem(f"mem_TEST_{RND}_f3", "active", S["ridB"], S["refB"], plan="plan_other"), "ignored:foreign")]
    for m, expected in cases:
        r, wid = hook({"type": "membership.activated", "data": {"id": m["id"]}})
        assert r.status_code == 200 and event_result(wid) == expected, (m["id"], event_result(wid))
    assert plan_of(S["ridB"]) == "free"
    r, wid = hook({"type": "membership.activated", "data": {}})
    assert event_result(wid) == "ignored:no_membership"


def test_04_past_due_and_canceling_stay_pro():
    mid = S["midA1"]
    MEMBERSHIPS[mid]["status"] = "past_due"
    r, wid = hook({"type": "payment.failed", "data": {"id": "pay_x", "membership": {"id": mid}}})
    assert event_result(wid) == "applied:pro" and plan_of(S["ridA"]) == "pro"
    MEMBERSHIPS[mid]["status"] = "canceling"
    MEMBERSHIPS[mid]["cancel_at_period_end"] = True
    r, wid = hook({"type": "membership.cancel_at_period_end_changed", "data": {"id": mid}})
    assert event_result(wid) == "applied:pro"
    st = run(call("GET", "/billing/status", S["tokA"])).json()
    assert st["plan"] == "pro" and st["cancelAtPeriodEnd"] is True


def test_05_downgrade_keeps_data():
    rid = S["ridA"]
    cat = run(call("POST", "/menu/categories", S["tokA"], json={"name": "TEST_Cat"})).json()
    S["cat"] = cat["id"]
    for i in range(25):
        r = run(call("POST", "/menu/items", S["tokA"], json={"categoryId": cat["id"], "name": f"TEST_P{i}", "price": 4.0}))
        assert r.status_code == 200
    S["item"] = r.json()["id"]
    ts = "2026-01-01T10:00:00+00:00"
    oid_ = run(db.orders.insert_one({"restaurantId": rid, "orderNumber": 9001, "orderType": "delivery", "status": "new",
                                     "customer": {"name": "TEST", "phone": "0470", "email": "cust@upxerotest.com"},
                                     "items": [], "subtotal": 10, "deliveryFee": 2, "total": 12, "createdAt": ts, "updatedAt": ts})).inserted_id
    S["delivery_order"] = str(oid_)
    MEMBERSHIPS[S["midA1"]]["status"] = "expired"
    r, wid = hook({"type": "membership.deactivated", "data": {"id": S["midA1"]}})
    assert event_result(wid) == "applied:free" and plan_of(rid) == "free"
    assert run(db.menu_items.count_documents({"restaurantId": rid, "isAvailable": True})) == 25
    assert run(db.users.find_one({"email": S["staff_email"]})) is not None
    assert staff_login() == 403
    CALLS["emails"].clear()
    r = run(call("PATCH", f"/orders/{S['delivery_order']}/status", S["tokA"], json={"status": "accepted", "estimatedMinutes": 30}))
    assert r.status_code == 200, r.text
    assert run(db.orders.find_one({"_id": oid_}))["status"] == "accepted"
    assert CALLS["emails"] == []
    # above the limit: activating anything new blocked, deactivating allowed
    r = run(call("POST", "/menu/items", S["tokA"], json={"categoryId": cat["id"], "name": "TEST_X", "price": 4.0}))
    assert r.status_code == 403


def test_06_out_of_order_old_activation_stays_free():
    r, wid = hook({"type": "membership.activated", "data": {"id": S["midA1"], "status": "active"}},
                  ts=int(time.time()) - 200)
    assert r.status_code == 200 and plan_of(S["ridA"]) == "free"


def test_07_upgrade_restores_then_refund():
    MEMBERSHIPS[S["midA1"]]["status"] = "active"
    hook({"type": "membership.activated", "data": {"id": S["midA1"]}})
    assert plan_of(S["ridA"]) == "pro" and staff_login() == 200
    MEMBERSHIPS[S["midA1"]]["status"] = "canceled"
    r, wid = hook({"type": "refund.created", "data": {"id": "rf_x", "payment": {"membership": {"id": S["midA1"]}}}})
    assert event_result(wid) == "applied:free" and plan_of(S["ridA"]) == "free"


def test_08_second_membership_rules():
    MEMBERSHIPS[S["midA1"]]["status"] = "active"
    hook({"type": "membership.activated", "data": {"id": S["midA1"]}})
    assert plan_of(S["ridA"]) == "pro"
    m2 = mem(f"mem_TEST_{RND}_A2", "active", S["ridA"], S["refA2"])
    r, wid = hook({"type": "membership.activated", "data": {"id": m2["id"]}})
    assert event_result(wid) == "ignored:other_membership"
    assert run(db.restaurants.find_one({"_id": ObjectId(S["ridA"])}))["subscription"]["whopMembershipId"] == S["midA1"]
    # membership A1 metadata pointing at B is still applied to A (linked by id), never B
    MEMBERSHIPS[S["midA1"]]["metadata"] = {"restaurant_id": S["ridB"], "checkout_ref": S["refB"]}
    hook({"type": "membership.updated", "data": {"id": S["midA1"]}})
    assert plan_of(S["ridB"]) == "free"
    MEMBERSHIPS[S["midA1"]]["metadata"] = {"restaurant_id": S["ridA"], "checkout_ref": S["refA"]}
    with pytest.raises(DuplicateKeyError):
        run(db.restaurants.update_one({"_id": ObjectId(S["ridB"])}, {"$set": {"subscription.whopMembershipId": S["midA1"]}}))
    # first membership ends -> a new valid one may replace it
    MEMBERSHIPS[S["midA1"]]["status"] = "canceled"
    hook({"type": "membership.deactivated", "data": {"id": S["midA1"]}})
    r, wid = hook({"type": "membership.activated", "data": {"id": m2["id"]}})
    assert event_result(wid) == "applied:pro"
    assert run(db.restaurants.find_one({"_id": ObjectId(S["ridA"])}))["subscription"]["whopMembershipId"] == m2["id"]


def test_09_whop_error_releases_claim():
    MEMBERSHIPS["mem_ERR"] = "ERR"
    ev = {"type": "membership.updated", "data": {"id": "mem_ERR"}}
    r, wid = hook(ev)
    assert r.status_code == 503 and run(db.whop_events.find_one({"_id": wid})) is None
    MEMBERSHIPS.pop("mem_ERR")
    mem("mem_ERR", "active", S["ridB"], "ref_none")
    r, _ = hook(ev, wid=wid)
    assert r.status_code == 200 and event_result(wid) == "ignored:unlinked"


def test_10_email_gating():
    rid = S["ridB"]
    run(db.restaurants.update_one({"_id": ObjectId(rid)}, {"$set": {
        "orderingEnabled": True, "pickupEnabled": True, "email": f"test_whop_b_{RND}@upxerotest.com",
        "openingHours": {d: {"closed": False, "open": "00:00", "close": "00:00"} for d in
                         ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}}}))
    cat = run(call("POST", "/menu/categories", S["tokB"], json={"name": "TEST_Cat"})).json()
    item = run(call("POST", "/menu/items", S["tokB"], json={"categoryId": cat["id"], "name": "TEST_I", "price": 3.0})).json()
    body = {"orderType": "pickup", "items": [{"productId": item["id"], "quantity": 1}],
            "customer": {"name": "TEST", "phone": "04700000", "email": f"cust_{RND}@upxerotest.com"}}
    CALLS["emails"].clear()
    r = run(call("POST", f"/public/restaurant/{S['slugB']}/orders", json=body))
    assert r.status_code == 200, r.text
    assert CALLS["emails"] == [], CALLS["emails"]
    oid_ = r.json()["id"]
    run(call("PATCH", f"/orders/{oid_}/status", S["tokB"], json={"status": "accepted", "estimatedMinutes": 20}))
    assert CALLS["emails"] == []
    run(db.restaurants.update_one({"_id": ObjectId(rid)}, {"$set": {"subscription": {"legacy": True}}}))
    r = run(call("POST", f"/public/restaurant/{S['slugB']}/orders", json=body))
    assert r.status_code == 200
    assert set(CALLS["emails"]) >= {"send_new_order_email", "send_order_received_customer_email"}, CALLS["emails"]
    run(db.restaurants.update_one({"_id": ObjectId(rid)}, {"$unset": {"subscription": ""}}))


def test_11_checkout_and_sync_mocked():
    CALLS["request"].clear()
    r = run(call("POST", "/billing/checkout", S["tokB"]))
    assert r.status_code == 200 and r.json()["purchaseUrl"].startswith("https://whop.com/")
    method, path, kw = CALLS["request"][-1]
    assert (method, path) == ("POST", "/checkout_configurations")
    assert kw["json"]["plan_id"] == PLAN and kw["json"]["metadata"]["restaurant_id"] == S["ridB"]
    assert kw["json"]["redirect_url"].endswith("/dashboard/abonnement?checkout=done")
    ref = kw["json"]["metadata"]["checkout_ref"]
    assert run(db.billing_checkouts.find_one({"ref": ref}))["whopCheckoutId"] == "ch_TEST"
    assert run(call("POST", "/billing/checkout", S["tokA"])).status_code == 400  # already pro
    for k in ("f1", "f2", "f3"):  # real list is filtered by product id; drop foreign fixtures
        MEMBERSHIPS.pop(f"mem_TEST_{RND}_{k}", None)
    mem(f"mem_TEST_{RND}_B1", "trialing", S["ridB"], ref)
    r = run(call("POST", "/billing/sync", S["tokB"]))
    assert r.status_code == 200 and r.json()["plan"] == "pro", r.text
    assert run(call("POST", "/billing/sync", S["tokB"])).status_code == 429


def test_12_quota_race_inprocess():
    r = {"_id": ObjectId(S["ridB"])}  # Free restaurant doc stub (no subscription)
    uid = f"{S['ridB']}:{ent.month_key()}"

    async def burst(n):
        res = await asyncio.gather(*[ent.reserve_order_slot(r) for _ in range(n)], return_exceptions=True)
        return sum(1 for x in res if isinstance(x, Exception))

    run(db.order_usage.update_one({"_id": uid}, {"$set": {"count": 28}}, upsert=True))
    assert run(burst(10)) == 8
    assert run(db.order_usage.find_one({"_id": uid}))["count"] == 30
    spurious = 0
    for _ in range(5):
        run(db.order_usage.delete_one({"_id": uid}))
        spurious += run(burst(10))
    print("first-of-month spurious 409s over 5x10 bursts:", spurious)
    assert spurious == 0, f"{spurious} spurious limit rejections on first-of-month concurrent upserts"
