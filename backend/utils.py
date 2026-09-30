import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pymongo import ReturnDocument


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def oid(value) -> ObjectId:
    """Coerce a string to ObjectId or raise a clean 404 (never a 500)."""
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Niet gevonden")


def serialize(doc):
    """Recursively convert a Mongo document to a JSON-safe dict."""
    if doc is None:
        return None
    out = {}
    for k, v in doc.items():
        key = "id" if k == "_id" else k
        out[key] = _conv(v)
    return out


def _conv(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [_conv(i) for i in v]
    if isinstance(v, dict):
        return serialize(v)
    return v


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "restaurant"


async def unique_slug(db, name: str) -> str:
    base = slugify(name)
    slug = base
    i = 1
    while await db.restaurants.find_one({"slug": slug}):
        i += 1
        slug = f"{base}-{i}"
    return slug


async def next_order_number(db, restaurant_id: str) -> int:
    doc = await db.counters.find_one_and_update(
        {"_id": f"orders:{restaurant_id}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return 1000 + int(doc["seq"])
