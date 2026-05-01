from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self, cast

from snowiki.storage.zones import StoragePaths, atomic_write_json

FreshnessStatus = Literal["current", "stale", "missing", "invalid"]

_FRESHNESS_STATUSES = frozenset(("current", "stale", "missing", "invalid"))


def _join_path(parent: str, key: str) -> str:
    if parent in ("", "$"):
        return key
    return f"{parent}.{key}"


def _require_mapping(value: object, field_path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_path} must be an object")
    return cast(Mapping[str, object], value)


def _require_key(
    payload: Mapping[str, object],
    key: str,
    parent_path: str,
) -> object:
    field_path = _join_path(parent_path, key)
    try:
        return payload[key]
    except KeyError as error:
        raise ValueError(f"{field_path} is required") from error


def _validate_non_negative_int(value: object, field_path: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_path} must be an integer")
    if value < 0:
        raise ValueError(f"{field_path} must be non-negative")


def _require_non_negative_int(
    payload: Mapping[str, object],
    key: str,
    parent_path: str,
) -> int:
    field_path = _join_path(parent_path, key)
    value = _require_key(payload, key, parent_path)
    _validate_non_negative_int(value, field_path)
    return cast(int, value)


def _validate_str(value: object, field_path: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_path} must be a string")


def _require_str(payload: Mapping[str, object], key: str, parent_path: str) -> str:
    field_path = _join_path(parent_path, key)
    value = _require_key(payload, key, parent_path)
    _validate_str(value, field_path)
    return cast(str, value)


def _validate_non_empty_str(value: object, field_path: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_path} must be a string")
    if not value.strip():
        raise ValueError(f"{field_path} must not be empty")


def _require_non_empty_str(
    payload: Mapping[str, object],
    key: str,
    parent_path: str,
) -> str:
    field_path = _join_path(parent_path, key)
    value = _require_key(payload, key, parent_path)
    _validate_non_empty_str(value, field_path)
    return cast(str, value)


def _validate_str_tuple(values: object, field_path: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_path} must be a tuple of strings")
    validated: list[str] = []
    for index, value in enumerate(values):
        _validate_str(value, f"{field_path}.{index}")
        validated.append(cast(str, value))
    return tuple(validated)


def _require_str_tuple(
    payload: Mapping[str, object],
    key: str,
    parent_path: str,
) -> tuple[str, ...]:
    field_path = _join_path(parent_path, key)
    value = _require_key(payload, key, parent_path)
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_path} must be a list of strings")
    values: list[str] = []
    for index, item in enumerate(cast(list[object] | tuple[object, ...], value)):
        item_path = f"{field_path}.{index}"
        _validate_str(item, item_path)
        values.append(cast(str, item))
    return tuple(values)


def _require_reasons_tuple(
    payload: Mapping[str, object],
    key: str,
    parent_path: str,
) -> tuple[FreshnessReason, ...]:
    field_path = _join_path(parent_path, key)
    value = _require_key(payload, key, parent_path)
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_path} must be a list of freshness reasons")
    return tuple(
        FreshnessReason.from_payload_at(item, f"{field_path}.{index}")
        for index, item in enumerate(cast(list[object] | tuple[object, ...], value))
    )


def _validate_freshness_status(value: object, field_path: str) -> None:
    if value not in _FRESHNESS_STATUSES:
        raise ValueError(
            f"{field_path} must be one of current, stale, missing, or invalid"
        )


def _require_freshness_status(
    payload: Mapping[str, object],
    key: str,
    parent_path: str,
) -> FreshnessStatus:
    field_path = _join_path(parent_path, key)
    value = _require_key(payload, key, parent_path)
    _validate_str(value, field_path)
    _validate_freshness_status(value, field_path)
    return cast(FreshnessStatus, value)


def _validate_bool(value: object, field_path: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_path} must be a boolean")


def _require_bool(payload: Mapping[str, object], key: str, parent_path: str) -> bool:
    field_path = _join_path(parent_path, key)
    value = _require_key(payload, key, parent_path)
    _validate_bool(value, field_path)
    return cast(bool, value)


