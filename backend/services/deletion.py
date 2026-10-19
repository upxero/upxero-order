"""Account anonymisation and restaurant data deletion.

Orders are retained (accounting/fiscal retention) but stripped of customer
personal data. Everything else tied to the restaurant is removed or anonymised.
"""
from bson import ObjectId

from db import db
from services.storage import delete_file
from utils import now_iso

ANON_CUSTOMER = "Anonymised"


async def anonymise_user(user: dict) -> str:
    uid = str(user["_id"])
    old_email = user.get("email", "")
    new_email = f"deleted-{uid}@deleted.invalid"
    ts = now_iso()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"email": new_email, "name": "Deleted user", "passwordHash": "", "isActive": False,
                  "deletedAt": ts, "updatedAt": ts},
         "$unset": {"language": "", "emailVerifiedAt": ""},
         "$inc": {"tokenVersion": 1}},
    )
    await db.password_reset_tokens.delete_many({"user_id": uid})
    await db.email_verification_tokens.delete_many({"user_id": uid})
    await db.email_verification_requests.delete_many({"user_id": uid})
    if old_email:
        await db.login_attempts.delete_many({"email": old_email})
        await db.password_reset_requests.delete_many({"email": old_email})
    await db.audit_logs.update_many({"actorId": uid}, {"$set": {"actorEmail": new_email}})
    await db.deletion_requests.update_many({"requestedBy": uid}, {"$set": {"requestedByEmail": new_email}})
    return new_email


async def delete_restaurant_data(rid: ObjectId) -> dict:
    rid_s = str(rid)
    ts = now_iso()

    files = await db["uploads.files"].find({"metadata.restaurantId": rid_s}, {"_id": 1}).to_list(100000)
    for f in files:
        await delete_file(f["_id"])
    items = await db.menu_items.delete_many({"restaurantId": rid_s})
    cats = await db.menu_categories.delete_many({"restaurantId": rid_s})
    invites = await db.staff_invitations.delete_many({"restaurantId": rid_s})

    users = await db.users.find({"restaurantId": rid_s, "deletedAt": {"$exists": False}}).to_list(1000)
    for u in users:
        await anonymise_user(u)

    orders = await db.orders.update_many(
        {"restaurantId": rid_s, "anonymisedAt": {"$exists": False}},
        {"$set": {"customer.name": ANON_CUSTOMER, "customer.phone": "", "customer.email": "",
                  "deliveryAddress": None, "notes": "", "anonymisedAt": ts},
         "$unset": {"statusTokenHash": "", "statusTokenExpiresAt": "", "statusToken": "", "idempotencyKey": ""}},
    )

    await db.restaurants.update_one(
        {"_id": rid},
        {"$set": {"isActive": False, "orderingEnabled": False, "pickupEnabled": False, "deliveryEnabled": False,
                  "email": "", "phone": "", "description": "", "logo": "", "street": "", "houseNumber": "",
                  "postalCode": "", "city": "", "latitude": None, "longitude": None, "deliveryZones": [],
                  "deletedAt": ts, "updatedAt": ts},
         "$unset": {"logoFileId": "", "menuFileId": "", "menuFileName": "", "menuFileType": ""}},
    )
    return {
        "filesDeleted": len(files),
        "menuItemsDeleted": items.deleted_count,
        "categoriesDeleted": cats.deleted_count,
        "invitationsDeleted": invites.deleted_count,
        "usersAnonymised": len(users),
        "ordersAnonymised": orders.modified_count,
    }
