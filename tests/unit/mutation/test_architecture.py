from __future__ import annotations

import ast
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src" / "snowiki"
MUTATION_ROOT = SRC_ROOT / "mutation"
MUTATION_FINALIZER = MUTATION_ROOT / "finalizer.py"

PRE_MUTATION_FINALIZER = not MUTATION_FINALIZER.exists()
PRE_MUTATION_DOMAIN_REASON = (
    "Phase 6 mutation finalizer has not landed yet; this demolition-map test "
    "documents the legacy bypasses that must disappear during migration."
)

LEGACY_MUTATION_CALLERS = (
    SRC_ROOT / "markdown" / "ingest.py",
    SRC_ROOT / "fileback" / "apply.py",
    SRC_ROOT / "markdown" / "source_prune.py",
)

REBUILD_ORCHESTRATION_MODULES = frozenset({"snowiki.rebuild.integrity"})
CACHE_CLEAR_MODULES = frozenset(
    {
        "snowiki.search.cache",
        "snowiki.search.runtime_retrieval",
    }
)
MANIFEST_MODULES = frozenset({"snowiki.storage.index_manifest"})

CACHE_CLEAR_OWNER_FILES = frozenset(
    {
        SRC_ROOT / "search" / "cache.py",
        SRC_ROOT / "search" / "runtime_retrieval.py",
    }
)
MANIFEST_OWNER_FILES = frozenset({SRC_ROOT / "storage" / "index_manifest.py"})
REBUILD_FINALIZER_FILES = frozenset({MUTATION_FINALIZER})


@pytest.mark.xfail(
    PRE_MUTATION_FINALIZER,
    reason=PRE_MUTATION_DOMAIN_REASON,
    strict=False,
)
def test_mutation_callers_do_not_call_rebuild_integrity_directly() -> None:
    """Demolition checklist: mutation callers must not own rebuild orchestration.

    Phase 6 routes ingest, fileback apply, and source prune through the mutation
    service. Direct calls to `run_rebuild_with_integrity` from those callers are
    forbidden because they preserve the legacy duplicated rebuild/cache/write
    orchestration instead of deleting it.
    """
    forbidden_calls = [
        call_site
        for source_path in LEGACY_MUTATION_CALLERS
        for call_site in _imported_symbol_call_sites(
            source_path,
            modules=REBUILD_ORCHESTRATION_MODULES,
            symbol="run_rebuild_with_integrity",
        )
    ]

    assert forbidden_calls == []


@pytest.mark.xfail(
    PRE_MUTATION_FINALIZER,
    reason=PRE_MUTATION_DOMAIN_REASON,
    strict=False,
)
def test_query_search_cache_is_cleared_only_by_mutation_finalizer() -> None:
    """Demolition checklist: cache invalidation has one mutation finalizer owner.

    Runtime search modules may define/export the cache-clear primitive. Production
    mutation flows must not call it directly outside `snowiki.mutation`, because
    cache invalidation belongs after mutation success and rebuild finalization.
    """
    forbidden_calls = [
        call_site
        for source_path in _production_sources()
        if not _is_cache_clear_allowed_source(source_path)
        for call_site in _imported_symbol_call_sites(
            source_path,
            modules=CACHE_CLEAR_MODULES,
            symbol="clear_query_search_index_cache",
        )
    ]

    assert forbidden_calls == []


@pytest.mark.xfail(
    PRE_MUTATION_FINALIZER,
    reason=PRE_MUTATION_DOMAIN_REASON,
    strict=False,
)
def test_index_manifest_writes_only_happen_in_rebuild_finalizer() -> None:
    """Demolition checklist: manifest writes are finalizer-only.

    The manifest proves compiled/index freshness, so writing it before the
    mutation rebuild finalizer completes can bless a partially updated runtime
    state. Phase 6 requires all `write_index_manifest` calls to flow through the
    rebuild finalizer rather than scattered legacy rebuild helpers.
    """
    forbidden_calls = [
        call_site
        for source_path in _production_sources()
        if source_path not in MANIFEST_OWNER_FILES | REBUILD_FINALIZER_FILES
        for call_site in _imported_symbol_call_sites(
            source_path,
            modules=MANIFEST_MODULES,
            symbol="write_index_manifest",
        )
    ]

    assert forbidden_calls == []


