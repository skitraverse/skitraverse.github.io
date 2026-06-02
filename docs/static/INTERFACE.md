# Skitraverse Frontend–Backend Interface

This document describes everything a backend engineer needs to know about the
static website at `skitraverse.com` and its relationship to the API at
`order.skitraverse.com`. Keep it in sync with `static/api.yml`, which is the
authoritative OpenAPI 3.0.3 contract.

---

## 1. API base URL

The frontend reads `SHOP_API_URL` from the Pelican build context. If the
variable is absent (local dev), it falls back to:

```
https://order.skitraverse.com
```

All paths in this document are relative to that base.

---

## 2. Endpoints called by the browser

### 2.1 `GET /api/prices`

Called once on page load by `templates/order.html`. No authentication.

**Response (200)**

```json
{
  "physical": { "CHF": 42.0, "EUR": 45.81, "USD": 53.86, "GBP": 39.65, "AUD": 74.48, "CAD": 73.75, "JPY": 8489.0 },
  "ebook":    { "CHF": 20.0, "EUR": 21.81, "USD": 25.65, "GBP": 18.88, "AUD": 35.47, "CAD": 35.12, "JPY": 4042.0 }
}
```

Schema: `PricesResponse` → `PriceSet`. All seven currencies (`CHF EUR USD GBP
AUD CAD JPY`) are required in both tiers. The frontend uses these values both
for display and as exchange-rate ratios for currency conversion — the ratio
`physical[to] / physical[from]` converts any amount between two currencies.
Hard-coded fallback values exist in the JS so the form is usable even if this
request fails.

### 2.2 `GET /api/captcha`

Called by the Altcha widget (`altcha-widget` custom element,
`cdn.jsdelivr.net/npm/altcha`). No authentication.

**Response (200)** — schema `Challenge`:

| Field       | Type   | Notes                                              |
|-------------|--------|----------------------------------------------------|
| `algorithm` | string | Always `"SHA-256"`                                 |
| `challenge` | string | SHA-256 hex digest the client finds a pre-image for |
| `maxnumber` | int64  | Upper bound for brute-force search                 |
| `salt`      | string | Must contain `?expires=<unix_ts>`                  |
| `signature` | string | HMAC-SHA256 of the challenge; verified on submit   |

### 2.3 `POST /api/order`

Main order submission. No authentication.

**Request body** — `application/json`, schema `OrderForm`:

| Field           | Required | Type            | Notes                                                                 |
|-----------------|----------|-----------------|-----------------------------------------------------------------------|
| `nonce`         | yes      | string          | `crypto.randomUUID()` — backend rejects duplicates with 409           |
| `altcha`        | yes      | string          | Base64 Altcha proof-of-work payload from the widget                   |
| `customer_name` | yes      | string          | Full name                                                             |
| `customer_email`| yes      | string          | Confirmation link sent here                                           |
| `street1`       | yes      | string          | First address line                                                    |
| `city`          | yes      | string          |                                                                       |
| `postcode`      | yes      | string          |                                                                       |
| `country`       | yes      | string          | ISO 3166-1 alpha-2, e.g. `"CH"`, `"DE"`, `"US"`                     |
| `line_items`    | yes      | LineItem[]      | Cart contents; at least one item required (see §3)                    |
| `phone`         | no       | string          | E.164, e.g. `+41791234567`; forwarded to Lulu carrier if present     |
| `order_code`    | no       | string          | Bookstore, sales, or charity-drive code; stored for owner review      |
| `shipping_level`| no       | string          | Lulu level: `MAIL`, `PRIORITY_MAIL`, `GROUND`, `EXPEDITED`, `EXPRESS`|
| `shipping_cost` | no       | number          | Shipping cost in the order currency as quoted to the customer         |
| `street2`       | no       | string          | Second address line                                                   |
| `state`         | no       | string          | Required by Lulu for US, CA, AU — frontend collects and sends this; `null` for all other countries |
| `website`       | no       | string          | Honeypot — must be absent or empty; non-empty → 400                   |

**Responses:**

| Status | Meaning                                                        |
|--------|----------------------------------------------------------------|
| 201    | Order created; confirmation email sent to `customer_email`     |
| 400    | Validation failure, bad CAPTCHA, or honeypot triggered         |
| 409    | Nonce already used (duplicate submission)                      |

**201 body** — schema `OrderResponse`:

```json
{ "order_id": "SKI-X7K9M2", "message": "Order received" }
```

The frontend displays `order_id` in the success message.

**400 body** (example):

```json
{ "error": "line_items[].variant must be one of: HARDCOVER, EBOOK, HARDCOVER_DE, EBOOK_DE" }
```

The frontend surfaces `data.error` or `data.message` directly to the user.

