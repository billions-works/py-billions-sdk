"""Exceptions raised by the Billions SDK."""

from typing import Any


class BillionsSdkError(Exception):
    """Base exception for all SDK-specific errors."""


class BillionsApiError(BillionsSdkError):
    """A failed HTTP response or transport error from the Billions API."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response_body: Any,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class InvoiceNotPaidError(BillionsSdkError):
    """The authoritative invoice status is not completed."""

    def __init__(self, message: str = "Invoice is not paid yet") -> None:
        super().__init__(message)


class CallbackVerificationError(BillionsSdkError):
    """Callback data does not match the authoritative API invoice."""

    def __init__(
        self,
        message: str = "Callback data does not match invoice data from API",
    ) -> None:
        super().__init__(message)

