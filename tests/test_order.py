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


def test_cross_language_bundle_discount(page: Page):
    """HARDCOVER (EN) + EBOOK_DE triggers the 20 % bundle discount.

    RED: verifies that the cross-language combination — not just same-language
    pairs — activates the discount both in the UI and in the submitted payload.
    """
    submitted = {}

    def handle_order(route: Route):
        try:
            submitted['body'] = route.request.post_data_json
        except Exception:
            submitted['body'] = {}
        route.fulfill(
            status=201,
            content_type='application/json',
            body=json.dumps({"order_id": "SKI-XBUNDLE", "message": "Order received"}),
        )

    page.route("**/api/order", handle_order)
    page.goto(ORDER_URL)

    # Country first so qty-change events fire price updates
    page.select_option("#order-country", "CH")
    # hardcover defaults to qty=1; add one German e-book
    page.fill("#qty_de_ebook", "1")

    # Discount note must appear and mention 20 %
    discount_note = page.locator("#discount-note")
    discount_note.wait_for(state="visible", timeout=5000)
    assert "20" in discount_note.inner_text(), \
        f"Expected '20' in discount note for cross-language bundle, got: {discount_note.inner_text()}"

    # #price-de-ebook must show a struck-through list price
    assert page.locator("#price-de-ebook del").count() > 0, \
        "<del> missing from #price-de-ebook for HARDCOVER + EBOOK_DE bundle"

    # Fill details and submit
    page.fill("#customer_name",  "Hans Muster")
    page.fill("#customer_email", "hans@example.com")
    page.fill("#street1",  "Hauptgasse 5")
    page.fill("#postcode", "3011")
    page.fill("#city",     "Bern")
    _inject_fake_altcha(page)
    page.check("#agree")
    page.click("#submit-btn")

    page.locator("#form-status").wait_for(state="visible", timeout=5000)

    assert submitted.get('body'), "No POST body captured"
    items = submitted['body'].get('line_items', [])
    variants = [i['variant'] for i in items]
    assert 'HARDCOVER' in variants, f"HARDCOVER missing from line_items: {items}"
    assert 'EBOOK_DE'  in variants, f"EBOOK_DE missing from line_items: {items}"

    ebook_de = next(i for i in items if i['variant'] == 'EBOOK_DE')
    hardcover = next(i for i in items if i['variant'] == 'HARDCOVER')
    # CHF list prices: physical=42.0, ebook=20.0 → discounted ebook=16.0
    assert ebook_de['unit_price'] < hardcover['unit_price'], \
        f"EBOOK_DE unit_price should be less than HARDCOVER: {ebook_de['unit_price']} vs {hardcover['unit_price']}"
    assert abs(ebook_de['unit_price'] - 16.0) < 0.02, \
        f"Expected EBOOK_DE unit_price ~16.00 CHF (20 % off 20.00), got: {ebook_de['unit_price']}"


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
    items = body.get('line_items')
    assert items, "line_items missing from payload"
    assert any(i['variant'] == 'HARDCOVER' for i in items), \
        f"Expected HARDCOVER in line_items, got: {items}"
    assert all(i['qty'] >= 1 for i in items), "all line_items must have qty >= 1"
    assert all(i['unit_price'] > 0 for i in items), "all line_items must have unit_price > 0"


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
    page.locator("#agree").wait_for(state="visible", timeout=5000)
    _inject_fake_altcha(page)
    page.check("#agree")

    _inject_fake_altcha(page)
    page.click("#submit-btn")

    status = page.locator("#form-status")
    status.wait_for(state="visible", timeout=5000)
    assert "book_variant" in status.inner_text() or "HARDCOVER" in status.inner_text()


