"""Create a Billions invoice using the synchronous client."""

from __future__ import annotations

import os
import time

from billions_sdk import BillionsApi

api_key = os.environ["BILLIONS_API_KEY"]
reference = f"python-example-{int(time.time())}"

with BillionsApi(api_key) as api:
    invoice = api.create_invoice(
        {
            "currency": "USD",
            "amount": "100.00",
            "type": "b2c",
            "idempotencyKey": reference,
            "order_no": reference,
            "description": "Example invoice from py-billions-sdk",
            "callbackUrl": "https://example.com/webhook",
        }
    )

print(f"Invoice: {invoice['id']}")
print(f"Payment URL: {invoice['invoice_url']}")

