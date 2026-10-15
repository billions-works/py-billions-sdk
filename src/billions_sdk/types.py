"""Typed request and response dictionaries for the Billions public API."""

from __future__ import annotations

from typing import Literal, TypedDict

CurrencyType = Literal["stablecoin", "fiat", "token"]
InvoiceType = Literal["b2b", "b2c"]
InvoiceStatus = Literal[
    "pending",
    "processing",
    "completed",
    "refund_processing",
    "failed",
    "expired",
    "refunded",
    "aml_check",
    "aml_block",
]
Amount = int | float | str
InvoiceWebhookEvent = Literal["invoice.paid", "invoice.status_changed"]


class CurrencyInfo(TypedDict):
    ticker: str
    fullName: str
    network: str
    contractAddress: str | None
    type: CurrencyType
    icon: str
    iconDark: str
    internalTicker: str


class CountryInfo(TypedDict):
    code: str
    name: str


class MerchantInfo(TypedDict):
    id: str
    email: str
    merchantName: str | None
    directorName: str | None
    website: str | None
    logo: str | None
    whitelabeling: bool


class _EstimateInvoiceFeesRequired(TypedDict):
    currency: str
    amount: Amount


class EstimateInvoiceFeesRequest(_EstimateInvoiceFeesRequired, total=False):
    type: InvoiceType
    order_no: str
    description: str
    autoconvert: str


class EstimateInvoiceFeesResponse(TypedDict):
    amount: int | float
    finalPrice: int | float
    fee: int | float
    merchantReceiveAmount: int | float


class EstimateInvoiceFeesResponseWithSummary(EstimateInvoiceFeesResponse, total=False):
    summaryFee: int | float


class CreateInvoiceRequest(EstimateInvoiceFeesRequest, total=False):
    idempotencyKey: str
    callbackUrl: str
    expiresAt: str


class InvoiceInfo(TypedDict):
    created_at: str
    updated_at: str
    expires_at: str | None
    invoice_url: str
    id: str
    type: InvoiceType
    status: InvoiceStatus
    merchant_id: str
    settlement_currency: str | None
    currency: str | None
    convert_currency: str | None
    amount: str
    final_amount: str
    merchant_fee: str
    network_and_other_fees: str
    merchant_receive_amount: str
    paid_amount: str
    callback_url: str | None
    order_no: str | None
    description: str | None


class _VerifyInvoicePaidCallbackRequired(TypedDict):
    status: str
    paid_amount: Amount


class VerifyInvoicePaidCallbackData(_VerifyInvoicePaidCallbackRequired, total=False):
    id: str
    invoice_id: str
    data: InvoiceWebhookData


class InvoiceWebhookData(TypedDict):
    invoice_id: str
    external_invoice_id: str | None
    order_no: str | None
    previous_status: InvoiceStatus
    status: InvoiceStatus
    amount: str
    final_amount: str
    paid_amount: str
    merchant_fee: str
    network_and_other_fees: str
    merchant_receive_amount: str
    currency: str | None
    settlement_currency: str | None
    payment_source: str | None
    payment_address: str | None
    updated_at: str


class _InvoiceWebhookPayloadRequired(TypedDict):
    event: InvoiceWebhookEvent
    event_timestamp: str
    attempt: int
    previous_attempt_timestamp: str | None
    data: InvoiceWebhookData


class InvoiceWebhookPayload(_InvoiceWebhookPayloadRequired, total=False):
    """Outgoing invoice webhook envelope.

    Event fields are duplicated at the top level for compatibility. New
    integrations should read them from ``data``.
    """

    invoice_id: str
    external_invoice_id: str | None
    order_no: str | None
    previous_status: InvoiceStatus
    status: InvoiceStatus
    amount: str
    final_amount: str
    paid_amount: str
    merchant_fee: str
    network_and_other_fees: str
    merchant_receive_amount: str
    currency: str | None
    settlement_currency: str | None
    payment_source: str | None
    payment_address: str | None
    updated_at: str