def _inject_fake_subscribe_altcha(page: Page) -> None:
    """Patch the subscribe altcha widget so its statechange handler stores a payload."""
    page.evaluate("""() => {
        const widget = document.getElementById('subscribe-altcha');
        if (!widget) return;
        Object.defineProperty(widget, 'value', {
            get: () => 'fakeSubscribePayload', configurable: true
        });
        widget.dispatchEvent(new CustomEvent('statechange', {
            detail: { state: 'verified', payload: 'fakeSubscribePayload' }
        }));
    }""")


def test_subscribe_checkbox_present(page: Page):
    """Order page has an opt-in subscribe checkbox, unchecked by default."""
    page.goto(ORDER_URL)
    checkbox = page.locator("#subscribe")
    checkbox.wait_for(state="attached", timeout=3000)
    assert not checkbox.is_checked(), "Subscribe checkbox must be unchecked by default"


def test_subscribe_fires_when_checked(page: Page):
    """Ticking the subscribe checkbox causes POST /api/subscribe after a 201 order."""
    subscribe_body = {}

    def handle_subscribe(route: Route):
        try:
            subscribe_body['data'] = route.request.post_data_json
        except Exception:
            subscribe_body['data'] = {}
        route.fulfill(
            status=200,
            content_type='application/json',
            body=json.dumps({"message": "You're on the list!"}),
        )

    page.route("**/api/order", lambda r: r.fulfill(
        status=201,
        content_type='application/json',
        body=json.dumps({"order_id": "SKI-SUB01", "message": "Order received"}),
    ))
    page.route("**/api/subscribe", handle_subscribe)
    page.goto(ORDER_URL)

    page.fill("#customer_name",  "Maria Muster")
    page.fill("#customer_email", "maria@example.com")
    page.select_option("#order-country", "CH")
    page.fill("#street1",  "Bahnhofstrasse 10")
    page.fill("#postcode", "8001")
    page.fill("#city",     "Zürich")
    _inject_fake_altcha(page)
    _inject_fake_subscribe_altcha(page)
    page.check("#subscribe")
    page.check("#agree")
    page.click("#submit-btn")

    page.locator("#form-status").wait_for(state="visible", timeout=5000)
    # Wait for the async subscribe call to complete
    page.wait_for_function(
        "() => document.getElementById('form-status').innerText.includes('mailing list')",
        timeout=5000,
    )

    assert subscribe_body.get('data'), "POST /api/subscribe was not called"
    sub = subscribe_body['data']
    assert sub.get('name')  == "Maria Muster",      f"Wrong name in subscribe payload: {sub}"
    assert sub.get('email') == "maria@example.com", f"Wrong email in subscribe payload: {sub}"
    assert sub.get('altcha') == 'fakeSubscribePayload', \
        f"Wrong altcha in subscribe payload: {sub}"
    assert sub.get('website') == '', f"Honeypot must be empty string, got: {sub}"


def test_subscribe_not_called_when_unchecked(page: Page):
    """Leaving the subscribe checkbox unticked does not call /api/subscribe."""
    subscribe_called = {}

    page.route("**/api/order", lambda r: r.fulfill(
        status=201,
        content_type='application/json',
        body=json.dumps({"order_id": "SKI-NOSUB", "message": "Order received"}),
    ))
    page.route("**/api/subscribe", lambda r: (
        subscribe_called.update({"called": True}),
        r.fulfill(status=200, content_type='application/json',
                  body=json.dumps({"message": "ok"})),
    ))

    page.goto(ORDER_URL)
    page.fill("#customer_name",  "Hans Muster")
    page.fill("#customer_email", "hans@example.com")
    page.select_option("#order-country", "CH")
    page.fill("#street1",  "Hauptgasse 5")
    page.fill("#postcode", "3011")
    page.fill("#city",     "Bern")
    _inject_fake_altcha(page)
    # subscribe checkbox left unchecked
    page.check("#agree")
    page.click("#submit-btn")

    page.locator("#form-status").wait_for(state="visible", timeout=5000)
    page.wait_for_timeout(500)  # brief wait to confirm no subscribe call fires
    assert not subscribe_called.get('called'), "/api/subscribe must not be called when checkbox is unticked"
