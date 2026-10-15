"""Internal helpers shared by synchronous and asynchronous clients."""

from __future__ import annotations

import hmac
import json
import re
import time
import uuid
from collections.abc import Mapping
from hashlib import sha256
from typing import Any, cast

import rfc8785

from .errors import CallbackVerificationError, InvoiceNotPaidError
from .types import InvoiceInfo, InvoiceWebhookPayload, VerifyInvoicePaidCallbackData

_DECIMAL_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?$")


def normalize_base_url(value: str | None, default: str) -> str:
    raw = (value or default).strip()
    return raw.rstrip("/")


def normalize_version(value: str | None, default: str) -> str:
    return (value or default).strip() or default


def verify_webhook_signature(
    secret: str | None,
    signature: str,
    body: str | bytes,
) -> bool:
    if secret is None:
        raise ValueError("webhook_secret is required to verify webhook signatures")

    normalized_signature = str(signature).strip()
    if normalized_signature.lower().startswith("jcs-sha256="):
        normalized_signature = normalized_signature[11:]
    if len(normalized_signature) != 64:
        return False
    try:
        bytes.fromhex(normalized_signature)
    except ValueError:
        return False

    try:
        parsed_body = json.loads(body)
        canonical_body = rfc8785.dumps(parsed_body)
    except (json.JSONDecodeError, rfc8785.CanonicalizationError, UnicodeDecodeError):
        return False
    expected_signature = hmac.new(secret.encode("utf-8"), canonical_body, sha256).hexdigest()
    return hmac.compare_digest(expected_signature, normalized_signature.lower())


def signed_mutation_headers(
    secret: str | None,
    version: str,
    path: str,
    payload: Mapping[str, Any],
    request_id: str | None,
    timestamp: int | str | None,
) -> dict[str, str]:
    if secret is None:
        raise ValueError("secret_key is required for signed operations")
    normalized_timestamp = str(timestamp if timestamp is not None else int(time.time()))
    normalized_request_id = str(request_id or uuid.uuid4()).strip().lower()
    canonical_body = rfc8785.dumps(dict(payload)).decode("utf-8")
    message = (
        f"POST\n/public/{version}{path}\n{normalized_timestamp}\n"
        f"{normalized_request_id}\n{canonical_body}"
    )
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), sha256).hexdigest()
    return {
        "x-billions-timestamp": normalized_timestamp,
        "x-billions-request-id": normalized_request_id,
        "x-billions-request-signature": f"v1={signature}",
    }


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
    normalized = f"{integer_part}.{fraction_part}" if fraction_part else integer_part
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
        raise CallbackVerificationError("Callback status does not match API invoice status")

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