def _optional_non_negative_int(
    payload: Mapping[str, object],
    key: str,
    default: int,
) -> int:
    value = payload.get(key, default)
    _validate_non_negative_int(value, key)
    return cast(int, value)


def _layer_identity_from_signature(root: Path) -> LayerIdentity:
    if not root.exists():
        return LayerIdentity(latest_mtime_ns=0, file_count=0, content_hash="")
    latest_mtime_ns = root.stat().st_mtime_ns
    file_count = 0
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)
        if path.is_file():
            file_count += 1
            relative_path = path.relative_to(root).as_posix()
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            try:
                digest.update(path.read_bytes())
            except FileNotFoundError:
                continue
            digest.update(b"\0")
    return LayerIdentity(
        latest_mtime_ns=latest_mtime_ns,
        file_count=file_count,
        content_hash=digest.hexdigest(),
    )


_LEGACY_MANIFEST_RETRIEVAL_SPECS: dict[str, tuple[str, str]] = {
    "regex_v1": ("regex", "1"),
    "kiwi_morphology_v1": ("kiwi", "2"),
    "kiwi_nouns_v1": ("kiwi", "2"),
    "mecab_morphology_v1": ("mecab", "3"),
    "hf_wordpiece_v1": ("subword", "2"),
}


def _normalize_legacy_manifest_tokenizer_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError("legacy tokenizer identity is required")
    return normalized


def _legacy_manifest_retrieval_identity(name: str) -> RetrievalIdentity:
    try:
        family, version = _LEGACY_MANIFEST_RETRIEVAL_SPECS[name]
    except KeyError as error:
        raise ValueError(f"unknown legacy tokenizer identity: {name}") from error
    return RetrievalIdentity(name=name, family=family, version=version)


def _legacy_retrieval_identity(payload: Mapping[str, object]) -> RetrievalIdentity:
    content_identity = payload.get("content_identity")
    if isinstance(content_identity, Mapping):
        identity_payload = cast(Mapping[str, object], content_identity)
        raw_tokenizer = identity_payload.get("tokenizer")
        if isinstance(raw_tokenizer, Mapping):
            tokenizer_payload = dict(cast(Mapping[str, object], raw_tokenizer))
            if "version" in tokenizer_payload:
                tokenizer_payload["version"] = str(tokenizer_payload["version"])
            return RetrievalIdentity.from_payload_at(
                tokenizer_payload,
                "content_identity.tokenizer",
            )

    raw_tokenizer_name = payload.get("tokenizer_name")
    if isinstance(raw_tokenizer_name, str) and raw_tokenizer_name.strip():
        normalized_name = _normalize_legacy_manifest_tokenizer_name(raw_tokenizer_name)
        return _legacy_manifest_retrieval_identity(normalized_name)

    has_legacy_flags = (
        "use_kiwi_tokenizer" in payload or "kiwi_lexical_candidate_mode" in payload
    )
    if not has_legacy_flags:
        raise ValueError("legacy tokenizer identity is required")

    raw_use_kiwi_tokenizer = payload.get("use_kiwi_tokenizer")
    raw_kiwi_lexical_candidate_mode = payload.get("kiwi_lexical_candidate_mode")
    use_kiwi_tokenizer: bool | None
    if isinstance(raw_use_kiwi_tokenizer, bool):
        use_kiwi_tokenizer = raw_use_kiwi_tokenizer
    elif isinstance(raw_kiwi_lexical_candidate_mode, str):
        use_kiwi_tokenizer = True
    else:
        use_kiwi_tokenizer = None

    if use_kiwi_tokenizer is False:
        return _legacy_manifest_retrieval_identity("regex_v1")
    if raw_kiwi_lexical_candidate_mode == "nouns":
        return _legacy_manifest_retrieval_identity("kiwi_nouns_v1")
    return _legacy_manifest_retrieval_identity("kiwi_morphology_v1")


def _freshness_reason(
    field_path: str,
    manifest_value: object,
    current_value: object,
) -> FreshnessReason:
    return FreshnessReason(
        field_path=field_path,
        manifest_value=manifest_value,
        current_value=current_value,
    )


