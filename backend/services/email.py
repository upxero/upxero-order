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


def _L(lang):
    return "nl" if str(lang or "").lower() == "nl" else "en"


# Bilingual email strings (restaurant-owned content like names is never translated).
ET = {
    "en": {
        "pickup": "Pickup", "delivery": "Delivery",
        "eta_prep": "Estimated preparation time", "eta_del": "Estimated delivery time",
        "customer": "Customer", "address": "Address", "note": "Note",
        "subtotal": "Subtotal", "delivery_fee": "Delivery fee", "total": "Total", "free": "Free",
        "view_order": "View your order", "view_dashboard": "View in dashboard",
        "sent_by": "Sent by", "never_pw": "We never ask for your password by email.",
        "new_order": "New order", "subj_new": "New order #{n} — {r}",
        "received_h": "Order received",
        "received_i": "We've received your order. The restaurant still needs to confirm it — you'll receive an email as soon as that happens.",
        "subj_received": "Order #{n} received",
        "subj_status": "Order #{n}: {h}", "subj_eta": "Order #{n}: estimated time updated",
        "eta_h": "Estimated time updated",
        "eta_i": "The {label} for your order has been changed to about {m} minutes.",
        "eta_i_generic": "The restaurant has updated the estimated time for your order.",
        "about_min": "about {m} minutes",
        "accepted_h": "Your order is confirmed", "accepted_i": "Good news! The restaurant has confirmed your order.",
        "preparing_h": "Your order is being prepared", "preparing_i": "The restaurant is working on your order.",
        "ready_pickup_h": "Your order is ready for pickup", "ready_pickup_i": "Your order is ready to be picked up.",
        "ready_delivery_h": "Your order is on its way", "ready_delivery_i": "Your order is on its way to your address.",
        "completed_h": "Your order is complete", "completed_i": "Thanks for your order!",
        "cancelled_h": "Your order was cancelled", "cancelled_i": "Your order has been cancelled. Please contact the restaurant with any questions.",
    },
    "nl": {
        "pickup": "Afhalen", "delivery": "Bezorgen",
        "eta_prep": "Verwachte bereidingstijd", "eta_del": "Verwachte bezorgtijd",
        "customer": "Klant", "address": "Adres", "note": "Opmerking",
        "subtotal": "Subtotaal", "delivery_fee": "Bezorgkosten", "total": "Totaal", "free": "Gratis",
        "view_order": "Bekijk je bestelling", "view_dashboard": "Bekijk in dashboard",
        "sent_by": "Verzonden door", "never_pw": "We vragen nooit je wachtwoord per e-mail.",
        "new_order": "Nieuwe bestelling", "subj_new": "Nieuwe bestelling #{n} — {r}",
        "received_h": "Bestelling ontvangen",
        "received_i": "We hebben je bestelling ontvangen. Het restaurant moet deze nog bevestigen — je ontvangt een e-mail zodra dat gebeurt.",
        "subj_received": "Bestelling #{n} ontvangen",
        "subj_status": "Bestelling #{n}: {h}", "subj_eta": "Bestelling #{n}: verwachte tijd aangepast",
        "eta_h": "Verwachte tijd aangepast",
        "eta_i": "De {label} van je bestelling is gewijzigd naar ongeveer {m} minuten.",
        "eta_i_generic": "Het restaurant heeft de verwachte tijd van je bestelling aangepast.",
        "about_min": "ongeveer {m} minuten",
        "accepted_h": "Je bestelling is bevestigd", "accepted_i": "Goed nieuws! Het restaurant heeft je bestelling bevestigd.",
        "preparing_h": "Je bestelling wordt bereid", "preparing_i": "Het restaurant is met je bestelling bezig.",
        "ready_pickup_h": "Je bestelling is klaar om af te halen", "ready_pickup_i": "Je bestelling staat klaar om af te halen.",
        "ready_delivery_h": "Je bestelling is onderweg", "ready_delivery_i": "Je bestelling is onderweg naar je adres.",
        "completed_h": "Je bestelling is voltooid", "completed_i": "Bedankt voor je bestelling!",
        "cancelled_h": "Je bestelling is geannuleerd", "cancelled_i": "Je bestelling is geannuleerd. Neem contact op met het restaurant bij vragen.",
    },
}


