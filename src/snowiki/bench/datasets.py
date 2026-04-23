from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from snowiki.config import resolve_repo_asset_path

from .specs import DatasetManifest, DatasetSourceLocator, EvaluationMatrix, LevelConfig


def load_matrix(path: str | Path) -> EvaluationMatrix:
    """Load an evaluation matrix from a YAML contract file."""

    source_path = Path(path)
    payload = _load_yaml_mapping(source_path)
    levels_payload = _require_mapping(payload, "levels", source_path)
    levels = {
        level_id: LevelConfig(
            level_id=level_id,
            query_cap=_require_int(level_payload, "query_cap", source_path),
            note=_optional_str(level_payload, "note", source_path),
        )
        for level_id, level_payload in _iter_named_mappings(levels_payload, source_path)
    }
    return EvaluationMatrix(
        matrix_id=_require_str(payload, "matrix_id", source_path),
        datasets=tuple(_require_str_list(payload, "datasets", source_path)),
        levels=levels,
    )


def load_dataset_manifest(path: str | Path) -> DatasetManifest:
    """Load one dataset manifest from a YAML contract file."""

    source_path = Path(path)
    payload = _load_yaml_mapping(source_path)
    source_locators = _load_dataset_sources(payload, source_path)
    field_mapping_payload = _require_mapping(payload, "field_mappings", source_path)
    field_mappings = {
        field_name: tuple(_require_sequence_of_str(field_value, field_name, source_path))
        for field_name, field_value in _iter_mapping_items(field_mapping_payload, source_path)
    }
    return DatasetManifest(
        dataset_id=_require_str(payload, "dataset_id", source_path),
        name=_require_str(payload, "name", source_path),
        language=_require_str(payload, "language", source_path),
        purpose_tags=tuple(_require_str_list(payload, "purpose_tags", source_path)),
        corpus_path=_require_str(payload, "corpus_path", source_path),
        queries_path=_require_str(payload, "queries_path", source_path),
        judgments_path=_require_str(payload, "judgments_path", source_path),
        source=source_locators,
        field_mappings=field_mappings,
        supported_levels=tuple(_require_str_list(payload, "supported_levels", source_path)),
    )


def resolve_dataset_assets(manifest: DatasetManifest) -> dict[str, Path]:
    """Resolve repo-owned dataset asset paths from a manifest."""

    return {
        "corpus": _resolve_manifest_path(manifest.corpus_path),
        "queries": _resolve_manifest_path(manifest.queries_path),
        "judgments": _resolve_manifest_path(manifest.judgments_path),
    }


def missing_materialized_asset_message(
    manifest: DatasetManifest,
    *,
    asset_name: str,
    path: Path,
) -> str:
    guidance = f"run snowiki benchmark-fetch --dataset {manifest.dataset_id}"
    return f"Missing {asset_name} file: {path} ({guidance})"


