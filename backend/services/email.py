"""Password-reset email via the Emergent-managed email integration.

Fixed server-side template: callers pass only a recipient address and a reset
token, never markup. Scope is password reset only.
"""
import logging
import os
from html import escape
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("upxero.email")

# Each environment runs its own integration proxy; read the host from env with a
# prod-correct fallback. Never hardcode a single host.
EMAIL_BASE_URL = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip().rstrip("/") or "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME") or "Upxero Ordering"


async def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send the reset link. Return value is for logging only — never surface it."""
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{base}/reset-wachtwoord?token={token}"
    if not EMAIL_KEY or EMAIL_KEY.startswith("{") or not base.startswith("https://"):
        if urlparse(base).hostname in ("localhost", "127.0.0.1", "::1"):
            logger.warning("E-mail niet geconfigureerd; reset-link: %s", link)
        else:
            logger.error("Reset-e-mail niet geconfigureerd (EMERGENT_EMAIL_KEY / FRONTEND_URL)")
        return False

    brand = escape(EMAIL_FROM_NAME)
    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<h2 style="margin:0 0 12px">Wachtwoord opnieuw instellen</h2>'
        f'<p>We ontvingen een verzoek om je {brand}-wachtwoord opnieuw in te stellen.</p>'
        f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#059669;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">Wachtwoord opnieuw instellen</a></p>'
        f'<p>Deze link verloopt binnen 1 uur en kan één keer gebruikt worden. Heb je dit niet aangevraagd, negeer dan deze e-mail — je wachtwoord blijft ongewijzigd.</p>'
        f'<p style="font-size:12px;color:#888;margin-top:24px">Verzonden door {brand}. We vragen nooit je wachtwoord per e-mail.</p>'
        f'</td></tr></table>'
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json={"to": [to_email], "subject": f"Stel je {EMAIL_FROM_NAME}-wachtwoord opnieuw in",
                      "html": html, "from_name": EMAIL_FROM_NAME},
            )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Reset-e-mail versturen mislukt: %s", exc)
        return False
