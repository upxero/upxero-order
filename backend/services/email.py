"""Transactional email via the Emergent-managed email integration.

All sends are fixed server-side templates — callers pass recipient addresses and
IDs/values, never markup. Every send path runs through `_assert_safe_email`.
"""
import ipaddress
import logging
import os
import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("upxero.email")

# Each environment runs its own integration proxy; read the host from env with a
# prod-correct fallback. Never hardcode a single host.
EMAIL_BASE_URL = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip().rstrip("/") or "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME") or "Upxero Ordering"


# ---------- Guardrail gate (G2/G3 structural defense in depth) ----------

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


def _configured(base: str, link: str = "") -> bool:
    """True when the integration can actually send. Logs a loopback link for dev."""
    if not EMAIL_KEY or EMAIL_KEY.startswith("{") or not base.startswith("https://"):
        if urlparse(base).hostname in ("localhost", "127.0.0.1", "::1") and link:
            logger.warning("E-mail niet geconfigureerd; link: %s", link)
        else:
            logger.error("E-mail niet geconfigureerd (EMERGENT_EMAIL_KEY / FRONTEND_URL)")
        return False
    return True


async def _send(to_email: str, subject: str, html: str) -> bool:
    """Internal send. `subject`/`html` are built from fixed server-side templates."""
    try:
        _assert_safe_email(subject, html)  # G2/G3 gate — never skip
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json={"to": [to_email], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME},
            )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("E-mail versturen mislukt: %s", exc)
        return False


_FOOTER = (f'<p style="font-size:12px;color:#888;margin-top:24px">Verzonden door {escape(EMAIL_FROM_NAME)}. '
           f'We vragen nooit je wachtwoord per e-mail.</p>')


async def send_password_reset_email(to_email: str, token: str) -> bool:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{base}/reset-wachtwoord?token={token}"
    if not _configured(base, link):
        return False
    brand = escape(EMAIL_FROM_NAME)
    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<h2 style="margin:0 0 12px">Wachtwoord opnieuw instellen</h2>'
        f'<p>We ontvingen een verzoek om je {brand}-wachtwoord opnieuw in te stellen.</p>'
        f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#059669;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">Wachtwoord opnieuw instellen</a></p>'
        f'<p>Deze link verloopt binnen 1 uur en kan één keer gebruikt worden. Heb je dit niet aangevraagd, negeer dan deze e-mail — je wachtwoord blijft ongewijzigd.</p>'
        f'{_FOOTER}</td></tr></table>'
    )
    return await _send(to_email, f"Stel je {EMAIL_FROM_NAME}-wachtwoord opnieuw in", html)


async def send_staff_invitation_email(to_email: str, token: str, restaurant_name: str, inviter_name: str) -> bool:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{base}/staff-uitnodiging?token={token}"
    if not _configured(base, link):
        return False
    brand = escape(EMAIL_FROM_NAME)
    resto = escape(restaurant_name or brand)
    inviter = escape(inviter_name or "het team")
    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<h2 style="margin:0 0 12px">Je bent uitgenodigd</h2>'
        f'<p>{inviter} heeft je uitgenodigd om mee te helpen bij <strong>{resto}</strong> op {brand}.</p>'
        f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#059669;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">Account aanmaken</a></p>'
        f'<p>Via deze link maak je je eigen wachtwoord aan. De link verloopt binnen 7 dagen en kan één keer gebruikt worden.</p>'
        f'{_FOOTER}</td></tr></table>'
    )
    return await _send(to_email, f"Uitnodiging voor {restaurant_name} op {EMAIL_FROM_NAME}", html)


def _eur(v):
    return "€" + ("%.2f" % float(v or 0)).replace(".", ",")


