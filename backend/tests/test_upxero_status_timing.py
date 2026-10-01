"""Upxero V2 refinement: email required, estimatedMinutes, hashed status token.

Covers:
- Checkout email required / invalid email / missing phone -> 422.
- Public order creation returns statusToken (plaintext) but no statusTokenHash.
- /public/order-status/{token} returns the order with estimatedMinutes and
  does NOT leak statusToken/statusTokenHash/internal ids.
- Accept with estimatedMinutes (10, 30, 60) persists; eta update to 45 reflects
  on status page; invalid minutes 0/9999 rejected (422) on both endpoints.
- Status workflow unchanged and cancellations allowed; illegal transitions 400.
- Random token -> 404; expired token (statusTokenExpiresAt in past) -> 410.
- Legacy plaintext statusToken fallback still works.
- Independent email toggles (orderEmailsEnabled vs customerEmailsEnabled).
- Tenant isolation on PATCH /orders/{id}/status and /eta -> 404.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
SLUG = "bistro-demo"
OWNER = {"email": "owner@demo.upxero.com", "password": "Demo!2025"}

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ---------- helpers ----------
def _owner_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=OWNER, timeout=30)
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


def _public():
    r = requests.get(f"{API}/public/restaurant/{SLUG}", timeout=30)
    assert r.status_code == 200
    return r.json()


def _simple_item(pdata):
    for i in pdata["items"]:
        if not any(g.get("required") for g in i.get("optionGroups") or []) and i.get("isAvailable", True):
            return i
    pytest.skip("no simple item available")


def _create_pickup(pdata, customer=None, idem=None):
    item = _simple_item(pdata)
    body = {
        "orderType": "pickup",
        "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": []}],
        "customer": customer or {"name": "TEST V2", "phone": "0400111222", "email": "v2@example.com"},
        "idempotencyKey": idem or f"TEST-V2-{uuid.uuid4()}",
    }
    return requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=30)


@pytest.fixture(scope="module")
def pdata():
    return _public()


@pytest.fixture(scope="module")
def owner():
    return _owner_session()


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


# ---------- Email required / invalid ----------
class TestCheckoutEmail:
    def test_missing_email_rejected_422(self, pdata):
        item = _simple_item(pdata)
        body = {
            "orderType": "pickup",
            "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": []}],
            "customer": {"name": "No Email", "phone": "0400111222"},
            "idempotencyKey": f"TEST-NOEMAIL-{uuid.uuid4()}",
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=30)
        assert r.status_code == 422, r.text

    def test_invalid_email_rejected_422(self, pdata):
        r = _create_pickup(pdata, customer={"name": "Bad", "phone": "0400111222", "email": "notanemail"})
        assert r.status_code == 422, r.text

    def test_missing_phone_rejected_422(self, pdata):
        item = _simple_item(pdata)
        body = {
            "orderType": "pickup",
            "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": []}],
            "customer": {"name": "No Phone", "email": "noph@example.com"},
            "idempotencyKey": f"TEST-NOPH-{uuid.uuid4()}",
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=30)
        assert r.status_code == 422, r.text

    def test_valid_order_returns_status_token_and_no_hash(self, pdata):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip(f"ordering closed: {r.text}")
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["status"] == "new"
        assert o.get("estimatedMinutes") is None
        assert o.get("statusToken") and isinstance(o["statusToken"], str)
        assert "statusTokenHash" not in o


# ---------- Delivery E2E (end-to-end; depends on geocoding) ----------
class TestDeliveryEndToEnd:
    def test_delivery_order_persists_fee_and_total(self, pdata):
        if not pdata["restaurant"]["deliveryEnabled"]:
            pytest.skip("delivery disabled")
        # Need subtotal >= min; pick cheapest simple item but quantity large.
        items = [i for i in pdata["items"] if not any(g.get("required") for g in i.get("optionGroups") or [])]
        assert items
        chosen = min(items, key=lambda x: x["price"])
        body = {
            "orderType": "delivery",
            "items": [{"productId": chosen["id"], "quantity": 5, "selectedOptions": []}],
            "customer": {"name": "TEST Deliv", "phone": "0400111222", "email": "deliv@example.com"},
            "deliveryAddress": {"street": "Nieuwstraat", "houseNumber": "10", "postalCode": "1000", "city": "Brussel"},
            "idempotencyKey": f"TEST-DELIV-{uuid.uuid4()}",
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=60)
        if r.status_code in (400, 409):
            pytest.skip(f"delivery not viable right now: {r.status_code} {r.text}")
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["orderType"] == "delivery"
        assert o["deliveryFee"] >= 0
        assert o["total"] == round(o["subtotal"] + o["deliveryFee"], 2)
        # confirm address persisted
        assert o["deliveryAddress"]["city"].lower().startswith("brussel")


# ---------- Status token endpoint ----------
class TestStatusTokenEndpoint:
    def test_status_page_returns_safe_projection(self, pdata):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        assert r.status_code == 200
        tok = r.json()["statusToken"]
        s = requests.get(f"{API}/public/order-status/{tok}", timeout=15)
        assert s.status_code == 200, s.text
        body = s.json()
        assert "estimatedMinutes" in body
        assert body["status"] == "new"
        for forbidden in ("statusToken", "statusTokenHash", "id", "_id", "restaurantId", "idempotencyKey"):
            assert forbidden not in body, f"{forbidden} leaked in response"

    def test_random_token_404(self):
        r = requests.get(f"{API}/public/order-status/not-a-real-token-xyz", timeout=15)
        assert r.status_code == 404

    def test_customer_endpoint_is_read_only(self, pdata):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        tok = r.json()["statusToken"]
        # No PATCH/POST/DELETE should be allowed for the customer status route
        for verb in ("patch", "post", "delete", "put"):
            resp = getattr(requests, verb)(f"{API}/public/order-status/{tok}",
                                           json={"status": "accepted"}, timeout=10)
            assert resp.status_code in (404, 405), f"{verb.upper()} unexpectedly allowed: {resp.status_code}"

    def test_expired_token_returns_410(self, pdata, mongo):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        o = r.json()
        tok = o["statusToken"]
        oid = ObjectId(o["id"])
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mongo.orders.update_one({"_id": oid}, {"$set": {"statusTokenExpiresAt": past}})
        s = requests.get(f"{API}/public/order-status/{tok}", timeout=15)
        assert s.status_code == 410, s.text

    def test_legacy_plaintext_token_fallback(self, pdata, mongo):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        o = r.json()
        oid = ObjectId(o["id"])
        legacy = f"legacy-{uuid.uuid4().hex}"
        # Simulate an old-style order: plaintext statusToken, no hash/expiry.
        mongo.orders.update_one(
            {"_id": oid},
            {"$set": {"statusToken": legacy},
             "$unset": {"statusTokenHash": "", "statusTokenExpiresAt": ""}},
        )
        s = requests.get(f"{API}/public/order-status/{legacy}", timeout=15)
        assert s.status_code == 200, s.text


# ---------- Accept + ETA (minutes) ----------
class TestAcceptAndEta:
    @pytest.mark.parametrize("minutes", [10, 30, 60])
    def test_accept_with_preset_minutes(self, pdata, owner, minutes):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        oid = r.json()["id"]
        up = owner.patch(f"{API}/orders/{oid}/status",
                         json={"status": "accepted", "estimatedMinutes": minutes})
        assert up.status_code == 200, up.text
        body = up.json()
        assert body["status"] == "accepted"
        assert body["estimatedMinutes"] == minutes
        assert "estimatedTime" not in body or not isinstance(body.get("estimatedTime"), str) \
            or ":" not in str(body.get("estimatedTime") or "")

    def test_eta_update_and_reflects_on_status_page(self, pdata, owner):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        o = r.json()
        oid, tok = o["id"], o["statusToken"]
        assert owner.patch(f"{API}/orders/{oid}/status",
                           json={"status": "accepted", "estimatedMinutes": 20}).status_code == 200
        eta = owner.patch(f"{API}/orders/{oid}/eta", json={"estimatedMinutes": 45})
        assert eta.status_code == 200, eta.text
        assert eta.json()["estimatedMinutes"] == 45
        s = requests.get(f"{API}/public/order-status/{tok}", timeout=15).json()
        assert s["estimatedMinutes"] == 45

    @pytest.mark.parametrize("bad", [0, 9999, -5, 601])
    def test_invalid_minutes_422_on_status(self, pdata, owner, bad):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        oid = r.json()["id"]
        up = owner.patch(f"{API}/orders/{oid}/status",
                         json={"status": "accepted", "estimatedMinutes": bad})
        assert up.status_code == 422, f"minutes={bad} should 422; got {up.status_code} {up.text}"

    @pytest.mark.parametrize("bad", [0, 9999, -1, 601])
    def test_invalid_minutes_422_on_eta(self, pdata, owner, bad):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        oid = r.json()["id"]
        # must accept first to enable ETA edit
        owner.patch(f"{API}/orders/{oid}/status",
                    json={"status": "accepted", "estimatedMinutes": 15})
        up = owner.patch(f"{API}/orders/{oid}/eta", json={"estimatedMinutes": bad})
        assert up.status_code == 422, f"minutes={bad} should 422; got {up.status_code}"


# ---------- Workflow / cancellation ----------
class TestWorkflow:
    def test_full_workflow_and_illegal_transition(self, pdata, owner):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        oid = r.json()["id"]
        bad = owner.patch(f"{API}/orders/{oid}/status", json={"status": "ready"})
        assert bad.status_code == 400
        for st in ["accepted", "preparing", "ready", "completed"]:
            up = owner.patch(f"{API}/orders/{oid}/status", json={"status": st})
            assert up.status_code == 200, up.text
            assert up.json()["status"] == st
        # cannot transition out of completed
        tail = owner.patch(f"{API}/orders/{oid}/status", json={"status": "cancelled"})
        assert tail.status_code == 400

    def test_cancel_from_new(self, pdata, owner):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        oid = r.json()["id"]
        up = owner.patch(f"{API}/orders/{oid}/status", json={"status": "cancelled"})
        assert up.status_code == 200
        assert up.json()["status"] == "cancelled"

    def test_cancel_from_ready(self, pdata, owner):
        r = _create_pickup(pdata)
        if r.status_code == 409:
            pytest.skip("ordering closed")
        oid = r.json()["id"]
        for st in ["accepted", "preparing", "ready"]:
            assert owner.patch(f"{API}/orders/{oid}/status", json={"status": st}).status_code == 200
        up = owner.patch(f"{API}/orders/{oid}/status", json={"status": "cancelled"})
        assert up.status_code == 200


# ---------- Tenant isolation ----------
class TestTenantIsolationOrders:
    def test_patch_foreign_order_status_404(self, owner):
        # synthetic ObjectId not owned by this restaurant
        up = owner.patch(f"{API}/orders/000000000000000000000000/status",
                         json={"status": "accepted"})
        assert up.status_code == 404

    def test_patch_foreign_order_eta_404(self, owner):
        up = owner.patch(f"{API}/orders/000000000000000000000000/eta",
                         json={"estimatedMinutes": 20})
        assert up.status_code == 404


# ---------- Email toggles independence ----------
class TestEmailToggleIndependence:
    def test_toggles_are_decoupled(self, owner, mongo):
        me = owner.get(f"{API}/restaurant/me").json()
        rid = me["id"]
        before = mongo.restaurants.find_one({"_id": ObjectId(rid)}) or {}
        orig = {
            "orderEmailsEnabled": before.get("orderEmailsEnabled", True),
            "customerEmailsEnabled": before.get("customerEmailsEnabled", True),
        }
        try:
            # Flip customer only
            r = owner.put(f"{API}/restaurant/settings",
                          json={"orderingEnabled": me.get("orderingEnabled", True),
                                "pickupEnabled": me.get("pickupEnabled", True),
                                "orderEmailsEnabled": True,
                                "customerEmailsEnabled": False})
            assert r.status_code == 200, r.text
            doc = mongo.restaurants.find_one({"_id": ObjectId(rid)})
            assert doc["orderEmailsEnabled"] is True
            assert doc["customerEmailsEnabled"] is False
            # Flip restaurant only
            r = owner.put(f"{API}/restaurant/settings",
                          json={"orderingEnabled": me.get("orderingEnabled", True),
                                "pickupEnabled": me.get("pickupEnabled", True),
                                "orderEmailsEnabled": False,
                                "customerEmailsEnabled": True})
            assert r.status_code == 200
            doc = mongo.restaurants.find_one({"_id": ObjectId(rid)})
            assert doc["orderEmailsEnabled"] is False
            assert doc["customerEmailsEnabled"] is True
        finally:
            owner.put(f"{API}/restaurant/settings",
                      json={"orderingEnabled": me.get("orderingEnabled", True),
                            "pickupEnabled": me.get("pickupEnabled", True),
                            "orderEmailsEnabled": orig["orderEmailsEnabled"],
                            "customerEmailsEnabled": orig["customerEmailsEnabled"]})
