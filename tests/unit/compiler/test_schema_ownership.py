from __future__ import annotations

import ast
import importlib
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src" / "snowiki"

SCHEMA_SYMBOLS_BY_MODULE = {
    "snowiki.schema.compiled": (
        "PageType",
        "PageSection",
        "CompiledPage",
    ),
    "snowiki.schema.normalized": ("NormalizedRecord",),
    "snowiki.schema.projection": (
        "ProjectionSection",
        "SourceIdentity",
        "CompilerProjection",
    ),
}

MOVED_SCHEMA_SYMBOLS_BY_LEGACY_MODULE = {
    "snowiki.compiler.taxonomy": frozenset(
        {
            "PageType",
            "PageSection",
            "CompiledPage",
            "NormalizedRecord",
        }
    ),
    "snowiki.compiler.projection": frozenset(
        {
            "ProjectionSection",
            "SourceIdentity",
            "CompilerProjection",
        }
    ),
}

SCAN_EXCLUSIONS = {
    SRC_ROOT / "compiler" / "taxonomy.py",
    SRC_ROOT / "compiler" / "projection.py",
}


def test_canonical_schema_symbols_live_in_schema_modules() -> None:
    for module_name, symbol_names in SCHEMA_SYMBOLS_BY_MODULE.items():
        module = importlib.import_module(module_name)

        for symbol_name in symbol_names:
            symbol = cast(object, getattr(module, symbol_name))
            symbol_module = cast(str, getattr(symbol, "__module__", ""))

            assert symbol_module.startswith("snowiki.schema."), (
                f"{module_name}.{symbol_name} is owned by {symbol_module!r}"
            )


def test_schema_compiled_and_normalized_do_not_load_compiler_modules() -> None:
    _drop_modules("snowiki.compiler")
    _drop_modules("snowiki.schema.compiled")
    _drop_modules("snowiki.schema.normalized")

    _ = importlib.import_module("snowiki.schema.compiled")
    _ = importlib.import_module("snowiki.schema.normalized")

    loaded_compiler_modules = sorted(
        module_name
        for module_name in sys.modules
        if module_name == "snowiki.compiler" or module_name.startswith("snowiki.compiler.")
    )
    assert loaded_compiler_modules == []


def test_production_modules_do_not_import_moved_schema_symbols_from_compiler() -> None:
    forbidden_imports = [
        forbidden_import
        for source_path in sorted(SRC_ROOT.rglob("*.py"))
        if source_path not in SCAN_EXCLUSIONS
        for forbidden_import in _forbidden_schema_imports(source_path)
    ]

    assert forbidden_imports == []


def _drop_modules(prefix: str) -> None:
    for module_name in list(sys.modules):
        if module_name == prefix or module_name.startswith(f"{prefix}."):
            del sys.modules[module_name]


def _forbidden_schema_imports(source_path: Path) -> Iterator[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module not in MOVED_SCHEMA_SYMBOLS_BY_LEGACY_MODULE:
            continue

        moved_symbols = MOVED_SCHEMA_SYMBOLS_BY_LEGACY_MODULE[node.module]
        imported_names = {alias.name for alias in node.names}
        forbidden_names = imported_names & moved_symbols
        if "*" in imported_names:
            forbidden_names = moved_symbols
        if not forbidden_names:
            continue

        relative_path = source_path.relative_to(REPO_ROOT)
        names = ", ".join(sorted(forbidden_names))
        yield f"{relative_path}:{node.lineno}: from {node.module} import {names}"
