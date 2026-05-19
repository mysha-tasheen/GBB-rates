from typing import Any, Dict, Type
from apps.core.adapters.base import BaseAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, Type[BaseAdapter]] = {}

    def register(self, name: str, adapter_class: Type[BaseAdapter]) -> None:
        self._adapters[name] = adapter_class

    def get_adapter(
        self,
        name: str,
        credentials: Dict[str, Any],
        commission_percent: float,
    ) -> BaseAdapter:
        if name not in self._adapters:
            raise ValueError(f"Unknown supplier adapter: {name}")
        return self._adapters[name](credentials, commission_percent)


registry = AdapterRegistry()
