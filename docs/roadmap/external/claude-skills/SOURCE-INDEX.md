# Claude Skill Authoring: Source Index

This index maps the authoritative and reference sources used to build the Snowiki Claude skill authoring guide.

## 1. Authoritative Sources (Official)

| Source Name | Type | URL | Capture Location | Why It Matters |
| :--- | :--- | :--- | :--- | :--- |
| Claude Code Skills Docs | Documentation | [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) | `.cache/research/claude-skills/code-claude-skills.md` | Primary reference for Claude Code-specific skill behavior, discovery, and loading. |
| Agent Skills Overview | Documentation | [platform.claude.com/.../overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | `.cache/research/claude-skills/platform-claude-agent-skills-overview.md` | Defines the "Agent Skills" open standard and progressive disclosure model. |
| Agent Skills Best Practices | Documentation | [platform.claude.com/.../best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | `.cache/research/claude-skills/platform-claude-agent-skills-best-practices.md` | Normative guidance on conciseness, freedom levels, and naming. |
| The Complete Guide (PDF) | Whitepaper | [resources.anthropic.com/.../guide.pdf](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en) | `.cache/research/claude-skills/The-Complete-Guide-to-Building-Skill-for-Claude.pdf` | Long-form authoritative guide covering planning, structure, and testing. |
| agentskills.io | Specification | [agentskills.io](https://agentskills.io) | `.cache/research/claude-skills/agentskills-io.md` | The home of the Agent Skills specification and community patterns. |
| Claude Code Sub-agents | Documentation | [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) | `.cache/research/claude-skills/code-claude-sub-agents.md` | Explains how skills interact with forked subagent contexts. |
| Claude Code Hooks | Documentation | [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) | `.cache/research/claude-skills/code-claude-hooks.md` | Details lifecycle events that can be used to enforce skill behavior. |
| Claude Code Permissions | Documentation | [code.claude.com/docs/en/permissions](https://code.claude.com/docs/en/permissions) | `.cache/research/claude-skills/code-claude-permissions.md` | Explains how `allowed-tools` and baseline permissions interact. |
| Claude Code Settings | Documentation | [code.claude.com/docs/en/settings](https://code.claude.com/docs/en/settings) | `.cache/research/claude-skills/code-claude-settings.md` | Covers global settings like `disableSkillShellExecution`. |
| Claude Blog Guide | Blog Post | [claude.com/blog/...](https://claude.com/blog/complete-guide-to-building-skills-for-claude) | `.cache/research/claude-skills/claude-blog-guide.md` | High-level overview and introduction to the authoritative PDF guide. |
| Claude Code llms.txt | Documentation | [code.claude.com/docs/llms.txt](https://code.claude.com/docs/llms.txt) | `.cache/research/claude-skills/code-claude-llms-txt.txt` | Canonical index of Claude Code documentation for LLM consumption. |
| Claude Code Commands | Documentation | [code.claude.com/docs/en/commands](https://code.claude.com/docs/en/commands) | `.cache/research/claude-skills/code-claude-commands.md` | Reference for built-in commands and bundled skills (e.g., `/batch`, `/loop`). |
| Claude Code Features | Documentation | [code.claude.com/docs/en/features-overview](https://code.claude.com/docs/en/features-overview) | `.cache/research/claude-skills/code-claude-features-overview.md` | Comparative overview of extensions (Skills vs. Hooks vs. MCP). |

## 2. Reference Implementations (External Patterns)

| Source Name | Type | URL | Capture Location | Why It Matters |
| :--- | :--- | :--- | :--- | :--- |
| anthropics/skills | Repository | [github.com/anthropics/skills](https://github.com/anthropics/skills) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` | Canonical examples of skill packaging and real-world workflows. |
| agentskills/agentskills | Repository | [github.com/agentskills/agentskills](https://github.com/agentskills/agentskills) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` | Reference implementation of the Agent Skills specification. |
| Farzapedia | Pattern | [gist.github.com/farzaa/...](https://gist.github.com/farzaa/c35ac0cfbeb957788650e36aabea836d) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` | Explicit `/wiki` command family and agent maintenance loop. |
| Karpathy LLM Wiki | Pattern | [gist.github.com/karpathy/...](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` | Simple three-layer model for compiled knowledge. |
| personal-os-skills | Repository | [github.com/ArtemXTech/...](https://github.com/ArtemXTech/personal-os-skills) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` | Concrete Claude Code skills with machine-readable schema files. |
| seCall | Repository | [github.com/hang-in/seCall](https://github.com/hang-in/seCall) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` | Vault-as-truth model and hybrid retrieval parameters. |
| qmd | Repository | [github.com/tobi/qmd](https://github.com/tobi/qmd) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` | Upstream lineage for Snowiki's retrieval and strong-signal shortcut. |

Captured on: 2026-04-18