def _resolve_manifest_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return resolve_repo_asset_path(path)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = _load_yaml_document(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping at {path}, got {type(payload).__name__}")
    return {str(key): value for key, value in payload.items()}


def _load_yaml_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return _parse_minimal_yaml(text)
    return yaml.safe_load(text)


@dataclass(frozen=True)
class _YamlLine:
    indent: int
    text: str


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    lines = _tokenize_yaml(text)
    if not lines:
        return {}
    parsed, index = _parse_mapping(lines, 0, lines[0].indent)
    if index != len(lines):
        raise ValueError("Could not parse the full YAML document.")
    return parsed


def _tokenize_yaml(text: str) -> list[_YamlLine]:
    lines: list[_YamlLine] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append(_YamlLine(indent=indent, text=stripped))
    return lines


def _parse_mapping(
    lines: list[_YamlLine],
    index: int,
    indent: int,
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent != indent:
            raise ValueError(f"Unexpected indentation for YAML mapping: {line.text}")
        if line.text.startswith("- ") or ":" not in line.text:
            raise ValueError(f"Expected YAML mapping entry, got: {line.text}")
        key, raw_value = line.text.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        index += 1
        if value:
            result[key] = _parse_scalar(value)
            continue
        if index >= len(lines) or lines[index].indent <= indent:
            result[key] = {}
            continue
        next_line = lines[index]
        if next_line.text.startswith("- "):
            list_value, index = _parse_list(lines, index, next_line.indent)
            result[key] = list_value
            continue
        nested_mapping, index = _parse_mapping(lines, index, next_line.indent)
        result[key] = nested_mapping
    return result, index


def _parse_list(
    lines: list[_YamlLine],
    index: int,
    indent: int,
) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        line = lines[index]
        if line.indent < indent or line.indent != indent or not line.text.startswith("- "):
            break
        value = line.text[2:].strip()
        index += 1
        if value:
            result.append(_parse_scalar(value))
            continue
        if index >= len(lines) or lines[index].indent <= indent:
            result.append(None)
            continue
        next_line = lines[index]
        if next_line.text.startswith("- "):
            nested_list, index = _parse_list(lines, index, next_line.indent)
            result.append(nested_list)
            continue
        nested_mapping, index = _parse_mapping(lines, index, next_line.indent)
        result.append(nested_mapping)
    return result, index


def _parse_scalar(value: str) -> Any:
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


def _iter_named_mappings(
    payload: dict[str, Any],
    source_path: Path,
) -> list[tuple[str, dict[str, Any]]]:
    named_mappings: list[tuple[str, dict[str, Any]]] = []
    for key, value in payload.items():
        if not isinstance(value, dict):
            raise ValueError(
                f"Expected mapping for {key!r} in {source_path}, got {type(value).__name__}"
            )
        named_mappings.append((str(key), {str(item_key): item_value for item_key, item_value in value.items()}))
    return named_mappings


def _iter_mapping_items(
    payload: dict[str, Any],
    source_path: Path,
) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    for key, value in payload.items():
        if not isinstance(key, str):
            raise ValueError(f"Expected string mapping key in {source_path}, got {key!r}")
        items.append((key, value))
    return items


def _require_mapping(payload: dict[str, Any], key: str, source_path: Path) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {key!r} in {source_path}")
    return {str(item_key): item_value for item_key, item_value in value.items()}


def _load_dataset_sources(
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, DatasetSourceLocator]:
    source_payload = _require_mapping(payload, "source", source_path)
    required_keys = ("corpus", "queries", "judgments")
    return {
        source_key: _load_dataset_source_locator(source_payload, source_key, source_path)
        for source_key in required_keys
    }


def _load_dataset_source_locator(
    source_payload: dict[str, Any],
    key: str,
    source_path: Path,
) -> DatasetSourceLocator:
    locator_payload = _require_mapping(source_payload, key, source_path)
    return DatasetSourceLocator(
        repo_id=_require_str(locator_payload, "repo_id", source_path),
        config=_require_str(locator_payload, "config", source_path),
        split=_require_str(locator_payload, "split", source_path),
        revision=_require_pinned_revision(locator_payload, "revision", source_path),
    )


def _require_str(payload: dict[str, Any], key: str, source_path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected string for {key!r} in {source_path}")
    return value


def _require_pinned_revision(payload: dict[str, Any], key: str, source_path: Path) -> str:
    raw_revision = payload.get(key)
    if raw_revision is None:
        revision = ""
    elif isinstance(raw_revision, str):
        revision = raw_revision.strip()
    else:
        raise ValueError(f"Expected string for {key!r} in {source_path}")
    if revision in {"", "main", "master"}:
        raise ValueError(
            f"Expected pinned revision for {key!r} in {source_path}, got {revision or '<empty>'}"
        )
    return revision


def _optional_str(payload: dict[str, Any], key: str, source_path: Path) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Expected optional string for {key!r} in {source_path}")
    return value


def _require_int(payload: dict[str, Any], key: str, source_path: Path) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Expected integer for {key!r} in {source_path}")
    return value


def _require_str_list(payload: dict[str, Any], key: str, source_path: Path) -> list[str]:
    value = payload.get(key)
    return _require_sequence_of_str(value, key, source_path)


def _require_sequence_of_str(value: Any, key: str, source_path: Path) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Expected list[str] for {key!r} in {source_path}")
    return cast(list[str], value)
