# Cleanup for test_admin_controls_deletion.py: removes TEST_Resto/TEST_Acct/TEST_UI restaurants + related data.
import os
import re

from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
rs = list(db.restaurants.find({"name": {"$regex": r"^TEST_(Resto|Acct|UI Resto) "}}))
for r in rs:
    rid = str(r["_id"])
    users = db.users.delete_many({"restaurantId": rid}).deleted_count
    counts = {c: db[c].delete_many({"restaurantId": rid}).deleted_count
              for c in ["orders", "menu_items", "menu_categories", "deletion_requests", "audit_logs", "staff_invitations"]}
    db.restaurants.delete_one({"_id": r["_id"]})
    print(r["name"], "users", users, counts)
print("login_attempts", db.login_attempts.delete_many({"email": {"$regex": "upxerotest.com$"}}).deleted_count)
print("left", db.users.count_documents({"email": {"$regex": re.escape("@upxerotest.com") + "$"}}))
