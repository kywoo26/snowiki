# Official Guidance Notes: Claude Skills

This document extracts authoritative guidance from official Anthropic sources regarding Claude skill authoring, discovery, and execution.
All normative statements in `docs/reference/research/claude-skill-authoring-guide.md` should trace back either to the provenance register below or to the local raw captures listed there.

## Provenance Register

| ID | Source | Type | Canonical URL | Local Capture | Accessed | Why It Matters |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| O1 | Claude Code Skills Docs | Documentation | [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) | `.cache/research/claude-skills/code-claude-skills.md` | 2026-04-18 | Primary Claude Code source for skill discovery, loading, front matter, supporting files, and invocation control. |
| O2 | Agent Skills Overview | Documentation | [platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | `.cache/research/claude-skills/platform-claude-agent-skills-overview.md` | 2026-04-18 | Defines progressive disclosure, filesystem packaging, and the staged loading model. |
| O3 | Agent Skills Best Practices | Documentation | [platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | `.cache/research/claude-skills/platform-claude-agent-skills-best-practices.md` | 2026-04-18 | Grounds naming, conciseness, degrees of freedom, and supporting-file guidance. |
| O4 | The Complete Guide (PDF) | Whitepaper | [resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en) | `.cache/research/claude-skills/The-Complete-Guide-to-Building-Skill-for-Claude.pdf` | 2026-04-18 | Long-form authoritative guide for planning, packaging, testing, and failure-mode awareness. |
| O5 | agentskills.io | Specification | [agentskills.io](https://agentskills.io) | `.cache/research/claude-skills/agentskills-io.md` | 2026-04-18 | Specification home for the Agent Skills standard that Claude Code extends. |
| O6 | Claude Code Sub-agents | Documentation | [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) | `.cache/research/claude-skills/code-claude-sub-agents.md` | 2026-04-18 | Grounds subagent routing, `context: fork`, and isolated execution patterns. |
| O7 | Claude Code Hooks | Documentation | [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) | `.cache/research/claude-skills/code-claude-hooks.md` | 2026-04-18 | Grounds skill-scoped hook usage and deterministic automation guidance. |
| O8 | Claude Code Permissions | Documentation | [code.claude.com/docs/en/permissions](https://code.claude.com/docs/en/permissions) | `.cache/research/claude-skills/code-claude-permissions.md` | 2026-04-18 | Explains how `allowed-tools` interacts with permission prompts and settings. |
| O9 | Claude Code Settings | Documentation | [code.claude.com/docs/en/settings](https://code.claude.com/docs/en/settings) | `.cache/research/claude-skills/code-claude-settings.md` | 2026-04-18 | Covers settings that materially affect skill execution and managed configuration behavior. |
| O10 | Claude Code Commands | Documentation | [code.claude.com/docs/en/commands](https://code.claude.com/docs/en/commands) | `.cache/research/claude-skills/code-claude-commands.md` | 2026-04-18 | Grounds bundled-skill examples such as `/batch`, `/loop`, and `/less-permission-prompts`. |
| O11 | Claude Code Features Overview | Documentation | [code.claude.com/docs/en/features-overview](https://code.claude.com/docs/en/features-overview) | `.cache/research/claude-skills/code-claude-features-overview.md` | 2026-04-18 | Grounds extension-selection guidance across skills, subagents, hooks, MCP, and plugins. |
| O12 | Claude Code llms.txt | Documentation Index | [code.claude.com/docs/llms.txt](https://code.claude.com/docs/llms.txt) | `.cache/research/claude-skills/code-claude-llms-txt.txt` | 2026-04-18 | Canonical index used to confirm the supporting Claude Code documentation set was captured locally. |
| O13 | Claude Blog Guide | Blog Post | [claude.com/blog/complete-guide-to-building-skills-for-claude](https://claude.com/blog/complete-guide-to-building-skills-for-claude) | `.cache/research/claude-skills/claude-blog-guide.md` | 2026-04-18 | Public framing for the longer guide and its emphasis on practical skill design and testing. |

## Progressive Disclosure Model

**Grounded in:** O1, O2, O4, O5

Agent Skills use a filesystem-based architecture to enable **progressive disclosure**, loading information in stages to preserve the context window.

- **Level 1: Metadata (Always Loaded)**: `name` and `description` from YAML front matter. Loaded at startup (~100 tokens).
- **Level 2: Instructions (Loaded when Triggered)**: The main body of `SKILL.md`. Loaded when Claude decides the skill is relevant (< 5k tokens).
- **Level 3: Resources and Code (Loaded as Needed)**: Supporting files (`.md`, `.py`, `.sh`) referenced from `SKILL.md`. Accessed via bash/code execution without loading full contents into context unless explicitly read.

## SKILL.md Frontmatter and Package Structure

**Grounded in:** O1, O5, O8

Claude Code extends the Agent Skills standard with specific fields:

| Field | Purpose |
| :--- | :--- |
| `name` | Display name and `/slash-command`. |
| `description` | Critical for discovery. Claude uses this to decide when to load the skill. |
| `argument-hint` | Optional autocomplete hint showing expected arguments, such as `[issue-number]` or `[filename] [format]`. |
| `disable-model-invocation` | Set to `true` to prevent Claude from auto-loading. Use for manual-only workflows (e.g., `/deploy`). |
| `user-invocable` | Set to `false` to hide from the `/` menu. Use for background knowledge. |
| `allowed-tools` | Pre-approves tools for the skill, bypassing per-use permission prompts. |
| `context: fork` | Runs the skill in an isolated subagent context. |
| `agent` | Specifies the subagent type (e.g., `Explore`, `Plan`) when `context: fork` is used. |
| `hooks` | Scopes lifecycle hooks to the skill. |
| `paths` | Glob patterns that limit when the skill is activated (path-specific rules). |

## Discovery and Loading Model

**Grounded in:** O1, O2, O8, O9

- **Location Priority**: Enterprise > Personal (`~/.claude/skills/`) > Project (`.claude/skills/`).
- **Nested Discovery**: Claude Code automatically discovers skills in nested `.claude/skills/` directories (e.g., in monorepos).
- **Live Detection**: Changes to skill files are picked up within the current session without restarting.
- **Compaction Behavior**: Invoked skills are carried forward during context compaction. Re-attached skills share a 25,000 token budget.

## Authoring Best Practices

**Grounded in:** O3, O4, O13

- **Conciseness**: Assume Claude is already smart. Only add context it doesn't have.
- **Degrees of Freedom**:
    - **High**: Text-based instructions for heuristic tasks (e.g., code review).
    - **Medium**: Pseudocode or scripts with parameters for preferred patterns.
    - **Low**: Specific scripts for fragile/consistent operations (e.g., migrations).
- **Naming**: Use **gerund form** (e.g., `processing-pdfs`) or noun phrases. Avoid vague names like `utils`.
- **Descriptions**: Write in **third person** (e.g., "Processes Excel files"). Include specific triggers and contexts.
- **Supporting Files**: Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files and link them directly from `SKILL.md`.

## Advanced Execution Patterns

**Grounded in:** O1, O6, O7, O8, O9, O10, O11

- **Dynamic Context Injection**: Use `` !`<command>` `` or ` ```! ` blocks to run shell commands and inject their output into the prompt *before* Claude receives it.
- **Subagent Delegation**:
    - `context: fork` makes the skill content the prompt for a subagent.
    - Subagents (like `Explore`) are optimized for specific tasks (e.g., read-only codebase analysis).
- **Hooks**: Use hooks (`PreToolUse`, `PostToolUse`, etc.) to enforce behavior or automate side effects during the skill lifecycle.
- **Permissions and Settings Boundary**: `allowed-tools` reduces prompt friction, but user or managed settings still define the outer permission envelope.
- **Bundled Skills as Patterns**: `/batch`, `/loop`, and `/less-permission-prompts` are useful official examples of prompt-based orchestration rather than direct built-in logic.

## Anti-Patterns and Failure Modes

**Grounded in:** O1, O3, O4

- **Deep Nesting**: Avoid linking files more than one level deep from `SKILL.md`. Claude may only partially read deeply nested files.
- **Vague Descriptions**: Descriptions like "Helps with documents" lead to poor discovery.
- **Over-explaining**: Don't explain basic concepts (e.g., what a PDF is) to Claude.
- **Implicit Writes**: Be cautious with skills that perform direct file writes without review, especially in knowledge-management contexts like Snowiki.

## Bundled Skills and Extension Selection

**Grounded in:** O1, O10, O11

### Bundled Skills as Reference Patterns
Claude Code includes several **bundled skills** that serve as official patterns for complex workflows:
- `/batch`: Orchestrates large-scale changes in parallel using subagents and worktrees.
- `/loop`: Runs a prompt repeatedly (proactive maintenance).
- `/debug`: Troubleshoots issues by reading session logs.
- `/claude-api`: Injects language-specific API reference material.
- `/less-permission-prompts`: Scans transcripts to auto-generate an allowlist for settings.

### When to Use a Skill (vs. Other Extensions)
Official guidance suggests a hierarchy for extending Claude Code:
1. **CLAUDE.md**: For project-wide conventions and "always do X" rules.
2. **Skill**: For reusable knowledge, reference docs, and repeatable multi-step workflows.
3. **Subagent**: For context isolation and specialized workers (often triggered by a skill).
4. **Hook**: For deterministic, non-LLM automation (e.g., running a linter after an edit).
5. **MCP**: For connecting to external services and live data.
6. **Plugin**: For packaging and distributing any of the above.

