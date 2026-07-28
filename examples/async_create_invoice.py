"""Create a Billions invoice using the asynchronous client."""

from __future__ import annotations

import asyncio
import os
import time

from billions_sdk import AsyncBillionsApi


async def main() -> None:
    api_key = os.environ["BILLIONS_API_KEY"]
    reference = f"python-async-example-{int(time.time())}"

    async with AsyncBillionsApi(api_key) as api:
        invoice = await api.create_invoice(
            {
                "currency": "EUR",
                "amount": "100.00",
                "type": "b2c",
                "idempotencyKey": reference,
                "order_no": reference,
                "description": "Async example from py-billions-sdk",
            }
        )

    print(f"Invoice: {invoice['id']}")
    print(f"Payment URL: {invoice['invoice_url']}")


if __name__ == "__main__":
    asyncio.run(main())

