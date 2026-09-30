"""Replaceable geocoding + distance abstraction.

V1 geocodes via Photon (primary) and Nominatim (fallback) — both free,
OpenStreetMap-based, no API key — and measures haversine (straight-line)
distance. Results are cached in MongoDB so the same address is geocoded once.
The public surface (geocode / haversine_km) is intentionally small so a
driving-distance provider (Google Maps, etc.) can be swapped in later without
touching callers.
"""
import math
import os
import logging

import httpx

from db import db

logger = logging.getLogger("upxero.distance")

PHOTON_URL = "https://photon.komoot.io/api/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = os.environ.get("NOMINATIM_USER_AGENT", "UpxeroOrdering/1.0")


async def _photon(address: str):
    params = {"q": address, "limit": 1}
    async with httpx.AsyncClient(timeout=12) as client:
        resp = await client.get(PHOTON_URL, params=params, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        feats = resp.json().get("features") or []
        if not feats:
            return None
        lon, lat = feats[0]["geometry"]["coordinates"]
        return float(lat), float(lon)


async def _nominatim(address: str):
    params = {"q": address, "format": "json", "limit": 1, "countrycodes": "be,nl"}
    async with httpx.AsyncClient(timeout=12) as client:
        resp = await client.get(NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])


async def geocode(address: str):
    """Return (lat, lng) for a free-text address, or None if not found."""
    if not address or not address.strip():
        return None
    key = address.strip().lower()
    cached = await db.geocode_cache.find_one({"_id": key})
    if cached:
        if cached.get("lat") is None:
            return None
        return cached["lat"], cached["lng"]

    coords = None
    for provider in (_photon, _nominatim):
        try:
            coords = await provider(address)
            if coords:
                break
        except Exception as exc:  # network / provider failure — try next, never fake
            logger.warning("Geocoder %s failed for %r: %s", provider.__name__, address, exc)

    if coords:
        await db.geocode_cache.update_one(
            {"_id": key}, {"$set": {"lat": coords[0], "lng": coords[1]}}, upsert=True
        )
        return coords
    # cache a negative result briefly so a bad address does not hammer providers
    await db.geocode_cache.update_one({"_id": key}, {"$set": {"lat": None, "lng": None}}, upsert=True)
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(a))
