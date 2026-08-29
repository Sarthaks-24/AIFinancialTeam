"""Agent-level permission checks for Nexus dispatch."""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser

from nexus.specialist import BaseSpecialist


def user_group_names(user: AbstractBaseUser | None) -> set[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return {"Admin"}
    return set(user.groups.values_list("name", flat=True))


def user_can_access(user: AbstractBaseUser | None, specialist: BaseSpecialist) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False

    groups = user_group_names(user)
    if "Admin" in groups:
        return True

    required = specialist.required_groups or []
    if not required:
        return True

    return any(group in groups for group in required)