@dataclass(frozen=True, slots=True)
class LayerIdentity:
    latest_mtime_ns: int
    file_count: int
    content_hash: str

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.latest_mtime_ns, "latest_mtime_ns")
        _validate_non_negative_int(self.file_count, "file_count")
        _validate_str(self.content_hash, "content_hash")

    def to_payload(self) -> dict[str, object]:
        return {
            "latest_mtime_ns": self.latest_mtime_ns,
            "file_count": self.file_count,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        return cls.from_payload_at(payload, "LayerIdentity")

    @classmethod
    def from_payload_at(cls, payload: object, field_path: str) -> Self:
        data = _require_mapping(payload, field_path)
        return cls(
            latest_mtime_ns=_require_non_negative_int(
                data, "latest_mtime_ns", field_path
            ),
            file_count=_require_non_negative_int(data, "file_count", field_path),
            content_hash=_require_str(data, "content_hash", field_path),
        )


@dataclass(frozen=True, slots=True)
class RetrievalIdentity:
    name: str
    family: str
    version: str

    def __post_init__(self) -> None:
        _validate_non_empty_str(self.name, "name")
        _validate_non_empty_str(self.family, "family")
        _validate_non_empty_str(self.version, "version")

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "family": self.family,
            "version": self.version,
        }

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        return cls.from_payload_at(payload, "RetrievalIdentity")

    @classmethod
    def from_payload_at(cls, payload: object, field_path: str) -> Self:
        data = _require_mapping(payload, field_path)
        return cls(
            name=_require_non_empty_str(data, "name", field_path),
            family=_require_non_empty_str(data, "family", field_path),
            version=_require_non_empty_str(data, "version", field_path),
        )


class ManifestRetrievalIdentityMismatchError(ValueError):
    def __init__(
        self,
        *,
        expected: RetrievalIdentity,
        actual: RetrievalIdentity,
    ) -> None:
        super().__init__(
            "retrieval identity mismatch: "
            f"expected {expected.to_payload()}, found {actual.to_payload()}"
        )
        self.expected = expected
        self.actual = actual


@dataclass(frozen=True, slots=True)
class IndexIdentity:
    normalized: LayerIdentity
    compiled: LayerIdentity
    retrieval: RetrievalIdentity

    def __post_init__(self) -> None:
        normalized = cast(object, self.normalized)
        compiled = cast(object, self.compiled)
        retrieval = cast(object, self.retrieval)
        if not isinstance(normalized, LayerIdentity):
            raise TypeError("normalized must be a LayerIdentity")
        if not isinstance(compiled, LayerIdentity):
            raise TypeError("compiled must be a LayerIdentity")
        if not isinstance(retrieval, RetrievalIdentity):
            raise TypeError("retrieval must be a RetrievalIdentity")

    def to_payload(self) -> dict[str, object]:
        return {
            "normalized": self.normalized.to_payload(),
            "compiled": self.compiled.to_payload(),
            "retrieval": self.retrieval.to_payload(),
        }

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        return cls.from_payload_at(payload, "IndexIdentity")

    @classmethod
    def from_payload_at(cls, payload: object, field_path: str) -> Self:
        data = _require_mapping(payload, field_path)
        return cls(
            normalized=LayerIdentity.from_payload_at(
                _require_key(data, "normalized", field_path),
                _join_path(field_path, "normalized"),
            ),
            compiled=LayerIdentity.from_payload_at(
                _require_key(data, "compiled", field_path),
                _join_path(field_path, "compiled"),
            ),
            retrieval=RetrievalIdentity.from_payload_at(
                _require_key(data, "retrieval", field_path),
                _join_path(field_path, "retrieval"),
            ),
        )


