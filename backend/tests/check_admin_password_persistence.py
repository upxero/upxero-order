# Verifies seed does not overwrite super admin password on restart. Restores exact original hash afterwards.
import os, subprocess, time, requests, sys
from pymongo import MongoClient
sys.path.insert(0, "/app/backend")
from security import hash_password

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
EMAIL = "mike.upxero@gmail.com"
u = db.users.find_one({"email": EMAIL})
orig = u["passwordHash"]
print("hash prefix", orig[:4], "role", u["role"])
try:
    db.users.update_one({"_id": u["_id"]}, {"$set": {"passwordHash": hash_password("TEST_Temp!Pass9")}})
    subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True)
    for _ in range(30):
        try:
            if requests.get(API + "/", timeout=3).status_code < 500: break
        except Exception: pass
        time.sleep(1)
    time.sleep(2)
    r = requests.post(API + "/auth/login", json={"email": EMAIL, "password": "TEST_Temp!Pass9"})
    print("login temp pw after restart:", r.status_code)
    r2 = requests.post(API + "/auth/login", json={"email": EMAIL, "password": "Upxero!Admin2025"})
    print("login env pw after restart (expect 401):", r2.status_code)
finally:
    db.users.update_one({"_id": u["_id"]}, {"$set": {"passwordHash": orig}})
    db.login_attempts.delete_many({"email": EMAIL})
    r3 = requests.post(API + "/auth/login", json={"email": EMAIL, "password": "Upxero!Admin2025"})
    print("restored login:", r3.status_code, r3.json().get("user", {}).get("role"), "httponly cookie:", "httponly" in r3.headers.get("set-cookie", "").lower())
