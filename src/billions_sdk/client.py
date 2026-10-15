"""Synchronous Billions public API client."""

from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Any, cast
from urllib.parse import quote

import httpx

from ._shared import (
    decode_response_body,
    extract_error_message,
    normalize_base_url,
    normalize_version,
    resolve_callback_arguments,
    resolve_webhook_invoice_id,
    verify_callback_against_invoice,
)
from .constants import BILLIONS_DEFAULT_BASE_URL, BILLIONS_PUBLIC_API_VERSION
from .errors import BillionsApiError
from .types import (
    CountryInfo,
    CreateInvoiceRequest,
    CurrencyInfo,
    EstimateInvoiceFeesRequest,
    EstimateInvoiceFeesResponseWithSummary,
    InvoiceInfo,
    InvoiceWebhookPayload,
    MerchantInfo,
    VerifyInvoicePaidCallbackData,
)


class BillionsApi:
    """Synchronous client for the Billions public API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        version: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 20.0,
    ) -> None:
        normalized_api_key = str(api_key).strip()
        if not normalized_api_key:
            raise ValueError("api_key is required")

        self.api_key = normalized_api_key
        self.base_url = normalize_base_url(base_url, BILLIONS_DEFAULT_BASE_URL)
        self.version = normalize_version(version, BILLIONS_PUBLIC_API_VERSION)
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def __enter__(self) -> BillionsApi:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the internally-created HTTP client."""
        if self._owns_client:
            self._client.close()

    def get_version(self) -> str:
        return cast(str, self._request("GET", "/version"))

    def get_currencies(self) -> list[CurrencyInfo]:
        return cast(list[CurrencyInfo], self._request("GET", "/currencies"))

    def get_countries(self) -> list[CountryInfo]:
        return cast(list[CountryInfo], self._request("GET", "/countries"))

    def get_merchant_info(self) -> MerchantInfo:
        return cast(MerchantInfo, self._request("GET", "/me"))

    def estimate_fees(
        self,
        payload: EstimateInvoiceFeesRequest,
    ) -> EstimateInvoiceFeesResponseWithSummary:
        return cast(
            EstimateInvoiceFeesResponseWithSummary,
            self._request("POST", "/invoices/estimateFees", payload),
        )

    def create_invoice(self, payload: CreateInvoiceRequest) -> InvoiceInfo:
        return cast(
            InvoiceInfo,
            self._request("POST", "/invoices/create", payload),
        )

    def get_invoice(self, invoice_id: str) -> InvoiceInfo:
        normalized_id = str(invoice_id).strip()
        if not normalized_id:
            raise ValueError("invoice_id is required")
        return cast(
            InvoiceInfo,
            self._request("GET", f"/invoices/{quote(normalized_id, safe='')}"),
        )

    def get_invoices_by_order_no(self, order_no: str) -> list[InvoiceInfo]:
        normalized_order_no = str(order_no).strip()
        if not normalized_order_no:
            raise ValueError("order_no is required")
        encoded = quote(normalized_order_no, safe="")
        return cast(
            list[InvoiceInfo],
            self._request("GET", f"/invoices/byOrder/{encoded}"),
        )

    def verify_invoice_paid(
        self,
        invoice_id_or_callback: str | VerifyInvoicePaidCallbackData | InvoiceWebhookPayload,
        callback_data: VerifyInvoicePaidCallbackData | None = None,
    ) -> InvoiceInfo:
        invoice_id, callback = resolve_callback_arguments(
            invoice_id_or_callback,
            callback_data,
        )
        invoice = self.get_invoice(invoice_id)
        return verify_callback_against_invoice(invoice, callback)

    def get_invoice_from_webhook(
        self,
        webhook: InvoiceWebhookPayload | VerifyInvoicePaidCallbackData,
    ) -> InvoiceInfo:
        """Retrieve authoritative invoice state for any webhook status."""
        invoice_id = resolve_webhook_invoice_id(webhook)
        if not invoice_id:
            raise ValueError("invoice id is required")
        return self.get_invoice(invoice_id)

    @property
    def _api_base_url(self) -> str:
        return f"{self.base_url}/public/{self.version}"

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                f"{self._api_base_url}{path}",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                },
                json=dict(payload) if payload is not None else None,
            )
        except httpx.HTTPError as exc:
            raise BillionsApiError(str(exc), 0, None) from exc

        response_body = decode_response_body(response.text)
        if not response.is_success:
            message = extract_error_message(response_body) or (
                f"Billions API request failed with status {response.status_code}"
            )
            raise BillionsApiError(message, response.status_code, response_body)
        return response_body