async def send_new_order_email(to_email: str, restaurant_name: str, order: dict, lang: str = "nl") -> bool:
    """Notify the restaurant of a new order (restaurant's selected language)."""
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    if not _configured(base):
        return False
    t = ET[_L(lang)]
    brand = escape(EMAIL_FROM_NAME)
    resto = escape(restaurant_name or brand)
    cust = order.get("customer", {}) or {}
    otype = t["delivery"] if order.get("orderType") == "delivery" else t["pickup"]

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
        addr = (f'<p style="margin:8px 0 0"><strong>{t["address"]}:</strong> '
                f'{escape(da.get("street",""))} {escape(da.get("houseNumber",""))}, '
                f'{escape(da.get("postalCode",""))} {escape(da.get("city",""))}'
                f'{(" — " + escape(da.get("extra",""))) if da.get("extra") else ""}</p>')
    notes = f'<p style="margin:8px 0 0"><strong>{t["note"]}:</strong> {escape(order.get("notes",""))}</p>' if order.get("notes") else ""
    delivery_row = (f'<tr><td style="padding:2px 0;color:#555">{t["delivery_fee"]}</td>'
                    f'<td style="padding:2px 0;text-align:right">{_eur(order.get("deliveryFee"))}</td></tr>') if order.get("orderType") == "delivery" else ""
    button = ""
    if base.startswith("https://"):
        link = f"{base}/dashboard/bestellingen"
        button = (f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#059669;color:#fff;'
                  f'padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">{t["view_dashboard"]}</a></p>')

    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<h2 style="margin:0 0 4px">{t["new_order"]} #{escape(str(order.get("orderNumber")))}</h2>'
        f'<p style="margin:0 0 16px;color:#555">{resto} · {otype}</p>'
        f'<p style="margin:0"><strong>{t["customer"]}:</strong> {escape(cust.get("name",""))} · {escape(cust.get("phone",""))}</p>'
        f'{addr}{notes}'
        f'<table width="100%" style="margin-top:16px;border-collapse:collapse">{rows}</table>'
        f'<table width="100%" style="margin-top:12px">'
        f'<tr><td style="padding:2px 0;color:#555">{t["subtotal"]}</td><td style="padding:2px 0;text-align:right">{_eur(order.get("subtotal"))}</td></tr>'
        f'{delivery_row}'
        f'<tr><td style="padding:6px 0;font-weight:700;border-top:1px solid #eee">{t["total"]}</td>'
        f'<td style="padding:6px 0;text-align:right;font-weight:700;border-top:1px solid #eee">{_eur(order.get("total"))}</td></tr>'
        f'</table>{button}'
        f'<p style="font-size:12px;color:#888;margin-top:24px">{t["sent_by"]} {brand}.</p>'
        f'</td></tr></table>'
    )
    return await _send(to_email, t["subj_new"].format(n=order.get("orderNumber"), r=restaurant_name), html)


def _status_link(token: str):
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return base, (f"{base}/order-status/{token}" if base.startswith("https://") else "")


def _eta_label(order: dict, t: dict) -> str:
    return t["eta_del"] if order.get("orderType") == "delivery" else t["eta_prep"]