@dataclass(frozen=True, slots=True)
class IndexManifest:
    schema_version: int
    records_indexed: int
    pages_indexed: int
    search_documents: int
    compiled_paths: tuple[str, ...]
    identity: IndexIdentity

    def __post_init__(self) -> None:
        _validate_non_negative_int(self.schema_version, "schema_version")
        _validate_non_negative_int(self.records_indexed, "records_indexed")
        _validate_non_negative_int(self.pages_indexed, "pages_indexed")
        _validate_non_negative_int(self.search_documents, "search_documents")
        _ = _validate_str_tuple(self.compiled_paths, "compiled_paths")
        identity = cast(object, self.identity)
        if not isinstance(identity, IndexIdentity):
            raise TypeError("identity must be an IndexIdentity")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "records_indexed": self.records_indexed,
            "pages_indexed": self.pages_indexed,
            "search_documents": self.search_documents,
            "compiled_paths": list(self.compiled_paths),
            "identity": self.identity.to_payload(),
        }

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        data = _require_mapping(payload, "IndexManifest")
        return cls(
            schema_version=_require_non_negative_int(data, "schema_version", "$"),
            records_indexed=_require_non_negative_int(data, "records_indexed", "$"),
            pages_indexed=_require_non_negative_int(data, "pages_indexed", "$"),
            search_documents=_require_non_negative_int(data, "search_documents", "$"),
            compiled_paths=_require_str_tuple(data, "compiled_paths", "$"),
            identity=IndexIdentity.from_payload_at(
                _require_key(data, "identity", "$"),
                "identity",
            ),
        )


@dataclass(frozen=True, slots=True)
class FreshnessReason:
    field_path: str
    manifest_value: object
    current_value: object

    def __post_init__(self) -> None:
        _validate_non_empty_str(self.field_path, "field_path")

    def to_payload(self) -> dict[str, object]:
        return {
            "field_path": self.field_path,
            "manifest_value": self.manifest_value,
            "current_value": self.current_value,
        }

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        return cls.from_payload_at(payload, "FreshnessReason")

    @classmethod
    def from_payload_at(cls, payload: object, field_path: str) -> Self:
        data = _require_mapping(payload, field_path)
        return cls(
            field_path=_require_non_empty_str(data, "field_path", field_path),
            manifest_value=_require_key(data, "manifest_value", field_path),
            current_value=_require_key(data, "current_value", field_path),
        )


@dataclass(frozen=True, slots=True)
class FreshnessExplanation:
    status: FreshnessStatus
    reasons: tuple[FreshnessReason, ...]
    rebuild_required: bool

    def __post_init__(self) -> None:
        _validate_freshness_status(self.status, "status")
        reasons = cast(object, self.reasons)
        if not isinstance(reasons, tuple):
            raise TypeError("reasons must be a tuple of FreshnessReason values")
        for index, reason in enumerate(cast(tuple[object, ...], self.reasons)):
            if not isinstance(reason, FreshnessReason):
                raise TypeError(f"reasons.{index} must be a FreshnessReason")
        _validate_bool(self.rebuild_required, "rebuild_required")

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reasons": [reason.to_payload() for reason in self.reasons],
            "rebuild_required": self.rebuild_required,
        }

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        data = _require_mapping(payload, "FreshnessExplanation")
        return cls(
            status=_require_freshness_status(data, "status", "$"),
            reasons=_require_reasons_tuple(data, "reasons", "$"),
            rebuild_required=_require_bool(data, "rebuild_required", "$"),
        )


def index_manifest_path(paths: StoragePaths) -> Path:
    return paths.index / "manifest.json"


def parse_index_manifest(payload: object) -> IndexManifest:
    return IndexManifest.from_payload(payload)


def normalize_legacy_index_manifest(payload: dict[str, object]) -> IndexManifest:
    content_identity = _require_mapping(
        payload.get("content_identity"),
        "content_identity",
    )
    return IndexManifest(
        schema_version=_optional_non_negative_int(payload, "schema_version", 1),
        records_indexed=_optional_non_negative_int(payload, "records_indexed", 0),
        pages_indexed=_optional_non_negative_int(payload, "pages_indexed", 0),
        search_documents=_optional_non_negative_int(payload, "search_documents", 0),
        compiled_paths=_require_str_tuple(payload, "compiled_paths", "$"),
        identity=IndexIdentity(
            normalized=LayerIdentity.from_payload_at(
                _require_key(content_identity, "normalized", "content_identity"),
                "content_identity.normalized",
            ),
            compiled=LayerIdentity.from_payload_at(
                _require_key(content_identity, "compiled", "content_identity"),
                "content_identity.compiled",
            ),
            retrieval=_legacy_retrieval_identity(payload),
        ),
    )