async def send_new_order_email(to_email: str, restaurant_name: str, order: dict) -> bool:
    """Notify the restaurant of a new order. Recipient = restaurant's own address."""
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    if not _configured(base):
        return False
    brand = escape(EMAIL_FROM_NAME)
    resto = escape(restaurant_name or brand)
    cust = order.get("customer", {}) or {}
    otype = "Bezorgen" if order.get("orderType") == "delivery" else "Afhalen"

    rows = ""
    for it in order.get("items", []):
        opts = ", ".join(escape(o.get("optionName", "")) for o in it.get("selectedOptions", []))
        opt_html = f'<div style="font-size:12px;color:#888">{opts}</div>' if opts else ""
        rows += (
            f'<tr><td style="padding:6px 0;border-bottom:1px solid #eee">'
            f'<strong>{it.get("quantity")}×</strong> {escape(it.get("productName",""))}{opt_html}</td>'
            f'<td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;white-space:nowrap">{_eur(it.get("lineTotal"))}</td></tr>'
        )

    addr = ""
    if order.get("orderType") == "delivery" and order.get("deliveryAddress"):
        da = order["deliveryAddress"]
        addr = (f'<p style="margin:8px 0 0"><strong>Adres:</strong> '
                f'{escape(da.get("street",""))} {escape(da.get("houseNumber",""))}, '
                f'{escape(da.get("postalCode",""))} {escape(da.get("city",""))}'
                f'{(" — " + escape(da.get("extra",""))) if da.get("extra") else ""}</p>')
    notes = f'<p style="margin:8px 0 0"><strong>Opmerking:</strong> {escape(order.get("notes",""))}</p>' if order.get("notes") else ""
    delivery_row = (f'<tr><td style="padding:2px 0;color:#555">Bezorgkosten</td>'
                    f'<td style="padding:2px 0;text-align:right">{_eur(order.get("deliveryFee"))}</td></tr>') if order.get("orderType") == "delivery" else ""
    button = ""
    if base.startswith("https://"):
        link = f"{base}/dashboard/bestellingen"
        button = (f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#059669;color:#fff;'
                  f'padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">Bekijk in dashboard</a></p>')

    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<h2 style="margin:0 0 4px">Nieuwe bestelling #{escape(str(order.get("orderNumber")))}</h2>'
        f'<p style="margin:0 0 16px;color:#555">{resto} · {otype}</p>'
        f'<p style="margin:0"><strong>Klant:</strong> {escape(cust.get("name",""))} · {escape(cust.get("phone",""))}</p>'
        f'{addr}{notes}'
        f'<table width="100%" style="margin-top:16px;border-collapse:collapse">{rows}</table>'
        f'<table width="100%" style="margin-top:12px">'
        f'<tr><td style="padding:2px 0;color:#555">Subtotaal</td><td style="padding:2px 0;text-align:right">{_eur(order.get("subtotal"))}</td></tr>'
        f'{delivery_row}'
        f'<tr><td style="padding:6px 0;font-weight:700;border-top:1px solid #eee">Totaal</td>'
        f'<td style="padding:6px 0;text-align:right;font-weight:700;border-top:1px solid #eee">{_eur(order.get("total"))}</td></tr>'
        f'</table>{button}'
        f'<p style="font-size:12px;color:#888;margin-top:24px">Verzonden door {brand}.</p>'
        f'</td></tr></table>'
    )
    return await _send(to_email, f"Nieuwe bestelling #{order.get('orderNumber')} — {restaurant_name}", html)


def _status_link(token: str):
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return base, (f"{base}/order-status/{token}" if base.startswith("https://") else "")


def _eta_label(order: dict) -> str:
    return "Verwachte bezorgtijd" if order.get("orderType") == "delivery" else "Verwachte afhaaltijd"


