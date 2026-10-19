# Platform admin controls (detail/activate/edit/audit) + owner deletion request workflow.
# Only TEST_ restaurants are mutated. Real restaurants are only hit with requests that must be rejected.
import os
import uuid

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

RAND = uuid.uuid4().hex[:6]
T = {"name": f"TEST_Resto {RAND}", "email": f"test_owner_{RAND}@upxerotest.com", "pw": "TestPass!123"}
ALL_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


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


@pytest.fixture(scope="module")
def real_rid(owner):
    return owner.get(f"{API}/restaurant/me").json()["id"]


# ---------- Authz: non-super-admins rejected on all admin endpoints ----------
class TestAdminAuthz:
    def endpoints(self, rid):
        return [
            ("get", f"/admin/restaurants", None), ("get", f"/admin/restaurants/{rid}", None),
            ("patch", f"/admin/restaurants/{rid}/active", {"isActive": False}),
            ("put", f"/admin/restaurants/{rid}", {"name": "HACKED"}),
            ("post", f"/admin/deletion-requests/{'0'*24}/approve", {"confirmText": "x"}),
            ("post", f"/admin/deletion-requests/{'0'*24}/reject", {"reason": "x"}),
            ("get", "/admin/users", None),
        ]

    @pytest.mark.parametrize("who", ["owner", "staff", "anon"])
    def test_rejected(self, who, request, real_rid):
        s = requests.Session() if who == "anon" else request.getfixturevalue(who)
        for m, path, body in self.endpoints(real_rid):
            r = getattr(s, m)(f"{API}{path}", json=body) if body is not None else getattr(s, m)(f"{API}{path}")
            exp = 401 if who == "anon" else 403
            assert r.status_code == exp, f"{who} {m} {path} -> {r.status_code}"
        r = MONGO.restaurants.find_one({"_id": ObjectId(real_rid)})
        assert r["isActive"] is True and r["name"] != "HACKED"

    def test_staff_deletion_request_forbidden(self, staff):
        assert staff.get(f"{API}/restaurant/deletion-request").status_code == 403
        assert staff.post(f"{API}/restaurant/deletion-request",
                          json={"type": "restaurant", "password": STAFF[1], "confirmText": "Bistro Demo"}).status_code == 403
        assert staff.delete(f"{API}/restaurant/deletion-request").status_code == 403


