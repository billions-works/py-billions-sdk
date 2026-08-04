"""Internal helpers shared by synchronous and asynchronous clients."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, cast

from .errors import CallbackVerificationError, InvoiceNotPaidError
from .types import InvoiceInfo, InvoiceWebhookPayload, VerifyInvoicePaidCallbackData

_DECIMAL_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?$")


def normalize_base_url(value: str | None, default: str) -> str:
    raw = (value or default).strip()
    return raw.rstrip("/")


def normalize_version(value: str | None, default: str) -> str:
    return (value or default).strip() or default


def decode_response_body(value: str) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def extract_error_message(payload: Any) -> str | None:
    if isinstance(payload, Mapping):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message
    return None


def normalize_decimal_string(value: Any) -> str:
    raw = str(value).strip()
    if not raw:
        return "0"
    if not _DECIMAL_PATTERN.fullmatch(raw):
        return raw

    negative = raw.startswith("-")
    unsigned = raw[1:] if negative else raw
    integer_part, _, fraction_part = unsigned.partition(".")
    integer_part = integer_part.lstrip("0") or "0"
    fraction_part = fraction_part.rstrip("0")
    normalized = (
        f"{integer_part}.{fraction_part}" if fraction_part else integer_part
    )
    return f"-{normalized}" if negative and normalized != "0" else normalized


def resolve_callback_arguments(
    invoice_id_or_callback: str | VerifyInvoicePaidCallbackData | InvoiceWebhookPayload,
    callback_data: VerifyInvoicePaidCallbackData | None,
) -> tuple[str, VerifyInvoicePaidCallbackData]:
    if isinstance(invoice_id_or_callback, str):
        invoice_id = invoice_id_or_callback.strip()
        callback = callback_data
    else:
        invoice_id = resolve_webhook_invoice_id(invoice_id_or_callback)
        event_data = invoice_id_or_callback.get("data")
        callback = cast(
            VerifyInvoicePaidCallbackData,
            event_data if isinstance(event_data, Mapping) else invoice_id_or_callback,
        )

    if not invoice_id:
        raise ValueError("invoice id is required")
    if callback is None:
        raise ValueError("callback data is required")
    return invoice_id, callback


def resolve_webhook_invoice_id(
    callback: VerifyInvoicePaidCallbackData | InvoiceWebhookPayload,
) -> str:
    event_data = callback.get("data")
    if isinstance(event_data, Mapping):
        invoice_id = str(event_data.get("invoice_id", "")).strip()
        if invoice_id:
            return invoice_id

    invoice_id = str(callback.get("invoice_id", "")).strip()
    if invoice_id:
        return invoice_id

    return str(callback.get("id", "")).strip()


def verify_callback_against_invoice(
    invoice: InvoiceInfo,
    callback: VerifyInvoicePaidCallbackData,
) -> InvoiceInfo:
    if invoice["status"] != "completed":
        raise InvoiceNotPaidError()

    if str(callback.get("status", "")).strip() != str(invoice["status"]).strip():
        raise CallbackVerificationError(
            "Callback status does not match API invoice status"
        )

    callback_amount = callback.get(
        "paid_amount",
        "__missing_callback_paid_amount__",
    )
    if normalize_decimal_string(callback_amount) != normalize_decimal_string(
        invoice["paid_amount"]
    ):
        raise CallbackVerificationError(
            "Callback paid_amount does not match API invoice paid_amount"
        )

    return invoice
