"""Contract tests: verify static/api.yaml matches what the frontend assumes.

These tests parse the local OpenAPI spec and assert the specific fields and
values the order form depends on. If a backend developer changes api.yaml in a
way that breaks the frontend (e.g. renames a variant value, drops a required
field, changes a response shape), these tests will fail immediately — without
needing to deploy anything.
"""
import json
import pathlib
import pytest
import yaml

SPEC_PATH = pathlib.Path(__file__).parent.parent / "static" / "api.yaml"

# Values the frontend radio buttons send for book_variant
FRONTEND_VARIANTS = {"HARDCOVER", "EBOOK"}
# Variants the backend says are valid (from spec description / example error)
BACKEND_PHYSICAL_VARIANTS = {"HARDCOVER"}


@pytest.fixture(scope="module")
def spec():
    with open(SPEC_PATH) as f:
        return yaml.safe_load(f)


def test_spec_file_exists():
    assert SPEC_PATH.exists(), f"OpenAPI spec not found at {SPEC_PATH}"


def test_order_endpoint_exists(spec):
    assert "/api/order" in spec["paths"], "POST /api/order missing from spec"
    assert "post" in spec["paths"]["/api/order"], "POST method missing on /api/order"


def test_order_required_fields(spec):
    """Fields the frontend always sends must all be listed as required in spec."""
    order_schema = spec["components"]["schemas"]["OrderForm"]
    required = set(order_schema.get("required", []))
    frontend_required = {"nonce", "altcha", "customer_name", "customer_email",
                         "street1", "city", "postcode", "country", "book_variant"}
    missing = frontend_required - required
    assert not missing, f"Fields required by frontend but not in spec: {missing}"


def test_book_variant_values_match_frontend(spec):
    """HARDCOVER must be valid per the spec description; GLOBAL must not be."""
    order_schema = spec["components"]["schemas"]["OrderForm"]
    props = order_schema["properties"]
    assert "book_variant" in props, "book_variant missing from OrderForm properties"

    # The spec's error example says "book_variant must be HARDCOVER, EBOOK, DE, or DE_EBOOK"
    error_example = (spec["paths"]["/api/order"]["post"]
                     ["responses"]["400"]["content"]["application/json"]["example"])
    error_text = error_example.get("error", "")
    assert "HARDCOVER" in error_text, f"Expected 'HARDCOVER' in 400 error example, got: {error_text}"
    assert "EBOOK" in error_text, f"Expected 'EBOOK' in 400 error example, got: {error_text}"
    assert "GLOBAL" not in error_text, \
        "'GLOBAL' appeared in spec — frontend must not send GLOBAL"


def test_prices_response_shape(spec):
    prices_schema = spec["components"]["schemas"]["PricesResponse"]
    required = set(prices_schema.get("required", []))
    assert "physical" in required
    assert "ebook" in required


def test_price_set_has_chf(spec):
    price_set = spec["components"]["schemas"]["PriceSet"]
    assert "CHF" in price_set.get("required", []), "CHF must be required in PriceSet"


def test_captcha_endpoint_exists(spec):
    assert "/api/captcha" in spec["paths"]
    assert "get" in spec["paths"]["/api/captcha"]


def test_captcha_response_fields(spec):
    challenge_schema = spec["components"]["schemas"]["Challenge"]
    required = set(challenge_schema.get("required", []))
    for field in ("algorithm", "challenge", "maxnumber", "salt", "signature"):
        assert field in required, f"Captcha field '{field}' not required in spec"


def test_order_response_has_order_id(spec):
    resp_schema = spec["components"]["schemas"]["OrderResponse"]
    assert "order_id" in resp_schema.get("required", [])


def test_honeypot_field_documented(spec):
    props = spec["components"]["schemas"]["OrderForm"]["properties"]
    assert "website" in props, "Honeypot field 'website' missing from spec"


def test_subscribe_endpoint_exists(spec):
    assert "/api/subscribe" in spec["paths"], "POST /api/subscribe missing from spec"
    assert "post" in spec["paths"]["/api/subscribe"]


def test_subscribe_required_fields(spec):
    schema = spec["components"]["schemas"]["SubscribeForm"]
    required = set(schema.get("required", []))
    for field in ("altcha", "name", "email"):
        assert field in required, f"SubscribeForm missing required field: {field}"
    assert "nonce" not in required, "SubscribeForm must not require nonce"


def test_subscribe_honeypot_documented(spec):
    props = spec["components"]["schemas"]["SubscribeForm"]["properties"]
    assert "website" in props, "Honeypot 'website' missing from SubscribeForm"


def test_subscribe_response_has_message(spec):
    schema = spec["components"]["schemas"]["SubscribeResponse"]
    assert "message" in schema.get("required", []), "SubscribeResponse must require 'message'"
    assert "order_id" not in schema.get("required", []), "SubscribeResponse must not have order_id"


