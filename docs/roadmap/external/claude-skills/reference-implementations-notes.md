# Reference Implementations Notes: Claude Skills

This document captures key example/standard repositories and materials for Claude skill packaging, route design, and workflow patterns.

## 1. Canonical Official Examples

### Anthropics Skills Repository
- **Source URL(s)**: 
    - [anthropics/skills](https://github.com/anthropics/skills)
    - [template/SKILL.md](https://raw.githubusercontent.com/anthropics/skills/main/template/SKILL.md)
    - [skills/docx/SKILL.md](https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md)
    - [skills/pdf/SKILL.md](https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md)
- **File/Section Pointers**: 
    - README: "About This Repository", "Skill Sets", "Creating a Basic Skill"
    - `template/SKILL.md` for standard structure
    - `skills/docx/` and `skills/pdf/` for real-world workflow examples
- **Contribution**: Demonstrates "skills as packages" structure (`skills/`, `spec/`, `template/`). Provides official implementation patterns for Claude Code skills and real workflows with helper scripts.
- **Evidence Strength**: Strong (Canonical)
- **Snowiki-Incompatible Patterns**: Document-generation patterns often imply direct file writes. Snowiki must maintain a reviewable/CLI-mediated write posture for durable knowledge.

### Agent Skills Specification
- **Source URL(s)**: 
    - [agentskills/agentskills](https://github.com/agentskills/agentskills)
    - [agentskills.io/specification](https://agentskills.io/specification)
    - [agentskills.io/client-implementation/adding-skills-support](https://agentskills.io/client-implementation/adding-skills-support)
    - [agentskills.io/skill-creation/best-practices](https://agentskills.io/skill-creation/best-practices)
- **File/Section Pointers**: 
    - `specification.md`: Directory structure and frontmatter constraints
    - `adding-skills-support.md`: Steps 1-5 for client implementation
    - `best-practices.md`: Gotchas, templates, and checklists
- **Contribution**: Normative specification for the SKILL.md format. Defines progressive disclosure (Discovery -> Activation -> Resources), discovery/activation models, and `.agents/skills/` conventions.
- **Evidence Strength**: Strong (Canonical)
- **Snowiki-Incompatible Patterns**: Mostly compatible. Caution against `allowed-tools` or bundled scripts creating unchecked mutation paths or interactive flows that bypass Snowiki's governance.

### Claude Skills Cookbook
- **Source URL(s)**: [Introduction to Claude Skills](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction)
- **File/Section Pointers**: 
    - "Progressive Disclosure Architecture"
    - "How Skills Work with Code Execution"
    - "Discovering Available Skills"
    - Quickstarts for xlsx/pptx/pdf
- **Contribution**: Practical end-to-end workflow for skills-enabled file creation. Shows metadata-only discovery, full-load activation, and code execution requirements.
- **Evidence Strength**: Strong (Official)
- **Snowiki-Incompatible Patterns**: The beta API/file-creation flow uses an implicit "write files directly from skill execution" posture. Snowiki requires explicit, reviewable proposals for durable wiki updates.

---

## 2. External Pattern References

### Farzapedia (FarzaTV)
- **Source URL(s)**: 
    - [Farzapedia Gist](https://gist.github.com/farzaa/c35ac0cfbeb957788650e36aabea836d)
    - [farza.com/knowledge](https://farza.com/knowledge)
- **File/Section Pointers**: 
    - `wiki-gen-skill.md`: "Directory Structure", "/wiki ingest", "/wiki absorb", "/wiki query", "/wiki cleanup", "/wiki breakdown", "/wiki status"
    - "Rules" and "Concurrency Rules"
- **Contribution**: Most operationally explicit `/wiki` command family. Introduces the **agent maintenance loop** (ingest → absorb → cleanup → query) and `status` as a first-class route.
- **Evidence Strength**: Medium (Pattern)
- **Snowiki-Incompatible Patterns**: Implicit write model and voice-heavy taxonomy. Weaker provenance/review discipline than Snowiki's contract requires.

### Karpathy’s LLM Wiki
- **Source URL(s)**: [Karpathy LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- **File/Section Pointers**: 
    - `llm-wiki.md`: "The core idea", "Architecture", "Operations", "Indexing and logging"
- **Contribution**: Classic three-layer model: `raw sources` → `compiled wiki` → `schema/rules`. Simple `ingest/query/lint` loop. Emphasizes index-first navigation and append-only maintenance.
- **Evidence Strength**: Medium (Pattern)
- **Snowiki-Incompatible Patterns**: Conceptual and lightweight; lacks durable governance or a formal reviewable write posture.

### personal-os-skills (ArtemXTech)
- **Source URL(s)**: 
    - [ArtemXTech/personal-os-skills](https://github.com/ArtemXTech/personal-os-skills)
    - [memory-skills-setup.md](https://github.com/ArtemXTech/personal-os-skills/blob/main/docs/memory-skills-setup.md)
- **File/Section Pointers**: 
    - README: "Available Skills"
    - `skills/` directory for route splitting examples
- **Contribution**: Concrete packaged Claude Code skills with explicit frontmatter and machine-readable schema files (YAML/JSON) for I/O validation. Separates temporal, topic, and graph-style routes.
- **Evidence Strength**: Medium (Pattern)
- **Snowiki-Incompatible Patterns**: Obsidian-specific operational assumptions and sync flows that might conflict with Snowiki's CLI-first truth.

### seCall (hang-in)
- **Source URL(s)**: [hang-in/seCall](https://github.com/hang-in/seCall)
- **File/Section Pointers**: 
    - README: "지식 볼트" (Knowledge Vault), "Knowledge Graph", "CLI 레퍼런스"
    - `crates/secall-core/src/search/tokenizer.rs` (Lindera/Kiwi fallback)
    - `crates/secall-core/src/search/hybrid.rs` (RRF and diversity cap)
- **Contribution**: Vault-as-source-of-truth model. Proven Korean-aware patterns (Lindera default + Kiwi opt-in). Hybrid fusion (RRF `k=60`) and session diversity capping.
- **Evidence Strength**: Medium (Pattern)
- **Snowiki-Incompatible Patterns**: Derived caches or sync flows must not become the primary truth; Snowiki maintains mutation through the CLI.

### qmd (tobi/qmd)
- **Source URL(s)**: [tobi/qmd](https://github.com/tobi/qmd)
- **File/Section Pointers**: 
    - `src/store.ts`: Retrieval pipeline and strong-signal shortcut
    - `README.md`: Product definition and hybrid modality
- **Contribution**: Upstream lineage for Snowiki's retrieval target. Defines the **strong-signal shortcut** (skip hybrid if lexical is dominant) and RRF parameters.
- **Evidence Strength**: Medium (Pattern)
- **Snowiki-Incompatible Patterns**: None major; primarily a retrieval reference rather than a skill packaging reference.