### 2.4 `POST /api/subscribe`

Called by the mailing-list subscribe form rendered by `templates/subscribe.html`.
No authentication.

**Request body** — schema `SubscribeForm`:

| Field     | Required | Notes                                    |
|-----------|----------|------------------------------------------|
| `altcha`  | yes      | Altcha proof-of-work payload             |
| `name`    | yes      |                                          |
| `email`   | yes      |                                          |
| `website` | no       | Honeypot — must be absent or empty       |

Note: no `nonce` field. This endpoint is idempotent.

**Responses:**

| Status | Meaning                          |
|--------|----------------------------------|
| 200    | Email recorded                   |
| 400    | Bad CAPTCHA, validation failure  |

**200 body** — schema `SubscribeResponse`:

```json
{ "message": "You're on the list!" }
```

### 2.5 `GET /api/confirm?token=<token>`

Linked from the confirmation email. Not called by the order form directly.

| Status | Meaning              |
|--------|----------------------|
| 200    | Order confirmed      |
| 400    | Invalid token        |
| 410    | Token already used   |

On a 200 response the backend branches by `book_variant`, derived from the
cart using the priority `HARDCOVER > EBOOK > HARDCOVER_DE > EBOOK_DE` (see §3):

| `book_variant` | Order status | What happens                                                        |
|----------------|--------------|---------------------------------------------------------------------|
| `HARDCOVER`    | `ORDERED`    | Owner email sent; hardcover queued for Lulu; invoice sent after owner review |
| `EBOOK`        | `ORDERED`    | Owner email sent; invoice + download link sent after owner review   |
| `HARDCOVER_DE` | `PRE_ORDER`  | Owner notified; no invoice yet                                      |
| `EBOOK_DE`     | `PRE_ORDER`  | Owner notified; no invoice yet                                      |

The `EBOOK` branch fires whenever the highest-priority live item is a digital
one — including cross-edition carts such as `HARDCOVER_DE + EBOOK`. In that
case the invoice covers the full cart; the German hardcover is delivered when
the edition ships.

The frontend does not need to act on this distinction — it simply renders the
confirmation page returned by the backend.

---

## 3. `line_items` and the `LineItem` schema

`line_items` is an array of one or more `LineItem` objects. The frontend builds
this array using `buildLineItems()` at submit time. Each item represents one
product in the cart:

| Field        | Required | Type   | Notes                                                              |
|--------------|----------|--------|--------------------------------------------------------------------|
| `variant`    | yes      | string | One of `HARDCOVER`, `EBOOK`, `HARDCOVER_DE`, `EBOOK_DE`           |
| `qty`        | yes      | int32  | Quantity ordered (≥ 1)                                             |
| `unit_price` | yes      | double | Unit price in the order currency **after any bundle discount** (see §5) |

**Variant meanings:**

| Variant        | Description                                  | Lulu-fulfilable?              |
|----------------|----------------------------------------------|-------------------------------|
| `HARDCOVER`    | English hardcover (print-on-demand via Lulu) | yes                           |
| `EBOOK`        | English e-book (digital delivery)            | no (digital, backend-fulfilled) |
| `HARDCOVER_DE` | German hardcover pre-order                   | no (manual)                   |
| `EBOOK_DE`     | German e-book pre-order                      | no (manual)                   |

Any value not in this list → 400. Only items with qty ≥ 1 are included; the
array is never empty.

**All cross-edition combinations are accepted.** Routing priority is
`HARDCOVER > EBOOK > HARDCOVER_DE > EBOOK_DE`, array-order-independent.
When a live item is present, the invoice always covers the full cart amount;
any pre-order component is delivered when the edition ships.

| Cart                               | Backend routing key | Confirm status   | Notes                                           |
|------------------------------------|---------------------|------------------|-------------------------------------------------|
| `HARDCOVER` + `EBOOK_DE`           | `HARDCOVER`         | `ORDERED`        | EN ships now; DE e-book sent on release         |
| `HARDCOVER` + `HARDCOVER_DE`       | `HARDCOVER`         | `ORDERED`        | EN ships now; DE ships on release               |
| `EBOOK` + `EBOOK_DE`               | `EBOOK`             | `ORDERED`        | Invoice + download after owner review; DE e-book sent on release  |
| `HARDCOVER_DE` + `EBOOK`           | `EBOOK`             | `ORDERED`        | Invoice + download after owner review; DE hardcover on release    |
| `HARDCOVER` + `EBOOK` + `EBOOK_DE` | `HARDCOVER`         | `ORDERED`        | Full four-item bundle                           |

*"Backend routing key" is derived by the backend from `line_items` using the priority rule above — it is not a field the frontend sends.*