def _customer_order_html(restaurant_name: str, order: dict, link: str, heading: str, intro: str) -> str:
    brand = escape(EMAIL_FROM_NAME)
    resto = escape(restaurant_name or brand)
    otype = "Bezorgen" if order.get("orderType") == "delivery" else "Afhalen"
    rows = ""
    for it in order.get("items", []):
        opts = ", ".join(escape(o.get("optionName", "")) for o in it.get("selectedOptions", []))
        opt_html = f'<div style="font-size:12px;color:#888">{opts}</div>' if opts else ""
        rows += (f'<tr><td style="padding:6px 0;border-bottom:1px solid #eee"><strong>{it.get("quantity")}×</strong> '
                 f'{escape(it.get("productName",""))}{opt_html}</td>'
                 f'<td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;white-space:nowrap">{_eur(it.get("lineTotal"))}</td></tr>')
    eta = ""
    if order.get("estimatedTime"):
        eta = f'<p style="margin:12px 0 0;font-size:16px"><strong>{_eta_label(order)}: {escape(str(order["estimatedTime"]))}</strong></p>'
    delivery_row = (f'<tr><td style="padding:2px 0;color:#555">Bezorgkosten</td>'
                    f'<td style="padding:2px 0;text-align:right">{_eur(order.get("deliveryFee"))}</td></tr>') if order.get("orderType") == "delivery" else ""
    button = (f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#059669;color:#fff;'
              f'padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">Bekijk bestelling</a></p>') if link else ""
    return (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<h2 style="margin:0 0 4px">{escape(heading)}</h2>'
        f'<p style="margin:0 0 12px;color:#555">{resto} · {otype} · Bestelling #{escape(str(order.get("orderNumber")))}</p>'
        f'<p style="margin:0">{escape(intro)}</p>{eta}'
        f'<table width="100%" style="margin-top:16px;border-collapse:collapse">{rows}</table>'
        f'<table width="100%" style="margin-top:12px">'
        f'<tr><td style="padding:2px 0;color:#555">Subtotaal</td><td style="padding:2px 0;text-align:right">{_eur(order.get("subtotal"))}</td></tr>'
        f'{delivery_row}'
        f'<tr><td style="padding:6px 0;font-weight:700;border-top:1px solid #eee">Totaal</td>'
        f'<td style="padding:6px 0;text-align:right;font-weight:700;border-top:1px solid #eee">{_eur(order.get("total"))}</td></tr>'
        f'</table>{button}'
        f'<p style="font-size:12px;color:#888;margin-top:24px">Verzonden door {brand}. We vragen nooit je wachtwoord per e-mail.</p>'
        f'</td></tr></table>'
    )


async def send_order_received_customer_email(to_email: str, restaurant_name: str, order: dict, token: str) -> bool:
    base, link = _status_link(token)
    if not _configured(base):
        return False
    html = _customer_order_html(
        restaurant_name, order, link, "Bestelling ontvangen",
        "We hebben je bestelling ontvangen. Het restaurant moet deze nog bevestigen — je ontvangt een e-mail zodra dat gebeurt.")
    return await _send(to_email, f"Bestelling #{order.get('orderNumber')} ontvangen", html)


_STATUS_COPY = {
    "accepted": ("Je bestelling is bevestigd", "Goed nieuws! Het restaurant heeft je bestelling bevestigd."),
    "preparing": ("Je bestelling wordt bereid", "Het restaurant is met je bestelling bezig."),
    "ready_pickup": ("Je bestelling is klaar om af te halen", "Je bestelling staat klaar om af te halen."),
    "ready_delivery": ("Je bestelling is onderweg", "Je bestelling is onderweg naar je adres."),
    "completed": ("Je bestelling is voltooid", "Bedankt voor je bestelling!"),
    "cancelled": ("Je bestelling is geannuleerd", "Je bestelling is geannuleerd. Neem contact op met het restaurant bij vragen."),
}


async def send_order_status_customer_email(to_email: str, restaurant_name: str, order: dict, token: str) -> bool:
    base, link = _status_link(token)
    if not _configured(base):
        return False
    status = order.get("status")
    key = status
    if status == "ready":
        key = "ready_delivery" if order.get("orderType") == "delivery" else "ready_pickup"
    copy = _STATUS_COPY.get(key)
    if not copy:
        return False
    heading, intro = copy
    html = _customer_order_html(restaurant_name, order, link, heading, intro)
    return await _send(to_email, f"Bestelling #{order.get('orderNumber')}: {heading}", html)


async def send_order_eta_customer_email(to_email: str, restaurant_name: str, order: dict, token: str) -> bool:
    base, link = _status_link(token)
    if not _configured(base):
        return False
    html = _customer_order_html(
        restaurant_name, order, link, "Verwachte tijd aangepast",
        "Het restaurant heeft de verwachte tijd van je bestelling aangepast.")
    return await _send(to_email, f"Bestelling #{order.get('orderNumber')}: verwachte tijd aangepast", html)
