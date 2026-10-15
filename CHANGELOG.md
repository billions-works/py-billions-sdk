# Changelog

## 0.5.0

- Added signed withdrawal, crypto refund, and fiat refund operations.
- Added typed operation payloads and responses with reusable request IDs.

## 0.4.1

- Aligned webhook verification with the backend's RFC 8785 JCS signature contract.

## 0.4.0

- Added optional webhook secrets to synchronous and asynchronous clients.
- Added timing-safe HMAC-SHA256 webhook signature verification.

## 0.3.0

- Added the public country directory to synchronous and asynchronous clients.
- Added `network_and_other_fees` to invoice and webhook types.

## 0.2.0

- Typed outgoing webhook envelope and invoice event data.
- Support for `invoice.paid` and intermediate `invoice.status_changed` events.
- Added `get_invoice_from_webhook()` to retrieve authoritative state for any status.
- Updated `verify_invoice_paid()` to accept the new webhook envelope and legacy callbacks.

## 0.1.0

- Initial synchronous and asynchronous clients.
- Current Public API invoice and fee fields.
- Invoice creation idempotency.
- Invoice lookup by `order_no`.
- Authoritative callback verification helpers.
- PEP 561 type information.
