"""Typed request and response dictionaries for the Billions public API."""

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


class CurrencyInfo(TypedDict):
    ticker: str
    fullName: str
    network: str
    contractAddress: str | None
    type: CurrencyType
    icon: str
    iconDark: str
    internalTicker: str


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