def load_index_manifest(paths: StoragePaths) -> IndexManifest | None:
    path = index_manifest_path(paths)
    if not path.exists():
        return None
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "identity" not in payload:
        return normalize_legacy_index_manifest(cast(dict[str, object], payload))
    return parse_index_manifest(payload)


def write_index_manifest(paths: StoragePaths, manifest: IndexManifest) -> None:
    manifest_path = index_manifest_path(paths)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _ = atomic_write_json(manifest_path, manifest.to_payload())


def current_layer_identity(paths: StoragePaths, layer: str) -> LayerIdentity:
    if layer == "normalized":
        return _layer_identity_from_signature(paths.normalized)
    if layer == "compiled":
        return _layer_identity_from_signature(paths.compiled)
    raise ValueError("layer must be normalized or compiled")


def current_index_identity(
    paths: StoragePaths,
    retrieval_identity: RetrievalIdentity,
) -> IndexIdentity:
    return IndexIdentity(
        normalized=current_layer_identity(paths, "normalized"),
        compiled=current_layer_identity(paths, "compiled"),
        retrieval=retrieval_identity,
    )


def explain_index_freshness(
    paths: StoragePaths,
    current: IndexIdentity,
) -> tuple[IndexManifest | None, FreshnessExplanation]:
    try:
        manifest = load_index_manifest(paths)
        manifest_for_comparison = manifest
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        manifest = None
        manifest_for_comparison = "invalid"
    explanation = compare_index_identity(manifest_for_comparison, current)
    return manifest, explanation


def current_content_identity_payload(
    paths: StoragePaths,
    retrieval_identity: RetrievalIdentity,
) -> dict[str, object]:
    return status_identity_payload(current_index_identity(paths, retrieval_identity))


def load_manifest_retrieval_identity(paths: StoragePaths) -> RetrievalIdentity | None:
    path = index_manifest_path(paths)
    if not path.exists():
        return None
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("index manifest must be an object")
    data = cast(Mapping[str, object], payload)
    raw_identity = data.get("identity")
    if isinstance(raw_identity, Mapping):
        identity = cast(Mapping[str, object], raw_identity)
        retrieval = identity.get("retrieval")
        if retrieval is not None:
            return RetrievalIdentity.from_payload_at(retrieval, "identity.retrieval")
    return _legacy_retrieval_identity(data)


def validate_manifest_retrieval_identity(
    paths: StoragePaths,
    expected: RetrievalIdentity,
) -> RetrievalIdentity | None:
    retrieval_identity = load_manifest_retrieval_identity(paths)
    if retrieval_identity is None:
        return None
    if retrieval_identity != expected:
        raise ManifestRetrievalIdentityMismatchError(
            expected=expected,
            actual=retrieval_identity,
        )
    return retrieval_identity


def compare_index_identity(
    manifest: IndexManifest | None | str,
    current: IndexIdentity,
) -> FreshnessExplanation:
    if manifest is None:
        return FreshnessExplanation(
            status="missing",
            reasons=(
                _freshness_reason(
                    "identity",
                    None,
                    current.to_payload(),
                ),
            ),
            rebuild_required=True,
        )
    if isinstance(manifest, str):
        return FreshnessExplanation(
            status="invalid",
            reasons=(
                _freshness_reason(
                    "identity",
                    manifest,
                    current.to_payload(),
                ),
            ),
            rebuild_required=True,
        )

    reasons: list[FreshnessReason] = []
    _append_layer_reasons(
        reasons,
        "identity.normalized",
        manifest.identity.normalized,
        current.normalized,
    )
    _append_layer_reasons(
        reasons,
        "identity.compiled",
        manifest.identity.compiled,
        current.compiled,
    )
    _append_retrieval_reasons(
        reasons,
        manifest.identity.retrieval,
        current.retrieval,
    )
    if not reasons:
        return FreshnessExplanation(
            status="current",
            reasons=(),
            rebuild_required=False,
        )
    return FreshnessExplanation(
        status="stale",
        reasons=tuple(reasons),
        rebuild_required=True,
    )


