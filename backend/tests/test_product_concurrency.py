# Stage 3: concurrency fix for the 20-active-product Free limit (PATCH availability + POST create races). LIVE API.
import os
import uuid
import concurrent.futures as cf

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0]
API = f"{BASE_URL.strip().strip(chr(34)).rstrip('/')}/api"


def _env(k):
    for line in open("/app/backend/.env"):
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip().strip('"')


mdb = MongoClient(_env("MONGO_URL"))[_env("DB_NAME")]


def hdr(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture
def free_rest():
    rnd = uuid.uuid4().hex[:8]
    email = f"test_conc_{rnd}@upxerotest.com"
    r = requests.post(f"{API}/auth/register", json={"restaurantName": f"TEST_Conc {rnd}", "name": "TEST Owner",
                                                     "email": email, "password": "Test!2025x"}, timeout=20)
    assert r.status_code in (200, 201), r.text
    tok = r.json()["token"]
    me = requests.get(f"{API}/restaurant/me", headers=hdr(tok), timeout=20).json()
    assert me["plan"] == "free"
    cat = requests.post(f"{API}/menu/categories", json={"name": "TEST_Cat", "sortOrder": 0, "isActive": True}, headers=hdr(tok), timeout=20).json()["id"]
    rid = me["id"]
    # seed 19 active + 5 inactive directly
    docs = [{"restaurantId": rid, "categoryId": cat, "name": f"TEST_A{i}", "price": 5.0, "isAvailable": True,
             "optionGroups": [], "sortOrder": i} for i in range(19)]
    docs += [{"restaurantId": rid, "categoryId": cat, "name": f"TEST_I{i}", "price": 5.0, "isAvailable": False,
              "optionGroups": [], "sortOrder": 100 + i} for i in range(5)]
    mdb.menu_items.insert_many(docs)
    yield {"tok": tok, "rid": rid, "cat": cat}
    mdb.menu_items.delete_many({"restaurantId": rid})
    mdb.menu_categories.delete_many({"restaurantId": rid})
    mdb.users.delete_many({"email": email})
    mdb.restaurants.delete_one({"_id": __import__("bson").ObjectId(rid)})


def active(rid):
    return mdb.menu_items.count_documents({"restaurantId": rid, "isAvailable": True})


def test_concurrent_patch_activation(free_rest):
    rid, h = free_rest["rid"], hdr(free_rest["tok"])
    inactive = [str(d["_id"]) for d in mdb.menu_items.find({"restaurantId": rid, "isAvailable": False})]
    assert active(rid) == 19 and len(inactive) == 5
    with cf.ThreadPoolExecutor(5) as ex:
        res = list(ex.map(lambda i: requests.patch(f"{API}/menu/items/{i}/availability", json={"isAvailable": True}, headers=h, timeout=30), inactive))
    codes = [r.status_code for r in res]
    print("PATCH codes", codes, "active", active(rid))
    assert all(c in (200, 403) for c in codes), codes
    assert active(rid) <= 20
    assert active(rid) == 19 + codes.count(200)


def test_concurrent_create(free_rest):
    rid, h, cat = free_rest["rid"], hdr(free_rest["tok"]), free_rest["cat"]
    before_total = mdb.menu_items.count_documents({"restaurantId": rid})
    body = lambda i: {"categoryId": cat, "name": f"TEST_New{i}", "price": 4.0, "isAvailable": True}
    with cf.ThreadPoolExecutor(5) as ex:
        res = list(ex.map(lambda i: requests.post(f"{API}/menu/items", json=body(i), headers=h, timeout=30), range(5)))
    codes = [r.status_code for r in res]
    print("POST codes", codes, "active", active(rid))
    assert all(c in (200, 403) for c in codes), codes
    assert active(rid) <= 20
    # losers deleted: total grows only by successes
    assert mdb.menu_items.count_documents({"restaurantId": rid}) == before_total + codes.count(200)
    assert mdb.menu_items.count_documents({"restaurantId": rid, "name": {"$regex": "^TEST_New"}}) == codes.count(200)


def test_sequential_after_race_still_allows_20th(free_rest):
    # After a race where every contender was rolled back, the 20th slot must still be usable.
    rid, h = free_rest["rid"], hdr(free_rest["tok"])
    inactive = [str(d["_id"]) for d in mdb.menu_items.find({"restaurantId": rid, "isAvailable": False})]
    r = requests.patch(f"{API}/menu/items/{inactive[0]}/availability", json={"isAvailable": True}, headers=h, timeout=20)
    assert r.status_code == 200 and active(rid) == 20
    r2 = requests.patch(f"{API}/menu/items/{inactive[1]}/availability", json={"isAvailable": True}, headers=h, timeout=20)
    assert r2.status_code == 403 and active(rid) == 20