# ---------- Full lifecycle on a TEST_ restaurant ----------
class TestLifecycle:
    state = {}

    def test_01_create_and_detail(self, admin):
        r = admin.post(f"{API}/admin/restaurants", json={"restaurantName": T["name"], "ownerName": "Test Owner",
                                                         "email": T["email"], "password": T["pw"]})
        assert r.status_code == 200, r.text
        d = r.json()
        self.state.update(rid=d["id"], slug=d["slug"])
        r = admin.get(f"{API}/admin/restaurants/{d['id']}")
        assert r.status_code == 200
        det = r.json()
        txt = r.text
        assert "passwordHash" not in txt and "tokenVersion" not in txt
        assert det["owner"]["email"] == T["email"]
        assert det["orderCount"] == 0 and len(det["users"]) == 1
        assert det["restaurant"]["createdAt"]
        assert any(a["action"] == "restaurant.created" for a in det["auditLog"])
        lst = admin.get(f"{API}/admin/restaurants").json()
        assert any(x["id"] == d["id"] for x in lst)
        assert admin.get(f"{API}/admin/restaurants/{'0'*24}").status_code == 404

    def test_02_setup_menu_and_orders(self):
        o = login(T["email"], T["pw"])
        self.state["owner"] = o
        assert o.put(f"{API}/restaurant/settings", json={"orderingEnabled": True, "pickupEnabled": True,
                     "orderEmailsEnabled": False, "customerEmailsEnabled": False}).status_code == 200
        hours = {d: {"closed": False, "open": "00:00", "close": "00:00"} for d in ALL_DAYS}
        assert o.put(f"{API}/restaurant/opening-hours", json=hours).status_code == 200
        c = o.post(f"{API}/menu/categories", json={"name": "TEST_cat"})
        assert c.status_code == 200, c.text
        i = o.post(f"{API}/menu/items", json={"categoryId": c.json()["id"], "name": "TEST_item", "price": 9.5})
        assert i.status_code == 200, i.text
        self.state["item"] = i.json()["id"]
        self.state["orders"] = []
        for n in range(2):
            r = requests.post(f"{API}/public/restaurant/{self.state['slug']}/orders", json={
                "orderType": "pickup", "items": [{"productId": self.state["item"], "quantity": 2}],
                "customer": {"name": f"TEST_Cust{n}", "phone": "+32470000000", "email": f"test_c{n}@upxerotest.com"},
                "notes": "ring bell"})
            assert r.status_code == 200, r.text
            self.state["orders"].append(r.json())
        doc = MONGO.orders.find_one({"restaurantId": self.state["rid"]})
        assert doc and doc.get("statusTokenHash")

    def test_03_deactivate_reactivate(self, admin):
        rid, slug = self.state["rid"], self.state["slug"]
        r = admin.patch(f"{API}/admin/restaurants/{rid}/active", json={"isActive": False})
        assert r.status_code == 200 and r.json()["isActive"] is False
        assert requests.get(f"{API}/public/restaurant/{slug}").status_code == 404
        assert self.state["owner"].get(f"{API}/restaurant/me").json()["isActive"] is False
        assert MONGO.menu_items.count_documents({"restaurantId": rid}) == 1
        assert MONGO.orders.count_documents({"restaurantId": rid}) == 2
        r = admin.patch(f"{API}/admin/restaurants/{rid}/active", json={"isActive": True})
        assert r.status_code == 200
        assert requests.get(f"{API}/public/restaurant/{slug}").status_code == 200
        acts = [(a["action"], a["actorEmail"]) for a in admin.get(f"{API}/admin/restaurants/{rid}").json()["auditLog"]]
        assert ("restaurant.deactivated", ADMIN[0]) in acts and ("restaurant.activated", ADMIN[0]) in acts

    def test_04_admin_edit(self, admin):
        rid = self.state["rid"]
        new_name = T["name"] + " X"
        body = {"name": new_name, "phone": "+3211111111", "description": "", "email": T["email"], "street": "",
                "houseNumber": "", "postalCode": "", "city": "", "country": "BE", "defaultLanguage": "en"}
        r = admin.put(f"{API}/admin/restaurants/{rid}", json=body)
        assert r.status_code == 200 and r.json()["name"] == new_name and r.json()["phone"] == "+3211111111"
        T["name"] = new_name
        logs = admin.get(f"{API}/admin/restaurants/{rid}").json()["auditLog"]
        upd = [a for a in logs if a["action"] == "restaurant.updated"]
        assert upd and set(upd[0]["details"]["fields"]) == {"name", "phone"}
        assert admin.put(f"{API}/admin/restaurants/{rid}", json={"name": "x"}).status_code == 422

    def test_05_owner_requests(self, admin, owner):
        o = self.state["owner"]
        url = f"{API}/restaurant/deletion-request"
        r = o.post(url, json={"type": "account", "password": T["pw"], "confirmText": T["email"]})
        assert r.status_code == 400 and "enige" in r.json()["detail"]
        r = o.post(url, json={"type": "restaurant", "password": "wrong", "confirmText": T["name"]})
        assert r.status_code == 400
        r = o.post(url, json={"type": "restaurant", "password": T["pw"], "confirmText": "nope"})
        assert r.status_code == 400
        r = o.post(url, json={"type": "restaurant", "password": T["pw"], "confirmText": T["name"]})
        assert r.status_code == 200, r.text
        assert o.get(url).json()["request"]["status"] == "pending"
        assert o.post(url, json={"type": "restaurant", "password": T["pw"], "confirmText": T["name"]}).status_code == 400
        # Bistro owner doesn't see TEST request
        assert owner.get(url).json()["request"] is None
        # withdraw
        assert o.delete(url).status_code == 200
        assert o.get(url).json()["request"] is None
        assert o.delete(url).status_code == 404
        # new request -> admin reject
        r = o.post(url, json={"type": "restaurant", "password": T["pw"], "confirmText": T["name"]})
        req_id = r.json()["request"]["id"]
        assert admin.post(f"{API}/admin/deletion-requests/{req_id}/reject", json={"reason": "TEST"}).status_code == 200
        assert MONGO.deletion_requests.find_one({"_id": ObjectId(req_id)})["status"] == "rejected"
        assert admin.post(f"{API}/admin/deletion-requests/{req_id}/approve", json={"confirmText": T["name"]}).status_code == 404
        # new request -> pendingDeletion flag
        r = o.post(url, json={"type": "restaurant", "password": T["pw"], "confirmText": T["name"]})
        self.state["req"] = r.json()["request"]["id"]
        lst = admin.get(f"{API}/admin/restaurants").json()
        assert next(x for x in lst if x["id"] == self.state["rid"])["pendingDeletion"] is True

    def test_06_approve(self, admin):
        rid, req = self.state["rid"], self.state["req"]
        r = admin.post(f"{API}/admin/deletion-requests/{req}/approve", json={"confirmText": "wrong name"})
        assert r.status_code == 400
        r = admin.post(f"{API}/admin/deletion-requests/{req}/approve", json={"confirmText": T["name"]})
        assert r.status_code == 200, r.text
        s = r.json()["summary"]
        assert s["ordersAnonymised"] == 2 and s["menuItemsDeleted"] == 1 and s["categoriesDeleted"] == 1 and s["usersAnonymised"] == 1
        for od in MONGO.orders.find({"restaurantId": rid}):
            assert od["orderNumber"] and od["items"] and od["total"] > 0
            assert od["customer"]["name"] == "Anonymised" and od["customer"]["phone"] == "" and od["customer"]["email"] == ""
            assert od["deliveryAddress"] is None and od["notes"] == ""
            assert "statusTokenHash" not in od
        assert MONGO.menu_items.count_documents({"restaurantId": rid}) == 0
        assert MONGO.menu_categories.count_documents({"restaurantId": rid}) == 0
        rd = MONGO.restaurants.find_one({"_id": ObjectId(rid)})
        assert rd["isActive"] is False and rd.get("deletedAt") and rd["email"] == "" and rd["phone"] == ""
        u = MONGO.users.find_one({"restaurantId": rid})
        assert u["email"] == f"deleted-{u['_id']}@deleted.invalid" and u["passwordHash"] == "" and u["isActive"] is False
        assert u.get("tokenVersion", 0) >= 1
        assert requests.post(f"{API}/auth/login", json={"email": T["email"], "password": T["pw"]}).status_code == 401
        assert self.state["owner"].get(f"{API}/restaurant/me").status_code == 401
        assert requests.get(f"{API}/public/restaurant/{self.state['slug']}").status_code == 404
        assert admin.patch(f"{API}/admin/restaurants/{rid}/active", json={"isActive": True}).status_code == 400
        assert admin.put(f"{API}/admin/restaurants/{rid}", json={"name": "TEST_again"}).status_code == 400
        assert MONGO.deletion_requests.find_one({"_id": ObjectId(req)})["status"] == "completed"
        # Old status token no longer resolves
        tok = self.state["orders"][0].get("statusToken")
        if tok:
            assert requests.get(f"{API}/public/order-status/{tok}").status_code == 404
        # Now the email is free again
        assert MONGO.users.count_documents({"email": T["email"]}) == 0


