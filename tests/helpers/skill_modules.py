from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_skill_script_module(name: str, *, module_prefix: str) -> ModuleType:
    module_path = repo_root() / "skill" / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"{module_prefix}_{name[:-3]}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load skill script module: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
