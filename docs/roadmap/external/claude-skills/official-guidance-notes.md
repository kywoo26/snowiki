# Official Guidance Notes: Claude Skills

This document extracts authoritative guidance from official Anthropic sources regarding Claude skill authoring, discovery, and execution.

## 1. Core Architecture: Progressive Disclosure

Agent Skills use a filesystem-based architecture to enable **progressive disclosure**, loading information in stages to preserve the context window.

- **Level 1: Metadata (Always Loaded)**: `name` and `description` from YAML frontmatter. Loaded at startup (~100 tokens).
- **Level 2: Instructions (Loaded when Triggered)**: The main body of `SKILL.md`. Loaded when Claude decides the skill is relevant (< 5k tokens).
- **Level 3: Resources and Code (Loaded as Needed)**: Supporting files (`.md`, `.py`, `.sh`) referenced from `SKILL.md`. Accessed via bash/code execution without loading full contents into context unless explicitly read.

## 2. SKILL.md Frontmatter Reference (Claude Code Specifics)

Claude Code extends the Agent Skills standard with specific fields:

| Field | Purpose |
| :--- | :--- |
| `name` | Display name and `/slash-command`. |
| `description` | Critical for discovery. Claude uses this to decide when to load the skill. |
| `disable-model-invocation` | Set to `true` to prevent Claude from auto-loading. Use for manual-only workflows (e.g., `/deploy`). |
| `user-invocable` | Set to `false` to hide from the `/` menu. Use for background knowledge. |
| `allowed-tools` | Pre-approves tools for the skill, bypassing per-use permission prompts. |
| `context: fork` | Runs the skill in an isolated subagent context. |
| `agent` | Specifies the subagent type (e.g., `Explore`, `Plan`) when `context: fork` is used. |
| `hooks` | Scopes lifecycle hooks to the skill. |
| `paths` | Glob patterns that limit when the skill is activated (path-specific rules). |

## 3. Discovery and Loading Model

- **Location Priority**: Enterprise > Personal (`~/.claude/skills/`) > Project (`.claude/skills/`).
- **Nested Discovery**: Claude Code automatically discovers skills in nested `.claude/skills/` directories (e.g., in monorepos).
- **Live Detection**: Changes to skill files are picked up within the current session without restarting.
- **Compaction Behavior**: Invoked skills are carried forward during context compaction. Re-attached skills share a 25,000 token budget.

## 4. Authoring Best Practices

- **Conciseness**: Assume Claude is already smart. Only add context it doesn't have.
- **Degrees of Freedom**:
    - **High**: Text-based instructions for heuristic tasks (e.g., code review).
    - **Medium**: Pseudocode or scripts with parameters for preferred patterns.
    - **Low**: Specific scripts for fragile/consistent operations (e.g., migrations).
- **Naming**: Use **gerund form** (e.g., `processing-pdfs`) or noun phrases. Avoid vague names like `utils`.
- **Descriptions**: Write in **third person** (e.g., "Processes Excel files"). Include specific triggers and contexts.
- **Supporting Files**: Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files and link them directly from `SKILL.md`.

## 5. Advanced Execution Patterns

- **Dynamic Context Injection**: Use `` !`<command>` `` or ` ```! ` blocks to run shell commands and inject their output into the prompt *before* Claude receives it.
- **Subagent Delegation**:
    - `context: fork` makes the skill content the prompt for a subagent.
    - Subagents (like `Explore`) are optimized for specific tasks (e.g., read-only codebase analysis).
- **Hooks**: Use hooks (`PreToolUse`, `PostToolUse`, etc.) to enforce behavior or automate side effects during the skill lifecycle.

## 6. Anti-Patterns and Failure Modes

- **Deep Nesting**: Avoid linking files more than one level deep from `SKILL.md`. Claude may only partially read deeply nested files.
- **Vague Descriptions**: Descriptions like "Helps with documents" lead to poor discovery.
- **Over-explaining**: Don't explain basic concepts (e.g., what a PDF is) to Claude.
- **Implicit Writes**: Be cautious with skills that perform direct file writes without review, especially in knowledge-management contexts like Snowiki.
