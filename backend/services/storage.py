"""GridFS-backed file storage on the existing MongoDB (Atlas) connection.

One bucket ("uploads") with chunked storage — no large binaries in normal docs,
no local filesystem, no external storage service. Every object carries metadata
(restaurantId, category, contentType, originalFilename, size, uploadedAt).
"""
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from db import db

_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="uploads")

# Allowed types per feature (server-authoritative; validated by magic bytes).
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
MENU_FILE_MIMES = {"application/pdf", "image/jpeg", "image/png"}

MB = 1024 * 1024


def _sniff_mime(data: bytes):
    """Detect the real content type from magic bytes (ignores client header)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:5] == b"%PDF-":
        return "application/pdf"
    return None


async def save_upload(file: UploadFile, restaurant_id, category: str,
                      allowed_mimes: set, max_bytes: int):
    """Validate + store an upload in GridFS. Returns (file_id_str, metadata)."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Het bestand is leeg.")
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Bestand is te groot (max {max_bytes // MB} MB).")
    sniffed = _sniff_mime(data)
    if sniffed is None or sniffed not in allowed_mimes:
        raise HTTPException(status_code=400, detail="Bestandstype niet toegestaan.")
    metadata = {
        "restaurantId": str(restaurant_id),
        "category": category,
        "contentType": sniffed,
        "originalFilename": (file.filename or "")[:200],
        "size": len(data),
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
    }
    file_id = await _bucket.upload_from_stream(f"{category}-{uuid.uuid4()}", data, metadata=metadata)
    return str(file_id), metadata


async def open_file(file_id):
    """Return (bytes, metadata) for a stored file, or 404."""
    try:
        oid_ = ObjectId(str(file_id))
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Bestand niet gevonden")
    try:
        stream = await _bucket.open_download_stream(oid_)
        data = await stream.read()
    except Exception:
        raise HTTPException(status_code=404, detail="Bestand niet gevonden")
    return data, (stream.metadata or {})


async def delete_file(file_id):
    """Best-effort permanent delete; safe to call on missing/invalid ids."""
    try:
        oid_ = ObjectId(str(file_id))
    except (InvalidId, TypeError):
        return
    try:
        await _bucket.delete(oid_)
    except Exception:
        pass
