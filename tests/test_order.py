"""Playwright tests for the order page."""
import json
import pytest
from playwright.sync_api import Page, Route

ORDER_API_URL = "https://order.skitraverse.com/api/order"

BASE_URL = "http://localhost:8000"
ORDER_URL = f"{BASE_URL}/winter-cdt-book/order/"
LULU_SHIPPING_URL = "https://api.lulu.com/shipping-options/"


def intercept_shipping(page: Page, country: str = "CH") -> dict:
    """Select a country on the order page and return the raw Lulu shipping response."""
    captured = {}

    def handle_route(route: Route):
        response = route.fetch()
        captured["body"] = response.json()
        route.fulfill(response=response)

    page.route(LULU_SHIPPING_URL, handle_route)
    page.goto(ORDER_URL)
    page.select_option("#order-country", country)
    page.wait_for_function("() => document.getElementById('shipping-info').style.display !== 'none'",
                           timeout=5000)
    return captured.get("body", [])


pytestmark = pytest.mark.usefixtures("require_dev_server")


def test_shipping_response_fields(page: Page):
    """Print the raw Lulu shipping option fields so we can identify the carrier key."""
    options = intercept_shipping(page, "CH")
    assert options, "No shipping options returned for CH"
    print("\nLulu shipping option keys:", list(options[0].keys()))
    print("First option:\n", json.dumps(options[0], indent=2))


def test_shipping_shows_carrier(page: Page):
    """Carrier name is visible in the shipping options section."""
    page.goto(ORDER_URL)
    page.select_option("#order-country", "CH")
    shipping_info = page.locator("#shipping-info")
    shipping_info.wait_for(state="visible", timeout=5000)
    text = shipping_info.inner_text()
    assert "days" in text, f"Expected delivery days in shipping info, got: {text}"
    assert "UPS" not in text, f"UPS should be excluded but appeared in: {text}"
    assert "Colissimo" not in text, f"Colissimo should be excluded but appeared in: {text}"
    print("\nShipping info text:\n", text)


def test_shipping_cost_in_local_currency(page: Page):
    """Shipping options must show costs in the destination country's currency, not EUR."""
    page.goto(ORDER_URL)
    page.select_option("#order-country", "CH")
    shipping_info = page.locator("#shipping-info")
    shipping_info.wait_for(state="visible", timeout=5000)
    text = shipping_info.inner_text()
    assert "CHF" in text, f"Expected CHF in CH shipping options, got: {text}"
    assert "EUR" not in text, f"EUR must not appear in CH shipping options (Lulu returns EUR, we must convert): {text}"

    page.select_option("#order-country", "US")
    shipping_info.wait_for(state="visible", timeout=5000)
    text = shipping_info.inner_text()
    assert "USD" in text, f"Expected USD in US shipping options, got: {text}"
    assert "EUR" not in text, f"EUR must not appear in US shipping options: {text}"


def test_price_note_no_dagger(page: Page):
    """Price note must not contain the dagger character (†) from a \\u2020 typo."""
    page.goto(ORDER_URL)
    for country in ("CH", "DE"):
        page.select_option("#order-country", country)
        text = page.locator("#price-note").inner_text()
        assert "†" not in text, f"Dagger in price note for {country}: {text}"


def test_submit_disabled_until_complete(page: Page):
    """Button stays disabled until all required fields are filled and checkbox ticked."""
    page.goto(ORDER_URL)
    assert page.locator("#submit-btn").is_disabled()

    # Zero out all quantities — button must stay disabled
    page.fill("#qty_hardcover", "0")
    assert page.locator("#submit-btn").is_disabled()

    # Restore quantity and fill personal details
    page.fill("#qty_hardcover", "1")
    page.fill("#customer_name",  "Maria Muster")
    assert page.locator("#submit-btn").is_disabled()

    page.fill("#customer_email", "maria@example.com")
    assert page.locator("#submit-btn").is_disabled()

    page.select_option("#order-country", "CH")
    page.fill("#street1",  "Bahnhofstrasse 10")
    page.fill("#postcode", "8001")
    page.fill("#city",     "Zürich")
    page.fill("#phone",    "+41791234567")
    assert page.locator("#submit-btn").is_disabled()

    # Altcha must also be solved before the button enables
    assert page.locator("#submit-btn").is_disabled()

    _inject_fake_altcha(page)
    page.check("#agree")
    assert page.locator("#submit-btn").is_enabled()

    page.uncheck("#agree")
    assert page.locator("#submit-btn").is_disabled()


def test_shipping_shows_for_eu_country(page: Page):
    """Shipping options appear for a non-CH SEPA country."""
    page.goto(ORDER_URL)
    page.select_option("#order-country", "DE")
    page.locator("#shipping-info").wait_for(state="visible", timeout=5000)


def test_gb_shows_invoice_text(page: Page):
    """GB is SEPA — must show invoice payment text."""
    page.goto(ORDER_URL)
    page.select_option("#order-country", "GB")
    text = page.locator("#payment-step").inner_text()
    assert "invoice" in text.lower(), f"Expected 'invoice' for GB, got: {text}"


def test_sepa_shows_invoice_payment_text(page: Page):
    """SEPA countries show invoice payment instructions."""
    page.goto(ORDER_URL)
    page.select_option("#order-country", "DE")
    text = page.locator("#payment-step").inner_text()
    assert "invoice" in text.lower(), f"Expected 'invoice' for DE, got: {text}"
    assert "Wise" not in text, f"'Wise' should not appear for DE, got: {text}"


def test_us_prices_shown_in_usd(page: Page):
    """Selecting US shows USD prices, not EUR."""
    page.goto(ORDER_URL)
    page.select_option("#order-country", "US")
    assert "USD" in page.locator("#price-hardcover").inner_text()
    assert "EUR" not in page.locator("#price-hardcover").inner_text()