def validate_retrieval_identity(
    manifest: IndexManifest,
    expected_name: str,
) -> None:
    manifest_object = cast(object, manifest)
    _validate_non_empty_str(expected_name, "expected_name")
    if not isinstance(manifest_object, IndexManifest):
        raise ValueError("index manifest is invalid")
    actual_name = manifest.identity.retrieval.name
    if actual_name != expected_name:
        raise ValueError(
            f"retrieval identity mismatch: expected {expected_name}, found {actual_name}"
        )


def to_status_payload(
    *,
    manifest: IndexManifest | None,
    current: IndexIdentity,
    explanation: FreshnessExplanation,
    latest_normalized_recorded_at: str | None,
    latest_compiled_update: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": explanation.status,
        "manifest_content_identity": (
            status_identity_payload(manifest.identity) if manifest is not None else None
        ),
        "current_content_identity": status_identity_payload(current),
        "latest_normalized_recorded_at": latest_normalized_recorded_at,
        "latest_compiled_update": latest_compiled_update,
    }
    if explanation.reasons:
        payload["reasons"] = [_reason_payload(reason) for reason in explanation.reasons]
    return payload


def status_identity_payload(identity: IndexIdentity) -> dict[str, object]:
    retrieval = identity.retrieval.to_payload()
    if identity.retrieval.version.isdecimal():
        retrieval["version"] = int(identity.retrieval.version)
    return {
        "normalized": identity.normalized.to_payload(),
        "compiled": identity.compiled.to_payload(),
        "tokenizer": retrieval,
    }


def _legacy_reason_value_payload(value: object) -> object:
    if not isinstance(value, Mapping):
        return value
    payload = cast(Mapping[str, object], value)
    normalized = payload.get("normalized")
    compiled = payload.get("compiled")
    retrieval = payload.get("retrieval")
    tokenizer = payload.get("tokenizer")
    tokenizer_payload = retrieval if isinstance(retrieval, Mapping) else tokenizer
    if (
        isinstance(normalized, Mapping)
        and isinstance(compiled, Mapping)
        and isinstance(tokenizer_payload, Mapping)
    ):
        projected_tokenizer = dict(cast(Mapping[str, object], tokenizer_payload))
        version = projected_tokenizer.get("version")
        if isinstance(version, str) and version.isdecimal():
            projected_tokenizer["version"] = int(version)
        return {
            "normalized": dict(cast(Mapping[str, object], normalized)),
            "compiled": dict(cast(Mapping[str, object], compiled)),
            "tokenizer": projected_tokenizer,
        }
    return dict(payload)


def _public_reason_field_path(field_path: str) -> str:
    if field_path == "identity":
        return "content_identity"
    if field_path.startswith("identity.normalized"):
        return field_path.replace("identity.normalized", "content_identity.normalized", 1)
    if field_path.startswith("identity.compiled"):
        return field_path.replace("identity.compiled", "content_identity.compiled", 1)
    if field_path.startswith("identity.retrieval"):
        return field_path.replace("identity.retrieval", "content_identity.tokenizer", 1)
    return field_path


def _public_reason_current_value(field_path: str, value: object) -> object:
    if (
        field_path == "content_identity.tokenizer.version"
        and isinstance(value, str)
        and value.isdecimal()
    ):
        return int(value)
    return _legacy_reason_value_payload(value)


def _reason_payload(reason: FreshnessReason) -> dict[str, object]:
    public_field_path = _public_reason_field_path(reason.field_path)
    return {
        "field_path": public_field_path,
        "manifest_value": _legacy_reason_value_payload(reason.manifest_value),
        "current_value": _public_reason_current_value(
            public_field_path,
            reason.current_value,
        ),
    }


