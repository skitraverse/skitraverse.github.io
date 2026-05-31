"""Contract tests: verify static/api.yaml matches what the frontend assumes.

These tests parse the local OpenAPI spec and assert the specific fields and
values the order form depends on. If a backend developer changes api.yaml in a
way that breaks the frontend (e.g. renames a variant value, drops a required
field, changes a response shape), these tests will fail immediately — without
needing to deploy anything.
"""
import pathlib
import pytest
import yaml

SPEC_PATH = pathlib.Path(__file__).parent.parent / "static" / "api.yaml"

# Variant strings the frontend sends inside line_items[].variant
FRONTEND_VARIANTS = {"HARDCOVER", "EBOOK", "HARDCOVER_DE", "EBOOK_DE"}
FRONTEND_PHYSICAL_VARIANTS = {"HARDCOVER", "HARDCOVER_DE"}


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
                         "street1", "city", "postcode", "country", "line_items"}
    missing = frontend_required - required
    assert not missing, f"Fields required by frontend but not in spec: {missing}"


def test_phone_is_optional(spec):
    """Phone is optional — backend must not reject orders without it."""
    required = set(spec["components"]["schemas"]["OrderForm"].get("required", []))
    assert "phone" not in required, "phone must not be required in OrderForm"


def test_line_item_schema_exists(spec):
    assert "LineItem" in spec["components"]["schemas"], "LineItem schema missing"


def test_line_item_required_fields(spec):
    li = spec["components"]["schemas"]["LineItem"]
    required = set(li.get("required", []))
    for field in ("variant", "qty", "unit_price"):
        assert field in required, f"LineItem missing required field: {field}"


def test_line_item_variant_values(spec):
    """All frontend variant strings must appear in the spec's 400 error example."""
    li = spec["components"]["schemas"]["LineItem"]
    assert "variant" in li["properties"], "variant missing from LineItem properties"

    error_example = (spec["paths"]["/api/order"]["post"]
                     ["responses"]["400"]["content"]["application/json"]["example"])
    error_text = error_example.get("error", "")
    for variant in FRONTEND_VARIANTS:
        assert variant in error_text, \
            f"Expected '{variant}' in 400 error example, got: {error_text}"
    for legacy in ("book_variant", "DE_EBOOK", " DE,", "GLOBAL"):
        assert legacy not in error_text, \
            f"Legacy value '{legacy}' still in spec error example — remove it"


def test_order_code_documented(spec):
    props = spec["components"]["schemas"]["OrderForm"]["properties"]
    assert "order_code" in props, "order_code field missing from OrderForm"


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
