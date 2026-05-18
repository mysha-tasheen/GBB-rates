"""Pure Python application errors (no Django)."""


class BookingNotFound(Exception):
    """No local booking exists for the given agent and reference."""