def _customer_order_html(restaurant_name: str, order: dict, link: str, heading: str, intro: str, t: dict) -> str:
    brand = escape(EMAIL_FROM_NAME)
    resto = escape(restaurant_name or brand)
    otype = t["delivery"] if order.get("orderType") == "delivery" else t["pickup"]
    rows = ""
    for it in order.get("items", []):
        opts = ", ".join(escape(o.get("optionName", "")) for o in it.get("selectedOptions", []))
        opt_html = f'<div style="font-size:12px;color:#888">{opts}</div>' if opts else ""
        rows += (f'<tr><td style="padding:6px 0;border-bottom:1px solid #eee"><strong>{it.get("quantity")}×</strong> '
                 f'{escape(it.get("productName",""))}{opt_html}</td>'
                 f'<td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;white-space:nowrap">{_eur(it.get("lineTotal"))}</td></tr>')
    eta = ""
    mins = order.get("estimatedMinutes")
    if mins:
        eta = f'<p style="margin:12px 0 0;font-size:16px"><strong>{_eta_label(order, t)}: {t["about_min"].format(m=int(mins))}</strong></p>'
    elif order.get("estimatedTime"):
        eta = f'<p style="margin:12px 0 0;font-size:16px"><strong>{_eta_label(order, t)}: {escape(str(order["estimatedTime"]))}</strong></p>'
    delivery_row = (f'<tr><td style="padding:2px 0;color:#555">{t["delivery_fee"]}</td>'
                    f'<td style="padding:2px 0;text-align:right">{_eur(order.get("deliveryFee"))}</td></tr>') if order.get("orderType") == "delivery" else ""
    button = (f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#059669;color:#fff;'
              f'padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">{t["view_order"]}</a></p>') if link else ""
    return (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<h2 style="margin:0 0 4px">{escape(heading)}</h2>'
        f'<p style="margin:0 0 12px;color:#555">{resto} · {otype} · #{escape(str(order.get("orderNumber")))}</p>'
        f'<p style="margin:0">{escape(intro)}</p>{eta}'
        f'<table width="100%" style="margin-top:16px;border-collapse:collapse">{rows}</table>'
        f'<table width="100%" style="margin-top:12px">'
        f'<tr><td style="padding:2px 0;color:#555">{t["subtotal"]}</td><td style="padding:2px 0;text-align:right">{_eur(order.get("subtotal"))}</td></tr>'
        f'{delivery_row}'
        f'<tr><td style="padding:6px 0;font-weight:700;border-top:1px solid #eee">{t["total"]}</td>'
        f'<td style="padding:6px 0;text-align:right;font-weight:700;border-top:1px solid #eee">{_eur(order.get("total"))}</td></tr>'
        f'</table>{button}'
        f'<p style="font-size:12px;color:#888;margin-top:24px">{t["sent_by"]} {brand}. {t["never_pw"]}</p>'
        f'</td></tr></table>'
    )


async def send_order_received_customer_email(to_email: str, restaurant_name: str, order: dict, token: str, lang: str = "nl") -> bool:
    base, link = _status_link(token)
    if not _configured(base):
        return False
    t = ET[_L(lang)]
    html = _customer_order_html(restaurant_name, order, link, t["received_h"], t["received_i"], t)
    return await _send(to_email, t["subj_received"].format(n=order.get("orderNumber")), html)


def _status_copy(t: dict):
    return {
        "accepted": (t["accepted_h"], t["accepted_i"]),
        "preparing": (t["preparing_h"], t["preparing_i"]),
        "ready_pickup": (t["ready_pickup_h"], t["ready_pickup_i"]),
        "ready_delivery": (t["ready_delivery_h"], t["ready_delivery_i"]),
        "completed": (t["completed_h"], t["completed_i"]),
        "cancelled": (t["cancelled_h"], t["cancelled_i"]),
    }


async def send_order_status_customer_email(to_email: str, restaurant_name: str, order: dict, token: str, lang: str = "nl") -> bool:
    base, link = _status_link(token)
    if not _configured(base):
        return False
    t = ET[_L(lang)]
    status = order.get("status")
    key = status
    if status == "ready":
        key = "ready_delivery" if order.get("orderType") == "delivery" else "ready_pickup"
    copy = _status_copy(t).get(key)
    if not copy:
        return False
    heading, intro = copy
    html = _customer_order_html(restaurant_name, order, link, heading, intro, t)
    return await _send(to_email, t["subj_status"].format(n=order.get("orderNumber"), h=heading), html)


async def send_order_eta_customer_email(to_email: str, restaurant_name: str, order: dict, token: str, lang: str = "nl") -> bool:
    base, link = _status_link(token)
    if not _configured(base):
        return False
    t = ET[_L(lang)]
    mins = order.get("estimatedMinutes")
    label = _eta_label(order, t).lower()
    intro = (t["eta_i"].format(label=label, m=int(mins)) if mins else t["eta_i_generic"])
    html = _customer_order_html(restaurant_name, order, link, t["eta_h"], intro, t)
    return await _send(to_email, t["subj_eta"].format(n=order.get("orderNumber")), html)
