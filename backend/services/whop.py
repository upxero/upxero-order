"""Whop REST client (api.whop.com/api/v1), webhook verification and membership sync."""
import base64
import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timezone

import httpx
from bson import ObjectId

from db import db
from services.audit import audit
from services.entitlements import effective_plan

log = logging.getLogger("upxero.whop")
BASE = "https://api.whop.com/api/v1"
WEBHOOK_TOLERANCE_S = 300
SYSTEM_ACTOR = {"_id": "whop", "email": "whop-sync", "role": "system"}


class WhopError(Exception):
    def __init__(self, status: int, path: str):
        super().__init__(f"Whop API {path} -> {status}")
        self.status = status


def cfg(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def api_configured() -> bool:
    return bool(cfg("WHOP_API_KEY") and cfg("WHOP_BUSINESS_ID") and cfg("WHOP_PRODUCT_ID"))


def checkout_configured() -> bool:
    return api_configured() and bool(cfg("WHOP_PLAN_ID"))


async def _request(method: str, path: str, **kw) -> dict:
    headers = {"Authorization": f"Bearer {cfg('WHOP_API_KEY')}", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=8) as c:
            res = await c.request(method, path, headers=headers, **kw)
    except httpx.HTTPError:
        log.warning("Whop API unreachable: %s %s", method, path)
        raise WhopError(0, path)
    if res.status_code >= 400:
        # Never log bodies or headers (may echo identifiers); status + path only.
        log.warning("Whop API error %s on %s %s", res.status_code, method, path)
        raise WhopError(res.status_code, path)
    return res.json()


async def list_plans() -> list:
    body = await _request("GET", "/plans", params={
        "account_id": cfg("WHOP_BUSINESS_ID"), "product_ids": cfg("WHOP_PRODUCT_ID"), "first": 50,
    })
    return body.get("data", [])


async def create_checkout(restaurant_id: str, ref: str, redirect_url: str) -> dict:
    return await _request("POST", "/checkout_configurations", json={
        "plan_id": cfg("WHOP_PLAN_ID"),
        "metadata": {"restaurant_id": restaurant_id, "checkout_ref": ref},
        "redirect_url": redirect_url,
    })


async def get_membership(membership_id: str) -> dict:
    return await _request("GET", f"/memberships/{membership_id}")


async def list_memberships() -> list:
    body = await _request("GET", "/memberships", params={"product_ids": cfg("WHOP_PRODUCT_ID"), "first": 50})
    return body.get("data", [])


def verify_webhook(raw: bytes, headers) -> None:
    """Standard Webhooks check as Whop signs it: HMAC-SHA256 keyed with the literal secret."""
    secret = cfg("WHOP_WEBHOOK_SECRET")
    wid, ts, sig = (headers.get("webhook-id"), headers.get("webhook-timestamp"),
                    headers.get("webhook-signature"))
    if not (secret and wid and ts and sig):
        raise ValueError("missing")
    try:
        ts_int = int(ts)
    except ValueError:
        raise ValueError("timestamp")
    if abs(time.time() - ts_int) > WEBHOOK_TOLERANCE_S:
        raise ValueError("stale")
    signed = f"{wid}.{ts}.".encode() + raw
    expected = base64.b64encode(hmac.new(secret.encode(), signed, hashlib.sha256).digest()).decode()
    for part in sig.split():
        version, _, value = part.partition(",")
        if version == "v1" and hmac.compare_digest(value, expected):
            return
    raise ValueError("signature")


def membership_id_from_event(event: dict) -> str | None:
    data = event.get("data") or {}
    typ = event.get("type", "")
    if typ.startswith("membership."):
        return data.get("id")
    if typ.startswith("payment."):
        return data.get("membership_id") or (data.get("membership") or {}).get("id")
    if typ.startswith("refund."):
        return ((data.get("payment") or {}).get("membership") or {}).get("id")
    return None


def _owned(m: dict) -> bool:
    plan_ok = not cfg("WHOP_PLAN_ID") or (m.get("plan") or {}).get("id") == cfg("WHOP_PLAN_ID")
    return ((m.get("company") or {}).get("id") == cfg("WHOP_BUSINESS_ID")
            and (m.get("product") or {}).get("id") == cfg("WHOP_PRODUCT_ID") and plan_ok)


async def _linked_restaurant(m: dict) -> dict | None:
    r = await db.restaurants.find_one({"subscription.whopMembershipId": m["id"]})
    if r:
        return r
    meta = m.get("metadata") or {}
    rid, ref = meta.get("restaurant_id"), meta.get("checkout_ref")
    if not (rid and ref and ObjectId.is_valid(rid)):
        return None
    if not await db.billing_checkouts.find_one({"ref": ref, "restaurantId": rid}):
        return None
    return await db.restaurants.find_one({"_id": ObjectId(rid), "deletedAt": None})


async def apply_membership(m: dict) -> str:
    """Persist authoritative membership state (fetched from Whop, never from webhook data)."""
    if not m.get("id") or not _owned(m):
        return "ignored:foreign"
    r = await _linked_restaurant(m)
    if not r:
        return "ignored:unlinked"
    sub = r.get("subscription") or {}
    current = sub.get("whopMembershipId")
    if current and current != m["id"]:
        from services.entitlements import PRO_STATUSES
        if sub.get("whopStatus") in PRO_STATUSES or m.get("status") not in PRO_STATUSES:
            return "ignored:other_membership"
    before = effective_plan(r)
    fields = {
        "whopMembershipId": m["id"],
        "whopStatus": m.get("status"),
        "whopUserId": (m.get("user") or {}).get("id"),
        "whopPlanId": (m.get("plan") or {}).get("id"),
        "whopProductId": (m.get("product") or {}).get("id"),
        "whopBusinessId": (m.get("company") or {}).get("id"),
        "renewalPeriodEnd": m.get("renewal_period_end"),
        "cancelAtPeriodEnd": bool(m.get("cancel_at_period_end")),
        "manageUrl": m.get("manage_url"),
        "lastSyncedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.restaurants.update_one({"_id": r["_id"]}, {"$set": {f"subscription.{k}": v for k, v in fields.items()}})
    after = effective_plan({"subscription": {**sub, **fields}})
    if before != after:
        await audit(SYSTEM_ACTOR, r["_id"], "subscription.changed",
                    {"from": before, "to": after, "whopStatus": m.get("status")})
    return f"applied:{after}"
