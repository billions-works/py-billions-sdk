# py-billions-sdk

Official Python SDK for the Billions public API.

## Requirements

- Python 3.10+
- `httpx` 0.27+

## Installation

```bash
pip install py-billions-sdk
```

## Synchronous usage

```python
from billions_sdk import BillionsApi

with BillionsApi("your-api-key", secret_key="your-api-secret-key") as api:
    version = api.get_version()
    currencies = api.get_currencies()
    countries = api.get_countries()
    invoice = api.create_invoice(
        {
            "currency": "USD",
            "amount": "100.00",
            "idempotencyKey": "checkout-attempt-123",
            "order_no": "ORDER-123",
            "callbackUrl": "https://example.com/webhook",
        }
    )

print(invoice["invoice_url"])
```

## Asynchronous usage

```python
from billions_sdk import AsyncBillionsApi

async with AsyncBillionsApi("your-api-key") as api:
    invoice = await api.get_invoice("invoice-id")
```

## Available methods

Both clients expose the same methods:

```python
api.get_version()
api.get_currencies()
api.get_countries()
api.get_merchant_info()
api.estimate_fees(payload)
api.create_invoice(payload)
api.create_withdrawal(payload, request_id=request_id)
api.refund_crypto(payload, request_id=request_id)
api.refund_fiat(payload, request_id=request_id)
api.get_invoice(invoice_id)
api.get_invoices_by_order_no(order_no)
api.get_invoice_from_webhook(webhook)
api.verify_webhook_signature(signature, raw_body)
api.verify_invoice_paid(invoice_id, callback_data)
api.verify_invoice_paid(callback_data_with_id)
```

Methods on `AsyncBillionsApi` are coroutines and must be awaited.

The withdrawal and refund methods sign the method, route, timestamp, request ID,
and RFC 8785/JCS body automatically. Preserve and reuse the same request ID and
body when retrying after a lost response; a new ID can authorize another operation.

The default API host is `https://api.billions.works`, and the default public API
version is `v1`. Both can be overridden in the constructor. A custom `httpx.Client`
or `httpx.AsyncClient` can be injected for transport customization and tests.

## Idempotency and order references

Pass `idempotencyKey` when creating an invoice. Repeating a create request with the
same key returns the invoice associated with that key. Use `order_no` as your business
order reference, then call `get_invoices_by_order_no()` when you need to recover all
invoices for that order.

## Webhooks and callback verification

Billions sends `invoice.status_changed` for intermediate transitions and
`invoice.paid` when an invoice becomes `completed`. Use the canonical `data`
object in the webhook envelope.

Verify the signature using the received JSON body:

```python
if not api.verify_webhook_signature(signature_header, raw_body):
    raise ValueError("Invalid webhook signature")
```

The method parses the body, canonicalizes it according to RFC 8785 (JCS), and
verifies HMAC-SHA256 using `webhook_secret`. It accepts plain hex or
`jcs-sha256=<hex>` and performs a timing-safe comparison. JSON whitespace,
property order, and equivalent escaping do not affect verification. The secret
is the original API `secretKey`, used as UTF-8 text.

Retrieve authoritative state for any webhook status:

```python
invoice = api.get_invoice_from_webhook(webhook)

if invoice["status"] == "processing":
    # Update the visible payment status, but do not fulfill the order.
    ...
```

For a paid event, you can additionally compare the webhook fields with the API
response:

```python
from billions_sdk import CallbackVerificationError, InvoiceNotPaidError

try:
    invoice = api.verify_invoice_paid(
        webhook
    )
except (InvoiceNotPaidError, CallbackVerificationError):
    # Reject or postpone callback processing.
    ...
```

`verify_invoice_paid()` accepts the current webhook envelope and legacy callback
objects. It retrieves the authoritative invoice from the API, requires its status
to be `completed`, and compares the callback status and paid amount.
Decimal forms such as `100`, `100.0`, and `100.000000000000000000` are equivalent.

If the callback should be used only as a wake-up signal, call
`get_invoice_from_webhook()` and base your application state exclusively on that
response.

## Errors

- `BillionsApiError` exposes `status_code` and `response_body`.
- `InvoiceNotPaidError` means the authoritative invoice is not completed.
- `CallbackVerificationError` means callback data differs from API data.

Transport errors use `status_code == 0`.

## Development

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest
python -m build
```
