# Removes all TEST_ restaurants (incl. tombstones) and their users/orders/menu/requests/audit/counters.
import os
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
for r in list(db.restaurants.find({"name": {"$regex": "^TEST_"}})):
    rid = str(r["_id"])
    q = {"restaurantId": {"$in": [rid, r["_id"]]}}
    for c in ["users", "orders", "menu_items", "menu_categories", "deletion_requests", "audit_logs", "staff_invitations"]:
        db[c].delete_many(q)
    db.counters.delete_one({"_id": f"orders:{rid}"})
    db.restaurants.delete_one({"_id": r["_id"]})
    print("removed", r["name"])
db.login_attempts.delete_many({"email": {"$regex": "upxerotest"}})
