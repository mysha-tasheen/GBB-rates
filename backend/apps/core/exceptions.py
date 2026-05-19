"""Pure Python application errors (no Django)."""


class BookingNotFound(Exception):
    """No local booking exists for the given agent and reference."""


class SupplierAPIError(Exception):
    """LiteAPI / Nuitee HTTP error with status and message."""

    def __init__(self, status_code: int, message: str, body: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.body = body or {}
        super().__init__(message)
