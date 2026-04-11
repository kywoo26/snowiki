from __future__ import annotations

from typing import TypedDict


class SurfacePolicy(TypedDict):
    owner: str
    required_children: list[str]


GOVERNED_SURFACES: dict[str, SurfacePolicy] = {
    "src/snowiki": {
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
    "src/snowiki/bench": {
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
}

NON_CANONICAL_STATUS_SURFACES = {
    "AGENTS.md",
    "pyproject.toml",
    "tests/governance/test_structure_contract.py",
}


def test_governed_surfaces_exist_with_expected_owners(repo_root) -> None:
    for relative_path, policy in GOVERNED_SURFACES.items():
        surface = repo_root / relative_path
        assert surface.exists(), relative_path
        assert policy["owner"]

        for child in policy["required_children"]:
            assert (surface / child).exists(), f"{relative_path}/{child}"


def test_governed_surface_policy_includes_child_owned_instruction_hotspots() -> None:
    assert GOVERNED_SURFACES["benchmarks"]["owner"] == "benchmarks/AGENTS.md"
    assert GOVERNED_SURFACES["vault-template"]["owner"] == "vault-template/AGENTS.md"
    assert GOVERNED_SURFACES["skill"]["owner"] == "skill/AGENTS.md"


def test_status_md_is_not_a_canonical_repo_surface(repo_root) -> None:
    assert not (repo_root / "STATUS.md").exists()

    for relative_path in NON_CANONICAL_STATUS_SURFACES:
        assert (repo_root / relative_path).exists(), relative_path
