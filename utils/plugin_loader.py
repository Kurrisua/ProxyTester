from __future__ import annotations

import importlib
import inspect
import pkgutil


def load_plugins(package: str, base_class: type) -> list:
    module = importlib.import_module(package)
    plugins = []
    for _, module_name, _ in pkgutil.iter_modules(module.__path__):
        loaded = importlib.import_module(f"{package}.{module_name}")
        for _, obj in inspect.getmembers(loaded, inspect.isclass):
            if issubclass(obj, base_class) and obj is not base_class:
                plugins.append(obj())
    return plugins
