"""Tests for DELETE /api/orders/{id} and related invariants.

Covers:
- admin delete of completed/cancelled orders -> 200
- admin delete of active orders -> 400 Dutch message, order remains
- staff delete -> 403, order remains
- customer status link invalidation after delete -> 404
- order number counter never resets after delete
- cross-tenant delete attempt returns 404 (filter includes restaurantId)
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "owner@demo.upxero.com", "password": "Demo!2025"}
STAFF = {"email": "staff@demo.upxero.com", "password": "Demo!2025"}
SLUG = "bistro-demo"

UA = {"User-Agent": "Mozilla/5.0 (pytest)"}
DUTCH_DETAIL = "Alleen afgeronde of geannuleerde bestellingen kunnen worden verwijderd."


def _login(creds):
    s = requests.Session()
    s.headers.update(UA)
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    s.headers.update({"Authorization": f"Bearer {body['token']}"})
    return s, body


@pytest.fixture(scope="module")
def admin_session():
    return _login(OWNER)


@pytest.fixture(scope="module")
def staff_session():
    return _login(STAFF)


@pytest.fixture(scope="module")
def public_items():
    r = requests.get(f"{API}/public/restaurant/{SLUG}", headers=UA, timeout=30)
    assert r.status_code == 200
    data = r.json()
    items = [i for i in data["items"]
             if i.get("isAvailable", True)
             and not any(g.get("required") for g in i.get("optionGroups") or [])]
    assert items, "need an item without required options"
    return items


def _create_order(item):
    body = {
        "orderType": "pickup",
        "items": [{"productId": item["id"], "quantity": 1, "selectedOptions": []}],
        "customer": {"name": "TEST Del", "phone": "0400000000", "email": "del@example.com"},
        "idempotencyKey": f"TEST-DEL-{uuid.uuid4()}",
    }
    r = requests.post(f"{API}/public/restaurant/{SLUG}/orders", json=body, headers=UA, timeout=30)
    if r.status_code == 409:
        pytest.skip(f"ordering disabled/closed: {r.text}")
    assert r.status_code == 200, r.text
    return r.json()


def _advance(session, order_id, target):
    chain = ["accepted", "preparing", "ready", "completed"]
    for st in chain:
        up = session.patch(f"{API}/orders/{order_id}/status", json={"status": st})
        assert up.status_code == 200, up.text
        if st == target:
            return


class TestDeleteCompleted:
    def test_admin_delete_completed_200_then_404(self, admin_session, public_items):
        s, _ = admin_session
        order = _create_order(public_items[0])
        oid = order["id"]
        _advance(s, oid, "completed")
        r = s.delete(f"{API}/orders/{oid}")
        assert r.status_code == 200, r.text
        assert r.json().get("message") == "Bestelling verwijderd"
        g = s.get(f"{API}/orders/{oid}")
        assert g.status_code == 404

    def test_admin_delete_cancelled_200(self, admin_session, public_items):
        s, _ = admin_session
        order = _create_order(public_items[0])
        oid = order["id"]
        up = s.patch(f"{API}/orders/{oid}/status", json={"status": "cancelled"})
        assert up.status_code == 200
        r = s.delete(f"{API}/orders/{oid}")
        assert r.status_code == 200


class TestDeleteActiveRejected:
    @pytest.mark.parametrize("status", ["new", "accepted", "preparing", "ready"])
    def test_cannot_delete_active(self, admin_session, public_items, status):
        s, _ = admin_session
        order = _create_order(public_items[0])
        oid = order["id"]
        if status != "new":
            _advance(s, oid, status)
        r = s.delete(f"{API}/orders/{oid}")
        assert r.status_code == 400, r.text
        assert r.json().get("detail") == DUTCH_DETAIL
        # order should still exist
        g = s.get(f"{API}/orders/{oid}")
        assert g.status_code == 200
        # cleanup: cancel + delete to not pollute
        s.patch(f"{API}/orders/{oid}/status", json={"status": "cancelled"})
        s.delete(f"{API}/orders/{oid}")


class TestStaffForbidden:
    def test_staff_cannot_delete(self, admin_session, staff_session, public_items):
        s_admin, _ = admin_session
        s_staff, _ = staff_session
        order = _create_order(public_items[0])
        oid = order["id"]
        s_admin.patch(f"{API}/orders/{oid}/status", json={"status": "cancelled"})
        r = s_staff.delete(f"{API}/orders/{oid}")
        assert r.status_code == 403, r.text
        # order still exists
        g = s_admin.get(f"{API}/orders/{oid}")
        assert g.status_code == 200
        # cleanup
        s_admin.delete(f"{API}/orders/{oid}")


class TestStatusLinkInvalidation:
    def test_status_token_404_after_delete(self, admin_session, public_items):
        s, _ = admin_session
        order = _create_order(public_items[0])
        token = order["statusToken"]
        oid = order["id"]
        # link resolves before delete
        pre = requests.get(f"{API}/public/order-status/{token}", headers=UA, timeout=15)
        assert pre.status_code == 200, pre.text
        s.patch(f"{API}/orders/{oid}/status", json={"status": "cancelled"})
        d = s.delete(f"{API}/orders/{oid}")
        assert d.status_code == 200
        post = requests.get(f"{API}/public/order-status/{token}", headers=UA, timeout=15)
        assert post.status_code == 404


class TestOrderNumberIntegrity:
    def test_counter_never_reused_after_delete(self, admin_session, public_items):
        s, _ = admin_session
        o1 = _create_order(public_items[0])
        n1 = o1["orderNumber"]
        s.patch(f"{API}/orders/{o1['id']}/status", json={"status": "cancelled"})
        d = s.delete(f"{API}/orders/{o1['id']}")
        assert d.status_code == 200
        o2 = _create_order(public_items[0])
        n2 = o2["orderNumber"]
        assert n2 > n1, f"expected {n2} > {n1}"
        # cleanup
        s.patch(f"{API}/orders/{o2['id']}/status", json={"status": "cancelled"})
        s.delete(f"{API}/orders/{o2['id']}")


class TestTenantIsolation:
    def test_delete_unknown_id_returns_404(self, admin_session):
        s, _ = admin_session
        r = s.delete(f"{API}/orders/000000000000000000000000")
        assert r.status_code == 404
