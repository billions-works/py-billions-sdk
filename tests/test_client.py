from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from billions_sdk import (
    AsyncBillionsApi,
    BillionsApi,
    BillionsApiError,
    CallbackVerificationError,
    InvoiceNotPaidError,
)
from billions_sdk.types import CreateInvoiceRequest, InvoiceInfo


def invoice(**overrides: Any) -> InvoiceInfo:
    result: InvoiceInfo = {
        "created_at": "2026-07-24T09:50:15.555Z",
        "updated_at": "2026-07-24T09:50:15.555Z",
        "expires_at": None,
        "invoice_url": "https://pay.example.test/invoice-id",
        "id": "invoice-id",
        "type": "b2c",
        "status": "completed",
        "merchant_id": "merchant-id",
        "settlement_currency": "USD",
        "currency": "USD",
        "convert_currency": None,
        "amount": "100.000000000000000000",
        "final_amount": "101.000000000000000000",
        "merchant_fee": "1.000000000000000000",
        "network_and_other_fees": "0.250000000000000000",
        "merchant_receive_amount": "99.000000000000000000",
        "paid_amount": "101.000000000000000000",
        "callback_url": "https://example.com/webhook",
        "order_no": "ORDER-42",
        "description": "Test invoice",
    }
    result.update(overrides)  # type: ignore[typeddict-item]
    return result


def sync_api(
    handler: httpx.MockTransport,
) -> tuple[BillionsApi, httpx.Client]:
    client = httpx.Client(transport=handler)
    return (
        BillionsApi(
            " secret ",
            base_url="https://example.test///",
            client=client,
        ),
        client,
    )


def test_constructor_normalizes_options() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json="v1"))
    api, client = sync_api(transport)
    try:
        assert api.api_key == "secret"
        assert api.base_url == "https://example.test"
        assert api.version == "v1"
    finally:
        client.close()


def test_api_key_is_required() -> None:
    with pytest.raises(ValueError, match="api_key is required"):
        BillionsApi(" ")


def test_verify_webhook_signature() -> None:
    body = b'{"event":"invoice.paid"}'
    signature = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()
    api = BillionsApi("secret", webhook_secret="whsec_test")
    try:
        assert api.verify_webhook_signature(signature, body)
        assert api.verify_webhook_signature(f"sha256={signature.upper()}", body)
        assert not api.verify_webhook_signature("0" * 64, body)
        assert not api.verify_webhook_signature("invalid", body)
    finally:
        api.close()


def test_verify_webhook_signature_requires_secret() -> None:
    api = BillionsApi("secret")
    try:
        with pytest.raises(ValueError, match="webhook_secret is required"):
            api.verify_webhook_signature("0" * 64, b"{}")
    finally:
        api.close()


def test_get_version_uses_expected_url_and_headers() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json="v1")

    api, client = sync_api(httpx.MockTransport(handler))
    try:
        assert api.get_version() == "v1"
    finally:
        client.close()

    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert str(requests[0].url) == "https://example.test/public/v1/version"
    assert requests[0].headers["x-api-key"] == "secret"
    assert requests[0].headers["content-type"] == "application/json"


def test_create_invoice_sends_current_wire_fields() -> None:
    requests: list[httpx.Request] = []
    expected_invoice = invoice()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=expected_invoice)

    api, client = sync_api(httpx.MockTransport(handler))
    payload: CreateInvoiceRequest = {
        "currency": "USD",
        "amount": "100.00",
        "idempotencyKey": "attempt-42",
        "order_no": "ORDER-42",
        "callbackUrl": "https://example.com/webhook",
    }
    try:
        assert api.create_invoice(payload) == expected_invoice
    finally:
        client.close()

    assert requests[0].method == "POST"
    assert str(requests[0].url) == "https://example.test/public/v1/invoices/create"
    assert json.loads(requests[0].content) == payload


def test_get_countries_uses_expected_endpoint() -> None:
    requests: list[httpx.Request] = []
    countries = [{"code": "US", "name": "United States"}]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=countries)

    api, client = sync_api(httpx.MockTransport(handler))
    try:
        assert api.get_countries() == countries
    finally:
        client.close()

    assert str(requests[0].url) == "https://example.test/public/v1/countries"


def test_get_invoice_and_order_lookup_encode_path_values() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body: Any = [] if "/byOrder/" in request.url.path else invoice()
        return httpx.Response(200, json=body)

    api, client = sync_api(httpx.MockTransport(handler))
    try:
        api.get_invoice(" invoice/42 ")
        assert api.get_invoices_by_order_no(" ORDER/42 ") == []
    finally:
        client.close()

    assert str(requests[0].url).endswith("/invoices/invoice%2F42")
    assert str(requests[1].url).endswith("/invoices/byOrder/ORDER%2F42")


@pytest.mark.parametrize(
    ("method_name", "message"),
    [
        ("get_invoice", "invoice_id is required"),
        ("get_invoices_by_order_no", "order_no is required"),
    ],
)
def test_lookup_values_are_required(method_name: str, message: str) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    api, client = sync_api(transport)
    try:
        with pytest.raises(ValueError, match=message):
            getattr(api, method_name)(" ")
    finally:
        client.close()


