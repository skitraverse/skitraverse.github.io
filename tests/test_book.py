"""Playwright tests for the book page subscribe form."""
import json
import pytest
from playwright.sync_api import Page, Route

BASE_URL = "http://localhost:8000"
BOOK_URL = f"{BASE_URL}/winter-cdt-book/winter-cdt-book/"

pytestmark = pytest.mark.usefixtures("require_dev_server")


def _inject_fake_altcha(page: Page) -> None:
    page.evaluate("""() => {
        const widget = document.getElementById('ml-book-altcha');
        if (!widget) return;
        Object.defineProperty(widget, 'value', {
            get: () => 'fakeAltchaPayload', configurable: true
        });
        widget.dispatchEvent(new CustomEvent('statechange', {
            detail: { state: 'verified', payload: 'fakeAltchaPayload' }
        }));
    }""")


def test_subscribe_button_disabled_initially(page: Page):
    page.goto(BOOK_URL)
    assert page.locator("#ml-book-btn").is_disabled()


def test_subscribe_button_enables_when_complete(page: Page):
    page.goto(BOOK_URL)
    page.fill("#ml-book-name", "Maria Muster")
    page.fill("#ml-book-email", "maria@example.com")
    assert page.locator("#ml-book-btn").is_disabled(), "Button must stay disabled before altcha"
    _inject_fake_altcha(page)
    assert page.locator("#ml-book-btn").is_enabled(), "Button must enable after altcha + fields filled"


def test_subscribe_success_message_visible(page: Page):
    """Success message must stay visible after the form is hidden."""
    def handle(route: Route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"message": "subscribed"}))

    page.route("**/api/subscribe", handle)
    page.goto(BOOK_URL)
    page.fill("#ml-book-name", "Maria Muster")
    page.fill("#ml-book-email", "maria@example.com")
    _inject_fake_altcha(page)
    page.click("#ml-book-btn")

    status = page.locator("#ml-book-status")
    status.wait_for(state="visible", timeout=5000)
    assert "list" in status.inner_text().lower() or "touch" in status.inner_text().lower()


def test_subscribe_sends_correct_fields(page: Page):
    """POST body must use name/email keys (not customer_name/customer_email)."""
    captured = {}

    def handle(route: Route):
        try:
            captured["body"] = route.request.post_data_json
        except Exception:
            captured["body"] = {}
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"message": "subscribed"}))

    page.route("**/api/subscribe", handle)
    page.goto(BOOK_URL)
    page.fill("#ml-book-name", "Maria Muster")
    page.fill("#ml-book-email", "maria@example.com")
    _inject_fake_altcha(page)
    page.click("#ml-book-btn")
    page.locator("#ml-book-status").wait_for(state="visible", timeout=5000)

    body = captured.get("body", {})
    assert body.get("name") == "Maria Muster", f"Expected name field, got: {body}"
    assert body.get("email") == "maria@example.com", f"Expected email field, got: {body}"
    assert "customer_name" not in body, "Must not send customer_name"
    assert "customer_email" not in body, "Must not send customer_email"
    assert "nonce" not in body, "Must not send nonce"
    assert body.get("altcha") == "fakeAltchaPayload"
