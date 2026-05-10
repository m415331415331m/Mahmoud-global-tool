"""
plugins/__init__.py
────────────────────
Simple plugin loader system.
Plugins are Python files placed in the plugins/ directory.
Each plugin must define:
    PLUGIN_NAME    : str
    PLUGIN_VERSION : str
    def create_tab(runner, get_serial) -> QWidget
"""

import importlib.util
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class PluginMeta:
    def __init__(self, name: str, version: str, module: Any, path: Path):
        self.name    = name
        self.version = version
        self.module  = module
        self.path    = path


def load_plugins(plugin_dir: Path) -> list[PluginMeta]:
    """
    Scan `plugin_dir` for *.py files and attempt to load each as a plugin.
    Returns list of successfully loaded PluginMeta objects.
    """
    plugins: list[PluginMeta] = []

    if not plugin_dir.exists():
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return plugins

    for py_file in plugin_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            spec   = importlib.util.spec_from_file_location(py_file.stem, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            name    = getattr(module, "PLUGIN_NAME",    py_file.stem)
            version = getattr(module, "PLUGIN_VERSION", "0.1")

            if not hasattr(module, "create_tab"):
                log.warning("Plugin %s missing create_tab(); skipped", py_file.name)
                continue

            plugins.append(PluginMeta(name, version, module, py_file))
            log.info("Plugin loaded: %s v%s", name, version)

        except Exception as exc:
            log.error("Failed to load plugin %s: %s", py_file.name, exc)

    return plugins
