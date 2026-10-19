from datetime import datetime, timezone

from db import db


async def audit(actor: dict, restaurant_id, action: str, details: dict | None = None) -> None:
    """Append-only record of who did what to which restaurant."""
    await db.audit_logs.insert_one({
        "actorId": str(actor["_id"]),
        "actorEmail": actor.get("email", ""),
        "actorRole": actor.get("role", ""),
        "restaurantId": str(restaurant_id) if restaurant_id else None,
        "action": action,
        "details": details or {},
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
