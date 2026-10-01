import os
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("restaurantId")
    await db.restaurants.create_index("slug", unique=True)
    await db.menu_categories.create_index("restaurantId")
    await db.menu_items.create_index("restaurantId")
    await db.menu_items.create_index("categoryId")
    await db.orders.create_index("restaurantId")
    await db.orders.create_index("status")
    await db.orders.create_index("createdAt")
    await db.orders.create_index("statusToken")
    await db.orders.create_index("statusTokenHash")
    # Partial unique index: only enforce uniqueness when idempotencyKey is a string,
    # so multiple keyless orders never collide on a null value.
    try:
        await db.orders.drop_index("restaurantId_1_idempotencyKey_1")
    except Exception:
        pass
    await db.orders.create_index(
        [("restaurantId", 1), ("idempotencyKey", 1)],
        unique=True,
        partialFilterExpression={"idempotencyKey": {"$type": "string"}},
    )
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("email")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_requests.create_index("email")
    await db.password_reset_requests.create_index("created_at", expireAfterSeconds=900)
    await db.staff_invitations.create_index("token_hash", unique=True)
    await db.staff_invitations.create_index("expires_at", expireAfterSeconds=0)
    await db.staff_invitations.create_index("restaurantId")
    await db.staff_invitations.create_index("email")
