from __future__ import annotations

from core.interfaces.checker_base import BaseSecurityChecker
from security.policy import validate_security_checker
from utils.plugin_loader import load_plugins


def build_default_security_checkers() -> list[BaseSecurityChecker]:
    checkers = load_plugins("security.plugins", BaseSecurityChecker)
    names = set()
    errors = []
    for checker in checkers:
        if checker.name in names:
            errors.append(f"duplicate security checker name: {checker.name}")
        names.add(checker.name)
        errors.extend(validate_security_checker(checker))
    if errors:
        raise ValueError("Invalid security checker contract: " + "; ".join(errors))
    return sorted(checkers, key=lambda item: item.order)
