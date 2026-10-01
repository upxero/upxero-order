"""Tests for the public menu PDF link feature on /order/<slug>."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://restaurant-dashboard-48.preview.emergentagent.com").rstrip("/")
SLUG = "bistro-demo"

OWNER = {"email": "owner@demo.upxero.com", "password": "Demo!2025"}

MIN_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.fixture(scope="module")
def owner_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=OWNER, timeout=20)
    assert r.status_code == 200, r.text
    return s


def test_public_payload_menu_file_url_shape(owner_session):
    # Ensure baseline: upload a pdf
    files = {"file": ("menu.pdf", MIN_PDF, "application/pdf")}
    up = owner_session.post(f"{BASE_URL}/api/restaurant/menu-file", files=files, timeout=30)
    assert up.status_code == 200, up.text

    # Public payload must expose menuFileUrl as a route path
    pr = requests.get(f"{BASE_URL}/api/public/restaurant/{SLUG}", timeout=20,
                      headers={"User-Agent": "Mozilla/5.0"})
    assert pr.status_code == 200
    data = pr.json().get("restaurant", {})
    menu_url = data.get("menuFileUrl")
    assert isinstance(menu_url, str) and menu_url, "menuFileUrl must be a non-empty string"
    assert f"/api/public/restaurant/{SLUG}/menu-file" in menu_url
    # No GridFS id leaked (checked on inner restaurant object)
    assert "menuFileId" not in data

    # Serve route works unauthenticated and is application/pdf
    anon = requests.get(f"{BASE_URL}{menu_url}", timeout=20,
                        headers={"User-Agent": "Mozilla/5.0"})
    assert anon.status_code == 200, anon.text
    ct = anon.headers.get("content-type", "")
    assert "application/pdf" in ct, f"Expected application/pdf, got {ct}"
    assert anon.content.startswith(b"%PDF"), "Body is not a PDF"


def test_delete_menu_file_removes_link(owner_session):
    # ensure file exists first
    up = owner_session.post(f"{BASE_URL}/api/restaurant/menu-file",
                            files={"file": ("menu.pdf", MIN_PDF, "application/pdf")}, timeout=30)
    assert up.status_code == 200
    # Delete
    d = owner_session.delete(f"{BASE_URL}/api/restaurant/menu-file", timeout=20)
    assert d.status_code in (200, 204), d.text

    pr = requests.get(f"{BASE_URL}/api/public/restaurant/{SLUG}", timeout=20,
                      headers={"User-Agent": "Mozilla/5.0"})
    assert pr.status_code == 200
    assert pr.json().get("restaurant", {}).get("menuFileUrl", "") == ""

    anon = requests.get(f"{BASE_URL}/api/public/restaurant/{SLUG}/menu-file", timeout=20,
                        headers={"User-Agent": "Mozilla/5.0"})
    assert anon.status_code == 404


def test_restore_menu_file_for_next_tests(owner_session):
    up = owner_session.post(f"{BASE_URL}/api/restaurant/menu-file",
                            files={"file": ("menu.pdf", MIN_PDF, "application/pdf")}, timeout=30)
    assert up.status_code == 200
