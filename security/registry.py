from __future__ import annotations

from core.interfaces.checker_base import BaseSecurityChecker
from utils.plugin_loader import load_plugins


def build_default_security_checkers() -> list[BaseSecurityChecker]:
    return sorted(load_plugins("security.plugins", BaseSecurityChecker), key=lambda item: item.order)