def test_queue_apply_cleans_pending_proposal_after_mutation_success() -> None:
    """Demolition checklist: queue cleanup must be after successful mutation.

    `fileback queue apply` must fail closed. The pending proposal may be deleted
    only after the apply/mutation result has been produced; deleting it before
    success would lose the reviewed write if raw, normalized, rebuild, cache, or
    manifest finalization fails.
    """
    lifecycle_path = SRC_ROOT / "fileback" / "queue" / "lifecycle.py"
    function = _function_definition(lifecycle_path, "apply_queued_fileback_proposal")
    cleanup_lines = tuple(_unlink_call_lines(function, receiver_names={"source_path"}))
    success_lines = tuple(
        _mutation_success_assignment_lines(
            function,
            result_names={"apply_result", "mutation_result"},
        )
    )

    assert success_lines, (
        "apply_queued_fileback_proposal must bind apply_result or mutation_result "
        "before deleting the pending queue proposal"
    )
    assert cleanup_lines, "apply_queued_fileback_proposal must delete pending proposal"
    assert min(cleanup_lines) > max(success_lines), (
        "pending proposal cleanup must happen after mutation/apply success; "
        f"cleanup lines={cleanup_lines}, success lines={success_lines}"
    )


def _production_sources() -> Iterator[Path]:
    yield from sorted(SRC_ROOT.rglob("*.py"))


def _is_cache_clear_allowed_source(source_path: Path) -> bool:
    return source_path in CACHE_CLEAR_OWNER_FILES or _is_under(source_path, MUTATION_ROOT)


def _is_under(path: Path, parent: Path) -> bool:
    try:
        _ = path.relative_to(parent)
    except ValueError:
        return False
    return True


def _parse_source(source_path: Path) -> ast.Module:
    return ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))


def _imported_symbol_call_sites(
    source_path: Path,
    *,
    modules: frozenset[str],
    symbol: str,
) -> Iterator[str]:
    tree = _parse_source(source_path)
    imported_call_names = _imported_symbol_names(tree, modules=modules, symbol=symbol)
    imported_module_names = _imported_module_names(tree, modules=modules)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _calls_imported_symbol(
            node.func,
            symbol=symbol,
            imported_call_names=imported_call_names,
            imported_module_names=imported_module_names,
        ):
            yield _format_call_site(source_path, node)


def _imported_symbol_names(
    tree: ast.Module,
    *,
    modules: frozenset[str],
    symbol: str,
) -> frozenset[str]:
    names: set[str] = {symbol}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module not in modules:
            continue
        imported_names = {alias.name for alias in node.names}
        if "*" in imported_names:
            names.add(symbol)
            continue
        for alias in node.names:
            if alias.name == symbol:
                names.add(alias.asname or alias.name)
    return frozenset(names)


def _imported_module_names(
    tree: ast.Module,
    *,
    modules: frozenset[str],
) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    names.add(alias.asname or alias.name)
                    names.add(alias.asname or alias.name.rsplit(".", maxsplit=1)[-1])
            continue
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        for alias in node.names:
            imported_module = f"{node.module}.{alias.name}"
            if imported_module in modules:
                names.add(alias.asname or alias.name)
    return frozenset(names)


def _calls_imported_symbol(
    func: ast.expr,
    *,
    symbol: str,
    imported_call_names: frozenset[str],
    imported_module_names: frozenset[str],
) -> bool:
    if isinstance(func, ast.Name):
        return func.id in imported_call_names
    if not isinstance(func, ast.Attribute) or func.attr != symbol:
        return False
    receiver_name = _dotted_name(func.value)
    return receiver_name in imported_module_names


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        if prefix is None:
            return None
        return f"{prefix}.{node.attr}"
    return None


def _format_call_site(source_path: Path, call: ast.Call) -> str:
    relative_path = source_path.relative_to(REPO_ROOT)
    return f"{relative_path}:{call.lineno}: {ast.unparse(call.func)}"


def _function_definition(source_path: Path, name: str) -> ast.FunctionDef:
    tree = _parse_source(source_path)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{source_path.relative_to(REPO_ROOT)} does not define {name}")


def _unlink_call_lines(
    function: ast.FunctionDef,
    *,
    receiver_names: Iterable[str],
) -> Iterator[int]:
    allowed_receivers = frozenset(receiver_names)
    for call in _calls(function):
        if not isinstance(call.func, ast.Attribute) or call.func.attr != "unlink":
            continue
        receiver_name = _dotted_name(call.func.value)
        if receiver_name in allowed_receivers:
            yield call.lineno


def _mutation_success_assignment_lines(
    function: ast.FunctionDef,
    *,
    result_names: Iterable[str],
) -> Iterator[int]:
    allowed_result_names = frozenset(result_names)
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        if not _assigns_any_name(node.targets, allowed_result_names):
            continue
        if any(_is_queue_completion_call(call) for call in _calls(node)):
            continue
        yield node.lineno


def _assigns_any_name(targets: Sequence[ast.expr], names: frozenset[str]) -> bool:
    for target in targets:
        if isinstance(target, ast.Name) and target.id in names:
            return True
    return False


def _is_queue_completion_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id == "_queue_completion_result"


def _calls(node: ast.AST) -> Iterator[ast.Call]:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            yield child