---

## 4. Currency handling

The frontend never asks the backend for exchange rates directly. Instead it
uses the `physical` prices from `/api/prices` as implicit rates:

```js
convertedAmount = amount * PRICES.physical[targetCurrency] / PRICES.physical[sourceCurrency]
```

The currency for a given order is derived from the shipping country:

| Country | Currency |
|---------|----------|
| CH      | CHF      |
| US      | USD      |
| CA      | CAD      |
| AU      | AUD      |
| GB      | GBP      |
| JP      | JPY      |
| all others | EUR  |

`unit_price` in each `LineItem` and `shipping_cost` in the POST body are
expressed in this local currency. The backend should use these values for
invoice generation rather than recomputing prices independently.

---

## 5. Bundle discount

When the cart contains at least one physical book (`HARDCOVER` or
`HARDCOVER_DE`) **and** at least one e-book (`EBOOK` or `EBOOK_DE`), a 20%
discount is applied to the e-book unit price on the frontend:

```
effective_ebook_price = list_ebook_price × 0.80
```

The discounted price is stored directly in `unit_price` for each `EBOOK` /
`EBOOK_DE` line item. The backend does not recompute the discount — it trusts
the `unit_price` values as the customer-quoted amounts, subject to the manual
review step before invoicing.

---

## 6. Shipping options (Lulu)

The frontend fetches shipping options **directly from Lulu** (not via the
backend) for any order that contains a hardcover:

```
POST https://api.lulu.com/shipping-options/
```

This is a direct browser→Lulu call. The backend is not involved. The selected
level and cost are forwarded in the order payload as `shipping_level` and
`shipping_cost`. `HARDCOVER_DE` and `EBOOK_DE` pre-orders have no Lulu product yet;
shipping for those is confirmed by the owner at dispatch.

---

## 7. Payment flow

The frontend classifies countries as SEPA or non-SEPA:

**SEPA** (`AD AT BE BG HR CY CZ DK EE FI FR DE GR HU IS IE IT LV LI LT LU MT
MC NL NO PL PT RO SM SK SI ES SE CH GB`):
- Customer shown: "You will receive an invoice — pay within 30 days by bank transfer."
- Backend sends IBAN payment instructions by email.

**Non-SEPA** (all others):
- Customer shown: "You will receive a Wise payment request by email after confirmation."
- Backend sends a Wise Business payment request by email. Credit card is not offered.

GB is SEPA for this purpose.

---

## 8. CAPTCHA

Both the order form and the subscribe form use an Altcha proof-of-work widget.
The frontend captures the solved payload inside the `statechange` event
listener and stores it in a `storedAltcha` variable. It is submitted as the
`altcha` field. The widget is reset (and `storedAltcha` cleared) on any failed
submission so the user must solve it again.

The challenge URL is:

```
{{ SHOP_API_URL }}/api/captcha
```

---

## 9. Honeypot fields

Both `OrderForm` and `SubscribeForm` include a `website` field that is hidden
from real users via CSS (`display:none`). Any non-empty value must be rejected
with 400.

---

## 10. Form validation (frontend-enforced, not a substitute for backend validation)

The submit button is disabled until all of the following are true:

1. At least one item has qty > 0.
2. All `[required]` fields in visible fieldsets are non-empty.
3. The Altcha widget has reached `state === "verified"`.
4. The "I agree" checkbox is checked.

**Address fieldset for ebook-only orders:** The backend validates
`street1`, `city`, `postcode`, and `country` for **all** orders regardless of
variant — the address doubles as a billing address for the invoice QR code.
When the cart contains only `EBOOK` or `EBOOK_DE` items, the frontend relabels
the fieldset legend from "Shipping address" to "Billing address" but the
fieldset stays visible and all address fields remain required. The backend must
still validate all required fields independently.

---

## 11. Known gaps

### Non-SEPA invoice flow not yet implemented

The backend currently sends the same IBAN/QR-bill invoice to all customers.
For non-SEPA countries the invoice should instead contain Wise Business payment
instructions. The SEPA country list is defined in §7.

**Fix needed in backend:** detect non-SEPA country at `GET /api/confirm` and
send a Wise Business payment request email instead of the standard invoice.

---

## 12. Pelican build variables

These Jinja2 variables are available to templates at build time:

| Variable                | Default                              | Used in              |
|-------------------------|--------------------------------------|----------------------|
| `SHOP_API_URL`          | `https://order.skitraverse.com`      | API calls            |
| `LULU_POD_PACKAGE_ID_EU`| `0850X1100.FC.STD.CW.080CW444.MXX`  | Lulu shipping query  |
| `BOOK_PAGE_COUNT`       | `200`                                | Lulu shipping query  |