def to_manifest_stats_payload(
    manifest: IndexManifest | None,
    *,
    present: bool | None = None,
) -> dict[str, str | int | bool | None]:
    manifest_present = manifest is not None if present is None else present
    return {
        "path": "index/manifest.json",
        "present": manifest_present,
        "tokenizer_name": manifest.identity.retrieval.name if manifest is not None else None,
        "records_indexed": manifest.records_indexed if manifest is not None else None,
        "pages_indexed": manifest.pages_indexed if manifest is not None else None,
        "search_documents": manifest.search_documents if manifest is not None else None,
        "compiled_path_count": len(manifest.compiled_paths) if manifest is not None else None,
    }


def to_lint_issue_payload(
    explanation: FreshnessExplanation,
    *,
    path: str = "index/manifest.json",
) -> list[dict[str, object]]:
    if explanation.status == "current":
        return []
    messages = {
        "missing": "index manifest missing for compiled layer",
        "invalid": "index manifest is invalid; rebuild required",
        "stale": "index manifest is stale; rebuild required",
    }
    issue: dict[str, object] = {
        "code": "L104",
        "check": "integrity.index_manifest",
        "severity": "error",
        "path": path,
        "message": messages.get(
            explanation.status,
            "index manifest is invalid; rebuild required",
        ),
    }
    if explanation.status in ("invalid", "stale") and explanation.reasons:
        issue["reasons"] = [_reason_payload(reason) for reason in explanation.reasons]
    return [issue]


def _append_layer_reasons(
    reasons: list[FreshnessReason],
    prefix: str,
    manifest_layer: LayerIdentity,
    current_layer: LayerIdentity,
) -> None:
    if manifest_layer.latest_mtime_ns != current_layer.latest_mtime_ns:
        reasons.append(
            _freshness_reason(
                f"{prefix}.latest_mtime_ns",
                manifest_layer.latest_mtime_ns,
                current_layer.latest_mtime_ns,
            )
        )
    if manifest_layer.file_count != current_layer.file_count:
        reasons.append(
            _freshness_reason(
                f"{prefix}.file_count",
                manifest_layer.file_count,
                current_layer.file_count,
            )
        )
    if manifest_layer.content_hash != current_layer.content_hash:
        reasons.append(
            _freshness_reason(
                f"{prefix}.content_hash",
                manifest_layer.content_hash,
                current_layer.content_hash,
            )
        )


def _append_retrieval_reasons(
    reasons: list[FreshnessReason],
    manifest_retrieval: RetrievalIdentity,
    current_retrieval: RetrievalIdentity,
) -> None:
    if manifest_retrieval.name != current_retrieval.name:
        reasons.append(
            _freshness_reason(
                "identity.retrieval.name",
                manifest_retrieval.name,
                current_retrieval.name,
            )
        )
    if manifest_retrieval.family != current_retrieval.family:
        reasons.append(
            _freshness_reason(
                "identity.retrieval.family",
                manifest_retrieval.family,
                current_retrieval.family,
            )
        )
    if manifest_retrieval.version != current_retrieval.version:
        reasons.append(
            _freshness_reason(
                "identity.retrieval.version",
                manifest_retrieval.version,
                current_retrieval.version,
            )
        )


__all__ = [
    "FreshnessExplanation",
    "FreshnessReason",
    "FreshnessStatus",
    "IndexIdentity",
    "IndexManifest",
    "LayerIdentity",
    "ManifestRetrievalIdentityMismatchError",
    "RetrievalIdentity",
    "compare_index_identity",
    "current_content_identity_payload",
    "current_index_identity",
    "current_layer_identity",
    "status_identity_payload",
    "index_manifest_path",
    "load_manifest_retrieval_identity",
    "load_index_manifest",
    "normalize_legacy_index_manifest",
    "parse_index_manifest",
    "to_lint_issue_payload",
    "to_manifest_stats_payload",
    "to_status_payload",
    "validate_manifest_retrieval_identity",
    "validate_retrieval_identity",
    "write_index_manifest",
]