# ---------- Account-type request with second admin ----------
class TestAccountRequest:
    def test_account_deletion_with_two_admins(self, admin):
        rnd = uuid.uuid4().hex[:6]
        name, e1, e2 = f"TEST_Acct {rnd}", f"test_owner_{rnd}@upxerotest.com", f"test_owner2_{rnd}@upxerotest.com"
        r = admin.post(f"{API}/admin/restaurants", json={"restaurantName": name, "ownerName": "Owner A", "email": e1, "password": T["pw"]})
        assert r.status_code == 200, r.text
        rid = r.json()["id"]
        from security import hash_password  # noqa
        MONGO.users.insert_one({"email": e2, "passwordHash": hash_password(T["pw"]), "name": "B", "role": "restaurant_admin",
                                "restaurantId": rid, "isActive": True, "createdAt": "2026-01-01T00:00:00+00:00"})
        o = login(e2, T["pw"])
        r = o.post(f"{API}/restaurant/deletion-request", json={"type": "account", "password": T["pw"], "confirmText": e2})
        assert r.status_code == 200, r.text
        req = r.json()["request"]["id"]
        assert admin.post(f"{API}/admin/deletion-requests/{req}/approve", json={"confirmText": name}).status_code == 200
        assert requests.post(f"{API}/auth/login", json={"email": e2, "password": T["pw"]}).status_code == 401
        assert MONGO.restaurants.find_one({"_id": ObjectId(rid)})["isActive"] is True
        login(e1, T["pw"])  # other admin still works