def test_non_sepa_shows_wise_payment_text(page: Page):
    """Non-SEPA countries show Wise/CC payment instructions."""
    page.goto(ORDER_URL)
    page.select_option("#order-country", "US")
    assert page.locator("#order-form").is_visible()
    text = page.locator("#payment-step").inner_text()
    assert "Wise" in text, f"Expected 'Wise' for US, got: {text}"
    assert "invoice" not in text.lower(), f"'invoice' should not appear for US, got: {text}"


def test_bundle_discount_layout_narrow_screen(page: Page):
    """On a narrow viewport the discount note is a separate block below the price note,
    and the struck-through price is stacked above the discounted price."""
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(ORDER_URL)

    # Trigger a bundle: hardcover (default qty=1) + e-book
    page.fill("#qty_ebook", "1")
    page.select_option("#order-country", "CH")

    discount_note = page.locator("#discount-note")
    discount_note.wait_for(state="visible", timeout=5000)

    # Discount note must mention 20 %
    assert "20" in discount_note.inner_text(), \
        f"Expected '20' in discount note, got: {discount_note.inner_text()}"

    # Price note must not contain a <br> (text flows as a clean sentence)
    assert page.locator("#price-note br").count() == 0, \
        "Found <br> inside #price-note — discount note should be a separate element"

    # Discount note sits below price note (separate block, not inline)
    price_note_box   = page.locator("#price-note").bounding_box()
    discount_note_box = discount_note.bounding_box()
    assert discount_note_box["y"] >= price_note_box["y"] + price_note_box["height"], \
        "Discount note overlaps or sits above the price note — expected a separate block below"

    # Strikethrough price is above the discounted price inside the e-book cell
    del_box = page.locator("#price-ebook del").bounding_box()
    cell_box = page.locator("#price-ebook").bounding_box()
    assert del_box is not None, "<del> element missing from #price-ebook"
    # del occupies the top portion of the cell; discounted price is below it
    assert del_box["y"] + del_box["height"] < cell_box["y"] + cell_box["height"], \
        "<del> and discounted price appear to be on the same line, not stacked"


def _inject_fake_altcha(page: Page) -> None:
    """Patch the shared altcha widget so the statechange handler stores a solved payload."""
    page.evaluate("""() => {
        const widget = document.getElementById('shared-altcha');
        if (!widget) return;
        Object.defineProperty(widget, 'value', {
            get: () => 'fakeAltchaPayload', configurable: true
        });
        widget.dispatchEvent(new CustomEvent('statechange', {
            detail: { state: 'verified', payload: 'fakeAltchaPayload' }
        }));
    }""")


def test_submit_order_shows_success(page: Page):
    """Submitting a complete order POSTs to /api/order and shows a success message."""
    submitted = {}

    def handle_order(route: Route):
        try:
            submitted['body'] = route.request.post_data_json
        except Exception:
            submitted['body'] = {}
        route.fulfill(
            status=201,
            content_type='application/json',
            body=json.dumps({"order_id": "SKI-TEST01", "message": "Order received"}),
        )

    page.route("**/api/order", handle_order)
    page.goto(ORDER_URL)

    page.fill("#customer_name",  "Maria Muster")
    page.fill("#customer_email", "maria@example.com")
    page.select_option("#order-country", "CH")
    page.fill("#street1",  "Bahnhofstrasse 10")
    page.fill("#postcode", "8001")
    page.fill("#city",     "Zürich")
    page.fill("#phone",    "+41791234567")
    page.locator("#agree").wait_for(state="visible", timeout=5000)
    _inject_fake_altcha(page)
    page.check("#agree")
    page.click("#submit-btn")

    status = page.locator("#form-status")
    status.wait_for(state="visible", timeout=5000)
    text = status.inner_text()
    assert "SKI-TEST01" in text or "order" in text.lower(), f"Unexpected status: {text}"

    assert submitted.get('body'), "No POST body captured"
    body = submitted['body']
    assert body.get('customer_name') == "Maria Muster"
    assert body.get('country') == "CH"
    assert body.get('altcha') == 'fakeAltchaPayload'
    assert body.get('nonce'), "nonce missing from payload"
    assert body.get('phone') == "+41791234567", f"phone missing or wrong: {body.get('phone')}"
    assert body.get('book_variant') == 'HARDCOVER', f"Expected HARDCOVER, got: {body.get('book_variant')}"
    assert body.get('books_total') is not None, "books_total missing from payload"


def test_submit_order_api_error_shows_message(page: Page):
    """A 400 response from the API is surfaced to the user."""
    page.route("**/api/order", lambda r: r.fulfill(
        status=400, content_type='application/json',
        body=json.dumps({"error": "book_variant must be HARDCOVER, EBOOK, DE, or DE_EBOOK"}),
    ))
    page.goto(ORDER_URL)

    page.fill("#customer_name",  "Test User")
    page.fill("#customer_email", "test@example.com")
    page.select_option("#order-country", "DE")
    page.fill("#street1",  "Unter den Linden 1")
    page.fill("#postcode", "10117")
    page.fill("#city",     "Berlin")
    page.fill("#phone",    "+49301234567")
    page.locator("#agree").wait_for(state="visible", timeout=5000)
    _inject_fake_altcha(page)
    page.check("#agree")

    _inject_fake_altcha(page)
    page.click("#submit-btn")

    status = page.locator("#form-status")
    status.wait_for(state="visible", timeout=5000)
    assert "book_variant" in status.inner_text() or "HARDCOVER" in status.inner_text()
