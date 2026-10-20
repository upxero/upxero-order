# Restaurant deletion lifecycle: platform list filter, archived listing, retention-gated purge, tombstone, authz.
# Only TEST_ restaurants are mutated. Run cleanup_test_purge.py afterwards.
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
MONGO = MongoClient(os.environ.get("MONGO_URL"))[os.environ.get("DB_NAME")]

ADMIN = ("mike.upxero@gmail.com", "Upxero!Admin2025")
OWNER = ("owner@demo.upxero.com", "Demo!2025")
STAFF = ("staff@demo.upxero.com", "Demo!2025")
ALL_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
PW = "TestPass!123"
RAND = uuid.uuid4().hex[:6]
T = {"name": f"TEST_Purge {RAND}", "email": f"test_purge_{RAND}@upxerotest.com"}


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


@pytest.fixture(scope="module")
def admin():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def owner():
    return login(*OWNER)


@pytest.fixture(scope="module")
def staff():
    return login(*STAFF)


# ---------- Super admin login + role ----------
def test_admin_login_role(admin):
    me = admin.get(f"{API}/auth/me").json()
    me = me.get("user", me)
    assert me["role"] == "super_admin"


# ---------- Authz on new endpoints ----------
@pytest.mark.parametrize("who", ["owner", "staff", "anon"])
def test_authz_archived_and_purge(who, request):
    s = requests.Session() if who == "anon" else request.getfixturevalue(who)
    exp = 401 if who == "anon" else 403
    assert s.get(f"{API}/admin/restaurants/archived").status_code == exp
    assert s.post(f"{API}/admin/restaurants/{'0'*24}/purge", json={"confirmText": "x"}).status_code == exp


def test_purge_unknown_and_non_deleted(admin):
    assert admin.post(f"{API}/admin/restaurants/{'0'*24}/purge", json={"confirmText": "x"}).status_code == 404
    bistro = MONGO.restaurants.find_one({"slug": "bistro-demo"})
    r = admin.post(f"{API}/admin/restaurants/{bistro['_id']}/purge", json={"confirmText": "Bistro Demo"})
    assert r.status_code == 400
    assert MONGO.restaurants.find_one({"_id": bistro["_id"]}).get("deletedAt") is None