def test_api_error_exposes_status_and_response_body() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            422,
            json={"message": "Invalid currency", "field": "currency"},
        )
    )
    api, client = sync_api(transport)
    try:
        with pytest.raises(BillionsApiError) as captured:
            api.get_currencies()
    finally:
        client.close()

    assert str(captured.value) == "Invalid currency"
    assert captured.value.status_code == 422
    assert captured.value.response_body == {
        "message": "Invalid currency",
        "field": "currency",
    }


def test_transport_error_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    api, client = sync_api(httpx.MockTransport(handler))
    try:
        with pytest.raises(BillionsApiError) as captured:
            api.get_version()
    finally:
        client.close()

    assert captured.value.status_code == 0
    assert captured.value.response_body is None


def test_verify_invoice_paid_accepts_equivalent_decimal_formats() -> None:
    expected_invoice = invoice()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=expected_invoice)
    )
    api, client = sync_api(transport)
    try:
        result = api.verify_invoice_paid(
            {
                "id": "invoice-id",
                "status": "completed",
                "paid_amount": "0101.000",
            }
        )
    finally:
        client.close()

    assert result == expected_invoice


def test_verify_invoice_paid_accepts_new_webhook_envelope() -> None:
    expected_invoice = invoice()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=expected_invoice)
    )
    api, client = sync_api(transport)
    try:
        result = api.verify_invoice_paid(
            {
                "event": "invoice.paid",
                "event_timestamp": "2026-08-04T09:42:08.189Z",
                "attempt": 1,
                "previous_attempt_timestamp": None,
                "data": {
                    "invoice_id": "invoice-id",
                    "external_invoice_id": "12",
                    "order_no": "ORDER-42",
                    "previous_status": "processing",
                    "status": "completed",
                    "amount": "100.000000000000000000",
                    "final_amount": "101.000000000000000000",
                    "paid_amount": "0101.000",
                    "merchant_fee": "1.000000000000000000",
                    "network_and_other_fees": "0.250000000000000000",
                    "merchant_receive_amount": "99.000000000000000000",
                    "currency": "USD",
                    "settlement_currency": "USD",
                    "payment_source": "internal",
                    "payment_address": None,
                    "updated_at": "2026-08-04T09:42:08.000Z",
                },
            }
        )
    finally:
        client.close()

    assert result == expected_invoice


def test_get_invoice_from_webhook_supports_intermediate_status() -> None:
    expected_invoice = invoice(status="processing", paid_amount="0")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=expected_invoice)
    )
    api, client = sync_api(transport)
    try:
        result = api.get_invoice_from_webhook(
            {
                "event": "invoice.status_changed",
                "event_timestamp": "2026-08-04T09:42:08.189Z",
                "attempt": 1,
                "previous_attempt_timestamp": None,
                "data": {
                    "invoice_id": "invoice-id",
                    "external_invoice_id": "12",
                    "order_no": "ORDER-42",
                    "previous_status": "pending",
                    "status": "processing",
                    "amount": "100.000000000000000000",
                    "final_amount": "101.000000000000000000",
                    "paid_amount": "0",
                    "merchant_fee": "1.000000000000000000",
                    "network_and_other_fees": "0.250000000000000000",
                    "merchant_receive_amount": "99.000000000000000000",
                    "currency": "USD",
                    "settlement_currency": "USD",
                    "payment_source": "internal",
                    "payment_address": None,
                    "updated_at": "2026-08-04T09:42:08.000Z",
                },
            }
        )
    finally:
        client.close()

    assert result["status"] == "processing"


def test_verify_invoice_paid_rejects_unpaid_invoice() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=invoice(status="pending"))
    )
    api, client = sync_api(transport)
    try:
        with pytest.raises(InvoiceNotPaidError):
            api.verify_invoice_paid(
                "invoice-id",
                {"status": "pending", "paid_amount": "0"},
            )
    finally:
        client.close()


def test_verify_invoice_paid_rejects_callback_mismatch() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=invoice())
    )
    api, client = sync_api(transport)
    try:
        with pytest.raises(
            CallbackVerificationError,
            match="paid_amount does not match",
        ):
            api.verify_invoice_paid(
                "invoice-id",
                {"status": "completed", "paid_amount": "99"},
            )
    finally:
        client.close()


@pytest.mark.asyncio
async def test_async_client_matches_sync_api() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/version"):
            return httpx.Response(200, json="v1")
        if request.url.path.endswith("/countries"):
            return httpx.Response(200, json=[{"code": "US", "name": "United States"}])
        return httpx.Response(200, json=[invoice()])

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = AsyncBillionsApi(
        "secret",
        base_url="https://example.test",
        webhook_secret="whsec_test",
        client=http_client,
    )
    try:
        body = b'{"event":"invoice.paid"}'
        signature = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()
        assert api.verify_webhook_signature(signature, body)
        assert await api.get_version() == "v1"
        assert await api.get_countries() == [{"code": "US", "name": "United States"}]
        assert await api.get_invoices_by_order_no("ORDER-42") == [invoice()]
    finally:
        await http_client.aclose()

    assert len(requests) == 3
