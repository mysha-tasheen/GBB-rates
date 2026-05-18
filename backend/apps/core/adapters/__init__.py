from apps.core.adapters.liteapi import LiteAPIAdapter
from apps.core.adapters.registry import registry

registry.register("liteapi", LiteAPIAdapter)

__all__ = ["LiteAPIAdapter", "registry"]
