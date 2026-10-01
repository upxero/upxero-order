"""Tests for restaurant.defaultLanguage: EN default for new restaurants, NL for demo,
public payload exposure, language on order status/confirmation, and Profile PUT persistence."""
import os
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
UA = {"User-Agent": "Mozilla/5.0 TestAgent"}

SUPER = {"email": "mike.upxero@gmail.com", "password": "Upxero!Admin2025"}
OWNER = {"email": "owner@demo.upxero.com", "password": "Demo!2025"}


def _login(creds):
    s = requests.Session()
    s.headers.update(UA)
    r = s.post(f"{API}/auth/login", json=creds)
    assert r.status_code == 200, r.text
    return s


# ----- English default on new restaurant -----

def test_new_restaurant_defaults_to_english_and_demo_stays_dutch():
    s = _login(SUPER)
    body = {
        "restaurantName": f"TEST_LangDefault_{uuid.uuid4().hex[:8]}",
        "ownerName": "Lang Tester",
        "email": f"lang-{uuid.uuid4().hex[:8]}@example.com",
        "password": "LangTest!2025",
    }
    r = s.post(f"{API}/admin/restaurants", json=body)
    assert r.status_code in (200, 201), r.text
    created = r.json()
    # defaultLanguage must be 'en' for new restaurants
    assert created.get("defaultLanguage") == "en", f"expected en, got {created.get('defaultLanguage')}"
    new_id = created.get("id") or created.get("_id")

    # Demo bistro must still be 'nl'
    pub = requests.get(f"{API}/public/restaurant/bistro-demo", headers=UA)
    assert pub.status_code == 200
    assert pub.json()["restaurant"]["defaultLanguage"] == "nl"

    # cleanup: delete created restaurant
    if new_id:
        s.delete(f"{API}/admin/restaurants/{new_id}")


# ----- Public payload exposes language on order status / confirmation -----

def _place_order_on_demo():
    """Create a public order on bistro-demo (pickup, uses existing menu)."""
    pub = requests.get(f"{API}/public/restaurant/bistro-demo", headers=UA).json()
    items = [i for i in pub["items"] if i.get("isAvailable", True)]
    assert items, "demo must have an available menu item"
    it = items[0]
    sel = []
    for g in it.get("optionGroups", []):
        if g.get("required") and g.get("options"):
            sel.append({"groupId": g["id"], "optionId": g["options"][0]["id"]})
    payload = {
        "orderType": "pickup",
        "customer": {"name": "TEST Lang", "phone": "+32470000000", "email": "testlang@example.com"},
        "items": [{"productId": it["id"], "quantity": 1, "selectedOptions": sel}],
        "notes": "lang-test",
        "idempotencyKey": uuid.uuid4().hex,
    }
    r = requests.post(f"{API}/public/restaurant/bistro-demo/orders", json=payload, headers=UA)
    assert r.status_code == 200, r.text
    return r.json()


def test_public_order_status_and_confirmation_include_language():
    order = _place_order_on_demo()
    token = order["statusToken"]
    order_id = order["id"]

    status = requests.get(f"{API}/public/order-status/{token}", headers=UA)
    assert status.status_code == 200
    assert status.json().get("language") == "nl"

    conf = requests.get(f"{API}/public/orders/{order_id}", headers=UA)
    assert conf.status_code == 200
    assert conf.json().get("language") == "nl"


# ----- Profile PUT persists defaultLanguage -----

def _profile_body(me: dict, **overrides) -> dict:
    """Build a valid ProfileReq body preserving existing fields."""
    body = {
        "name": me.get("name", ""),
        "description": me.get("description", ""),
        "phone": me.get("phone", ""),
        "email": me.get("email", ""),
        "street": me.get("street", ""),
        "houseNumber": me.get("houseNumber", ""),
        "postalCode": me.get("postalCode", ""),
        "city": me.get("city", ""),
        "country": me.get("country", "BE"),
        "defaultLanguage": me.get("defaultLanguage", "nl"),
    }
    body.update(overrides)
    return body


def test_profile_language_switch_persists_and_reverts():
    s = _login(OWNER)

    # Read current
    me = s.get(f"{API}/restaurant/me")
    assert me.status_code == 200
    me_json = me.json()
    original = me_json.get("defaultLanguage", "nl")

    try:
        # Switch to English
        r = s.put(f"{API}/restaurant/profile", json=_profile_body(me_json, defaultLanguage="en"))
        assert r.status_code == 200, r.text
        me_json = s.get(f"{API}/restaurant/me").json()
        assert me_json["defaultLanguage"] == "en"

        # Public payload reflects it
        pub = requests.get(f"{API}/public/restaurant/bistro-demo", headers=UA).json()
        assert pub["restaurant"]["defaultLanguage"] == "en"

        # Order placed now must report english language
        order = _place_order_on_demo()
        status = requests.get(f"{API}/public/order-status/{order['statusToken']}", headers=UA).json()
        assert status["language"] == "en"

        # Switch back
        r = s.put(f"{API}/restaurant/profile", json=_profile_body(me_json, defaultLanguage="nl"))
        assert r.status_code == 200
        me_json = s.get(f"{API}/restaurant/me").json()
        assert me_json["defaultLanguage"] == "nl"
    finally:
        # Guarantee demo baseline reset to original
        me_json = s.get(f"{API}/restaurant/me").json()
        s.put(f"{API}/restaurant/profile", json=_profile_body(me_json, defaultLanguage=original))
        final = s.get(f"{API}/restaurant/me").json()
        assert final["defaultLanguage"] == original == "nl"
