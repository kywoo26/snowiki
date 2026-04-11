from __future__ import annotations

from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]


class SurfacePolicy(TypedDict):
    owner: str
    required_children: list[str]


GOVERNED_SURFACES: dict[str, SurfacePolicy] = {
    "snowiki": {
        "owner": "root AGENTS.md",
        "required_children": ["config.py", "storage/zones.py", "bench"],
    },
    "tests": {
        "owner": "root AGENTS.md",
        "required_children": ["governance"],
    },
    "scripts": {
        "owner": "root AGENTS.md",
        "required_children": [],
    },
    "snowiki/bench": {
        "owner": "root AGENTS.md",
        "required_children": [],
    },
    "benchmarks": {
        "owner": "benchmarks/AGENTS.md",
        "required_children": ["README.md", "queries.json", "judgments.json"],
    },
    "vault-template": {
        "owner": "vault-template/AGENTS.md",
        "required_children": ["CLAUDE.md", "wiki"],
    },
    "skill": {
        "owner": "skill/AGENTS.md",
        "required_children": ["SKILL.md", "scripts", "workflows"],
    },
    ".sisyphus": {
        "owner": "root AGENTS.md",
        "required_children": ["plans", "evidence", "notepads"],
    },
}

NON_CANONICAL_STATUS_SURFACES = {
    ".sisyphus/plans",
    ".sisyphus/evidence",
    "AGENTS.md",
    "pyproject.toml",
    "tests/governance/test_structure_contract.py",
}


def test_governed_surfaces_exist_with_expected_owners() -> None:
    for relative_path, policy in GOVERNED_SURFACES.items():
        surface = ROOT / relative_path
        assert surface.exists(), relative_path
        assert policy["owner"]

        for child in policy["required_children"]:
            assert (surface / child).exists(), f"{relative_path}/{child}"


def test_governed_surface_policy_includes_child_owned_instruction_hotspots() -> None:
    assert GOVERNED_SURFACES["benchmarks"]["owner"] == "benchmarks/AGENTS.md"
    assert GOVERNED_SURFACES["vault-template"]["owner"] == "vault-template/AGENTS.md"
    assert GOVERNED_SURFACES["skill"]["owner"] == "skill/AGENTS.md"


def test_sisyphus_is_planning_and_evidence_only() -> None:
    sisyphus_policy = GOVERNED_SURFACES[".sisyphus"]

    assert sisyphus_policy["owner"] == "root AGENTS.md"
    assert all(
        (ROOT / ".sisyphus" / child).exists()
        for child in sisyphus_policy["required_children"]
    )
    assert not (ROOT / ".sisyphus" / "STATUS.md").exists()


def test_status_md_is_not_a_canonical_repo_surface() -> None:
    assert not (ROOT / "STATUS.md").exists()

    for relative_path in NON_CANONICAL_STATUS_SURFACES:
        assert (ROOT / relative_path).exists(), relative_path
