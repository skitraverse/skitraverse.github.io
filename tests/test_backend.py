"""Integration tests against the live order.skitraverse.com backend."""
import pytest
import requests
import uuid

BASE = "https://order.skitraverse.com"


@pytest.fixture(scope="session", autouse=True)
def require_backend():
    try:
        r = requests.get(f"{BASE}/api/prices", timeout=5)
        r.raise_for_status()
    except Exception as e:
        pytest.skip(f"Backend not reachable: {e}")


# ---------------------------------------------------------------------------
# GET /api/prices
# ---------------------------------------------------------------------------

def test_prices_structure():
    r = requests.get(f"{BASE}/api/prices", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "physical" in data and "ebook" in data
    for tier in ("physical", "ebook"):
        assert "CHF" in data[tier], f"CHF missing from {tier}"
        assert "EUR" in data[tier], f"EUR missing from {tier}"
        assert isinstance(data[tier]["CHF"], (int, float))
        assert data[tier]["CHF"] > 0


def test_prices_physical_higher_than_ebook():
    data = requests.get(f"{BASE}/api/prices", timeout=5).json()
    assert data["physical"]["CHF"] > data["ebook"]["CHF"]


# ---------------------------------------------------------------------------
# GET /api/captcha
# ---------------------------------------------------------------------------

def test_captcha_challenge_fields():
    r = requests.get(f"{BASE}/api/captcha", timeout=5)
    assert r.status_code == 200
    ch = r.json()
    for field in ("algorithm", "challenge", "maxnumber", "salt", "signature"):
        assert field in ch, f"Missing field: {field}"
    assert ch["algorithm"] == "SHA-256"
    assert "?expires=" in ch["salt"]


# ---------------------------------------------------------------------------
# POST /api/order — validation rejections (no real captcha needed)
# ---------------------------------------------------------------------------

def test_order_missing_fields_returns_4xx():
    r = requests.post(f"{BASE}/api/order", json={}, timeout=5)
    assert 400 <= r.status_code < 500


def test_order_honeypot_returns_400():
    r = requests.post(f"{BASE}/api/order", json={
        "nonce": "00000000-0000-0000-0000-000000000000",
        "altcha": "fake",
        "customer_name": "Test",
        "customer_email": "test@example.com",
        "street1": "Teststr. 1",
        "city": "Bern",
        "postcode": "3000",
        "country": "CH",
        "line_items": [{"variant": "HARDCOVER", "qty": 1, "unit_price": 42.0}],
        "website": "http://spam.example.com",  # honeypot
    }, timeout=5)
    assert 400 <= r.status_code < 500


def test_order_invalid_variant_returns_400():
    r = requests.post(f"{BASE}/api/order", json={
        "nonce": str(uuid.uuid4()),
        "altcha": "fake",
        "customer_name": "Test",
        "customer_email": "test@example.com",
        "street1": "Teststr. 1",
        "city": "Bern",
        "postcode": "3000",
        "country": "CH",
        "line_items": [{"variant": "GLOBAL", "qty": 1, "unit_price": 42.0}],
    }, timeout=5)
    assert 400 <= r.status_code < 500


def test_order_bad_captcha_returns_400():
    """A well-formed payload with a fake altcha token must be rejected."""
    r = requests.post(f"{BASE}/api/order", json={
        "nonce": str(uuid.uuid4()),
        "altcha": "bm90dmFsaWQ=",  # base64("notvalid")
        "customer_name": "Test User",
        "customer_email": "test@example.com",
        "street1": "Bahnhofstrasse 10",
        "city": "Zürich",
        "postcode": "8001",
        "country": "CH",
        "line_items": [{"variant": "HARDCOVER", "qty": 1, "unit_price": 42.0}],
    }, timeout=5)
    assert 400 <= r.status_code < 500
