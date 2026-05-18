"""Lazy service proxies — avoid DB/API wiring at import time."""


class LazyService:
    """Instantiate the target factory on first attribute access."""

    def __init__(self, factory):
        self._factory = factory
        self._instance = None

    def _get(self):
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def __getattr__(self, name):
        return getattr(self._get(), name)
