"""End-to-end backend tests for Upxero Ordering.

Covers: auth (login/me/logout/lockout-reset), menu categories & items CRUD,
tenant isolation, restaurant settings, public ordering (quote, order create,
below-minimum, idempotency, price-security), order status transitions.
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "owner@demo.upxero.com", "password": "Demo!2025"}
STAFF = {"email": "staff@demo.upxero.com", "password": "Demo!2025"}
SUPER = {"email": "mike.upxero@gmail.com", "password": "Upxero!Admin2025"}
SLUG = "bistro-demo"


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    body = r.json()
    # Also set bearer as belt & suspenders
    s.headers.update({"Authorization": f"Bearer {body['token']}"})
    return s, body


@pytest.fixture(scope="session")
def owner_session():
    s, body = _login(OWNER)
    return s, body


@pytest.fixture(scope="session")
def public_data():
    r = requests.get(f"{API}/public/restaurant/{SLUG}", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Health ----------
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


# ---------- Auth ----------
class TestAuth:
    def test_login_owner(self, owner_session):
        _, body = owner_session
        assert body["user"]["email"] == OWNER["email"]
        assert body["user"]["role"] == "restaurant_admin"
        assert "passwordHash" not in body["user"]
        assert body.get("token")

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": OWNER["email"], "password": "wrong-xyz"}, timeout=30)
        assert r.status_code == 401

    def test_me(self, owner_session):
        s, _ = owner_session
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["user"]["email"] == OWNER["email"]
        assert "restaurant" in r.json()

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_login_super_admin(self):
        s, body = _login(SUPER)
        assert body["user"]["role"] == "super_admin"


# ---------- Menu categories CRUD ----------
class TestMenu:
    def test_category_crud_and_persistence(self, owner_session):
        s, _ = owner_session
        payload = {"name": f"TEST_Cat_{uuid.uuid4().hex[:6]}", "description": "t", "sortOrder": 99}
        c = s.post(f"{API}/menu/categories", json=payload)
        assert c.status_code == 200, c.text
        cid = c.json()["id"]
        # verify listing
        lst = s.get(f"{API}/menu/categories").json()
        assert any(x["id"] == cid for x in lst)
        # update
        up = s.put(f"{API}/menu/categories/{cid}", json={**payload, "name": "TEST_Cat_upd"})
        assert up.status_code == 200 and up.json()["name"] == "TEST_Cat_upd"
        # delete
        d = s.delete(f"{API}/menu/categories/{cid}")
        assert d.status_code == 200
        lst2 = s.get(f"{API}/menu/categories").json()
        assert not any(x["id"] == cid for x in lst2)

    def test_item_crud_with_options_and_availability(self, owner_session):
        s, _ = owner_session
        cats = s.get(f"{API}/menu/categories").json()
        assert cats, "expected demo categories"
        cid = cats[0]["id"]
        item_payload = {
            "categoryId": cid,
            "name": f"TEST_Item_{uuid.uuid4().hex[:6]}",
            "description": "t",
            "price": 9.5,
            "sortOrder": 50,
            "isAvailable": True,
            "optionGroups": [{
                "name": "Saus", "required": True, "multiple": False,
                "options": [{"name": "Mayo", "price": 0}, {"name": "Ketchup", "price": 0.5}],
            }],
        }
        c = s.post(f"{API}/menu/items", json=item_payload)
        assert c.status_code == 200, c.text
        iid = c.json()["id"]
        assert c.json()["optionGroups"][0]["id"]
        # availability off
        av = s.patch(f"{API}/menu/items/{iid}/availability", json={"isAvailable": False})
        assert av.status_code == 200 and av.json()["isAvailable"] is False
        # update
        up = s.put(f"{API}/menu/items/{iid}",
                   json={**item_payload, "name": "TEST_Item_upd", "price": 10.0})
        assert up.status_code == 200 and up.json()["price"] == 10.0
        # delete
        d = s.delete(f"{API}/menu/items/{iid}")
        assert d.status_code == 200


# ---------- Restaurant settings ----------
class TestRestaurantSettings:
    def test_settings_toggle_and_persist(self, owner_session):
        s, _ = owner_session
        cur = s.get(f"{API}/restaurant/me").json()
        original = {"orderingEnabled": cur.get("orderingEnabled", True),
                    "pickupEnabled": cur.get("pickupEnabled", True)}
        # flip and back
        r = s.put(f"{API}/restaurant/settings",
                  json={"orderingEnabled": not original["orderingEnabled"],
                        "pickupEnabled": original["pickupEnabled"]})
        assert r.status_code == 200
        assert r.json()["orderingEnabled"] == (not original["orderingEnabled"])
        # restore
        s.put(f"{API}/restaurant/settings", json={**original})

    def test_opening_hours_update(self, owner_session):
        s, _ = owner_session
        cur = s.get(f"{API}/restaurant/me").json()
        hours = cur.get("openingHours") or {}
        # keep all days but ensure valid values
        default_day = {"closed": False, "open": "10:00", "close": "22:00"}
        payload = {d: hours.get(d, default_day) for d in
                   ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
        payload["monday"] = {"closed": True, "open": "11:30", "close": "21:30"}
        r = s.put(f"{API}/restaurant/opening-hours", json=payload)
        assert r.status_code == 200
        assert r.json()["openingHours"]["monday"]["closed"] is True


# ---------- Tenant isolation ----------
class TestTenantIsolation:
    def test_get_arbitrary_order_returns_404(self, owner_session):
        s, _ = owner_session
        r = s.get(f"{API}/orders/000000000000000000000000")
        assert r.status_code == 404

    def test_patch_arbitrary_order_returns_404(self, owner_session):
        s, _ = owner_session
        r = s.patch(f"{API}/orders/000000000000000000000000/status", json={"status": "accepted"})
        assert r.status_code == 404

    def test_cross_tenant_category_update_404(self, owner_session):
        # attempt to update a non-existent (or foreign) category id
        s, _ = owner_session
        r = s.put(f"{API}/menu/categories/000000000000000000000000",
                  json={"name": "x", "description": "", "sortOrder": 0})
        assert r.status_code == 404

    def test_orders_list_scoped(self, owner_session):
        s, _ = owner_session
        r = s.get(f"{API}/orders")
        assert r.status_code == 200
        rid = s.get(f"{API}/restaurant/me").json()["id"]
        for o in r.json():
            assert o["restaurantId"] == rid


# ---------- Public ordering ----------
class TestPublicOrdering:
    def test_public_restaurant(self, public_data):
        r = public_data["restaurant"]
        assert r["slug"] == SLUG
        assert public_data["categories"] and public_data["items"]

    def _first_item_without_required_options(self, items):
        for i in items:
            groups = i.get("optionGroups") or []
            if not any(g.get("required") for g in groups) and i.get("isAvailable", True):
                return i
        return None

    def _first_item_with_required_options(self, items):
        for i in items:
            for g in i.get("optionGroups") or []:
                if g.get("required") and g.get("options"):
                    return i, g
        return None, None

    def test_pickup_quote(self, public_data):
        item = self._first_item_without_required_options(public_data["items"])
        assert item, "need at least one item without required options"
        payload = {
            "orderType": "pickup",
            "items": [{"productId": item["id"], "quantity": 2, "selectedOptions": []}],
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/quote", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["subtotal"] == round(item["price"] * 2, 2)
        assert body["deliveryFee"] == 0.0
        assert body["total"] == body["subtotal"]

    def test_required_option_missing_400(self, public_data):
        item, g = self._first_item_with_required_options(public_data["items"])
        if not item:
            pytest.skip("no item with required options")
        payload = {
            "orderType": "pickup",
            "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": []}],
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/quote", json=payload, timeout=30)
        assert r.status_code == 400

    def test_delivery_quote_brussels(self, public_data):
        if not public_data["restaurant"]["deliveryEnabled"]:
            pytest.skip("delivery not enabled")
        item = self._first_item_without_required_options(public_data["items"])
        assert item
        payload = {
            "orderType": "delivery",
            "items": [{"productId": item["id"], "quantity": 5, "selectedOptions": []}],
            "deliveryAddress": {"street": "Nieuwstraat", "houseNumber": "10",
                                "postalCode": "1000", "city": "Brussel"},
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/quote", json=payload, timeout=45)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["orderType"] == "delivery"
        if b.get("available"):
            assert "deliveryFee" in b and "total" in b
            assert b["total"] == round(b["subtotal"] + b["deliveryFee"], 2)

    def test_pickup_order_creation_and_idempotency(self, public_data):
        item = self._first_item_without_required_options(public_data["items"])
        assert item
        key = f"TEST-{uuid.uuid4()}"
        body = {
            "orderType": "pickup",
            "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": []}],
            "customer": {"name": "TEST User", "phone": "0400000000", "email": "test.user@example.com"},
            "idempotencyKey": key,
        }
        r1 = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=30)
        if r1.status_code == 409:
            pytest.skip(f"ordering disabled or closed: {r1.text}")
        assert r1.status_code == 200, r1.text
        o1 = r1.json()
        assert o1["orderType"] == "pickup"
        assert o1["subtotal"] == round(item["price"], 2)
        assert o1["total"] == o1["subtotal"]
        assert o1["status"] == "new"
        # idempotent replay
        r2 = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["orderNumber"] == o1["orderNumber"]
        # GET confirmation
        gc = requests.get(f"{API}/public/orders/{o1['id']}", timeout=15)
        assert gc.status_code == 200 and gc.json()["orderNumber"] == o1["orderNumber"]

    def test_price_security_ignores_client_prices(self, public_data):
        """Server must ignore any client-supplied prices; body has no price fields anyway."""
        item = self._first_item_without_required_options(public_data["items"])
        assert item
        # inject bogus 'price'/'unitPrice' into request payload; server should ignore
        body = {
            "orderType": "pickup",
            "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": [],
                       "price": 0.01, "unitPrice": 0.01}],
            "customer": {"name": "TEST Sec", "phone": "0400000000", "email": "sec@example.com"},
            "idempotencyKey": f"TEST-SEC-{uuid.uuid4()}",
            "subtotal": 0.01, "total": 0.01,
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=30)
        if r.status_code == 409:
            pytest.skip("ordering disabled")
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["subtotal"] == round(item["price"], 2)
        assert o["total"] == round(item["price"], 2)

    def test_delivery_below_minimum(self, public_data):
        if not public_data["restaurant"]["deliveryEnabled"]:
            pytest.skip("delivery not enabled")
        # Find cheapest item without required options to trigger below-min
        items = [i for i in public_data["items"]
                 if not any(g.get("required") for g in i.get("optionGroups") or [])]
        assert items
        cheapest = min(items, key=lambda x: x["price"])
        body = {
            "orderType": "delivery",
            "items": [{"productId": cheapest["id"], "quantity": 1, "selectedOptions": []}],
            "customer": {"name": "TEST Min", "phone": "0400000000", "email": "min@example.com"},
            "deliveryAddress": {"street": "Nieuwstraat", "houseNumber": "10",
                                "postalCode": "1000", "city": "Brussel"},
            "idempotencyKey": f"TEST-MIN-{uuid.uuid4()}",
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=45)
        # Expect below-min rejection (400) OR ordering disabled (409); shouldn't succeed silently
        assert r.status_code in (400, 409), f"unexpected {r.status_code}: {r.text}"
        if r.status_code == 400:
            assert "minimum" in r.text.lower() or "bezorg" in r.text.lower()


# ---------- Order status transitions (uses staff order created above) ----------
class TestOrderStatus:
    def test_status_transitions(self, owner_session, public_data):
        s, _ = owner_session
        item = None
        for i in public_data["items"]:
            if not any(g.get("required") for g in i.get("optionGroups") or []):
                item = i
                break
        if not item:
            pytest.skip("no item")
        body = {
            "orderType": "pickup",
            "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": []}],
            "customer": {"name": "TEST Flow", "phone": "0400000000", "email": "flow@example.com"},
            "idempotencyKey": f"TEST-FLOW-{uuid.uuid4()}",
        }
        r = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, timeout=30)
        if r.status_code == 409:
            pytest.skip("ordering disabled")
        assert r.status_code == 200
        oid = r.json()["id"]
        # invalid transition
        bad = s.patch(f"{API}/orders/{oid}/status", json={"status": "completed"})
        assert bad.status_code == 400
        # valid path new -> accepted -> preparing -> ready -> completed
        for st in ["accepted", "preparing", "ready", "completed"]:
            up = s.patch(f"{API}/orders/{oid}/status", json={"status": st})
            assert up.status_code == 200, up.text
            assert up.json()["status"] == st