class TestPurgeLifecycle:
    st = {}

    def test_01_create_with_data(self, admin):
        r = admin.post(f"{API}/admin/restaurants", json={"restaurantName": T["name"], "ownerName": "TEST Owner",
                                                         "email": T["email"], "password": PW})
        assert r.status_code == 200, r.text
        self.st.update(rid=r.json()["id"], slug=r.json()["slug"])
        o = login(T["email"], PW)
        self.st["owner"] = o
        assert o.put(f"{API}/restaurant/settings", json={"orderingEnabled": True, "pickupEnabled": True,
                     "orderEmailsEnabled": False, "customerEmailsEnabled": False}).status_code == 200
        hours = {d: {"closed": False, "open": "00:00", "close": "00:00"} for d in ALL_DAYS}
        assert o.put(f"{API}/restaurant/opening-hours", json=hours).status_code == 200
        c = o.post(f"{API}/menu/categories", json={"name": "TEST_cat"}).json()
        item = o.post(f"{API}/menu/items", json={"categoryId": c["id"], "name": "TEST_item", "price": 7.0}).json()
        self.st["item"] = item["id"]
        r = requests.post(f"{API}/public/restaurant/{self.st['slug']}/orders", json={
            "orderType": "pickup", "items": [{"productId": item["id"], "quantity": 1}],
            "customer": {"name": "TEST_Cust", "phone": "+32470000000", "email": "test_c@upxerotest.com"}})
        assert r.status_code == 200, r.text
        assert MONGO.counters.find_one({"_id": f"orders:{self.st['rid']}"}) is not None

    def test_02_request_and_approve(self, admin):
        o = self.st["owner"]
        r = o.post(f"{API}/restaurant/deletion-request", json={"type": "restaurant", "password": PW, "confirmText": T["name"]})
        assert r.status_code == 200, r.text
        req = r.json()["request"]["id"]
        self.st["req"] = req
        r = admin.post(f"{API}/admin/deletion-requests/{req}/approve", json={"confirmText": T["name"]})
        assert r.status_code == 200, r.text

    def test_03_list_filter_and_archive(self, admin):
        rid = self.st["rid"]
        assert not any(x["id"] == rid for x in admin.get(f"{API}/admin/restaurants").json())
        arc = admin.get(f"{API}/admin/restaurants/archived").json()
        assert arc["retentionDays"] == 30
        e = next(x for x in arc["restaurants"] if x["id"] == rid)
        deleted = datetime.fromisoformat(e["deletedAt"])
        assert abs((datetime.fromisoformat(e["purgeEligibleAt"]) - deleted) - timedelta(days=30)) < timedelta(seconds=1)
        assert e["canPurge"] is False and e["purgedAt"] is None and e["orderCount"] == 1
        assert e["name"] == T["name"] and e["slug"] == self.st["slug"]

    def test_04_blocked_actions(self, admin):
        rid, slug = self.st["rid"], self.st["slug"]
        r = admin.post(f"{API}/admin/restaurants/{rid}/purge", json={"confirmText": T["name"]})
        assert r.status_code == 400 and "bewaartermijn" in r.json()["detail"]
        assert admin.post(f"{API}/admin/restaurants/{rid}/purge", json={"confirmText": "wrong"}).status_code == 400
        assert admin.patch(f"{API}/admin/restaurants/{rid}/active", json={"isActive": True}).status_code == 400
        assert requests.get(f"{API}/public/restaurant/{slug}").status_code == 404
        r = requests.post(f"{API}/public/restaurant/{slug}/orders", json={
            "orderType": "pickup", "items": [{"productId": self.st["item"], "quantity": 1}],
            "customer": {"name": "X", "phone": "+32470000000", "email": "x@upxerotest.com"}})
        assert r.status_code in (404, 400, 409)
        assert MONGO.orders.count_documents({"restaurantId": rid}) == 1
        assert MONGO.restaurants.find_one({"_id": ObjectId(rid)}).get("purgedAt") is None

    def test_05_backdate_and_purge(self, admin):
        rid = self.st["rid"]
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        MONGO.restaurants.update_one({"_id": ObjectId(rid)}, {"$set": {"deletedAt": old}})
        e = next(x for x in admin.get(f"{API}/admin/restaurants/archived").json()["restaurants"] if x["id"] == rid)
        assert e["canPurge"] is True
        # case-insensitive / whitespace tolerant confirm
        r = admin.post(f"{API}/admin/restaurants/{rid}/purge", json={"confirmText": f"  {T['name'].upper()} "})
        assert r.status_code == 200, r.text
        s = r.json()["summary"]
        assert s["userRecordsDeleted"] == 1

    def test_06_verify_mongo_after_purge(self, admin):
        rid = self.st["rid"]
        assert MONGO.users.count_documents({"restaurantId": rid}) == 0
        assert MONGO.menu_items.count_documents({"restaurantId": rid}) == 0
        assert MONGO.menu_categories.count_documents({"restaurantId": rid}) == 0
        assert MONGO.counters.find_one({"_id": f"orders:{rid}"}) is None
        doc = MONGO.restaurants.find_one({"_id": ObjectId(rid)})
        keys = set(doc) - {"_id"}
        assert keys == {"name", "slug", "country", "createdAt", "deletedAt", "isActive", "orderingEnabled",
                        "pickupEnabled", "deliveryEnabled", "purgedAt", "updatedAt"}, keys
        assert doc["purgedAt"] and doc["isActive"] is False and doc["name"] == T["name"]
        orders = list(MONGO.orders.find({"restaurantId": rid}))
        assert len(orders) == 1 and orders[0]["customer"]["name"] == "Anonymised" and orders[0]["customer"]["email"] == ""
        assert MONGO.deletion_requests.count_documents({"restaurantId": rid}) >= 1
        acts = {a["action"] for a in MONGO.audit_logs.find({"restaurantId": {"$in": [rid, ObjectId(rid)]}})}
        assert "restaurant.purged" in acts and "deletion.completed" in acts
        e = next(x for x in admin.get(f"{API}/admin/restaurants/archived").json()["restaurants"] if x["id"] == rid)
        assert e["purgedAt"] and e["canPurge"] is False
        # detail of tombstone still works
        assert admin.get(f"{API}/admin/restaurants/{rid}").status_code == 200

    def test_07_idempotent(self, admin):
        rid = self.st["rid"]
        r = admin.post(f"{API}/admin/restaurants/{rid}/purge", json={"confirmText": T["name"]})
        assert r.status_code == 200 and r.json().get("alreadyPurged") is True
        assert requests.get(f"{API}/public/restaurant/{self.st['slug']}").status_code == 404
