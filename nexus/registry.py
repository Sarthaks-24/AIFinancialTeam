from __future__ import annotations

import logging
from typing import Type

from nexus.specialist import BaseSpecialist

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, BaseSpecialist] = {}
_ALIAS_TO_NAME: dict[str, str] = {}


def register_specialist(cls: Type[BaseSpecialist] | None = None, **kwargs):
    """Class decorator: @register_specialist or @register_specialist(name=...)."""

    def decorator(specialist_cls: Type[BaseSpecialist]) -> Type[BaseSpecialist]:
        instance = specialist_cls()
        if kwargs.get("name"):
            instance.name = kwargs["name"]
        if kwargs.get("domain"):
            instance.domain = kwargs["domain"]

        name = instance.name
        if name in _REGISTRY:
            logger.warning("Replacing registered specialist: %s", name)

        _REGISTRY[name] = instance
        _ALIAS_TO_NAME[name.lower()] = name
        for alias in getattr(instance, "aliases", []) or []:
            _ALIAS_TO_NAME[alias.lower()] = name

        logger.info("Registered specialist: %s (domain=%s)", name, instance.domain)
        return specialist_cls

    if cls is not None:
        return decorator(cls)
    return decorator


def get_specialist(name: str) -> BaseSpecialist | None:
    if not name:
        return None
    canonical = _ALIAS_TO_NAME.get(name.lower())
    if not canonical:
        return None
    return _REGISTRY.get(canonical)


def list_specialists() -> list[BaseSpecialist]:
    return sorted(_REGISTRY.values(), key=lambda specialist: specialist.name)


def resolve_name(name: str) -> str | None:
    if not name:
        return None
    return _ALIAS_TO_NAME.get(name.lower())
