# Claude Skill Authoring Guide

This guide synthesizes authoritative guidance and community patterns for building high quality Claude skills. It serves as a durable reference for Snowiki development. This guide does not finalize Snowiki `/wiki` route design. This guide does not edit current skill package files.
Normative statements below are grounded in `docs/roadmap/external/claude-skills/official-guidance-notes.md` and indexed in `docs/roadmap/external/claude-skills/SOURCE-INDEX.md`. Non-normative packaging and workflow patterns trace to `docs/roadmap/external/claude-skills/reference-implementations-notes.md`.

## What a Claude skill is

A Claude skill is a packaged set of instructions, tools, and resources that extends Claude's capabilities within a specific domain. It uses a filesystem based architecture to enable progressive disclosure. This means Claude only loads the information it needs when it needs it, which preserves the context window.

Official guidance defines three levels of disclosure:
1. **Metadata**: The name and description from the YAML front matter. Claude loads this at startup to understand what skills are available.
2. **Instructions**: The main body of the `SKILL.md` file. Claude loads this when it decides the skill is relevant to the user's request.
3. **Resources**: Supporting files like scripts or reference documents. Claude accesses these as needed during execution.

## SKILL.md front matter reference

The `SKILL.md` file must start with a YAML front matter block. Claude Code uses these fields to manage discovery and execution.

| Field | Description |
| :--- | :--- |
| `name` | The display name and the slash command used to trigger the skill. |
| `description` | A third person summary of what the skill does. This is the most important field for discovery. |
| `argument-hint` | Optional text shown in the UI to help users provide the right arguments. |
| `allowed-tools` | A list of tools the skill can use without asking for permission every time. |
| `user-invocable` | Set to `false` to hide the skill from the slash menu. Useful for background knowledge. |
| `disable-model-invocation` | Set to `true` to prevent Claude from auto loading the skill based on the description. |
| `context: fork` | Runs the skill in an isolated subagent context to protect the main session. |
| `agent` | Specifies the type of subagent (like `Explore` or `Plan`) when using `context: fork`. |
| `hooks` | Scopes specific lifecycle hooks to the skill. |
| `paths` | Glob patterns that restrict the skill to specific directories or files. |

## How Claude discovers and loads skills

Claude Code looks for skills in several locations. It prioritizes enterprise skills, then personal skills in `~/.claude/skills/`, and finally project skills in `.claude/skills/`.

The discovery process is automatic. Claude scans these directories for `SKILL.md` files and reads their metadata. If you change a skill file, Claude picks up the changes immediately without needing a restart.

When a skill is triggered, Claude loads the full instructions. If the skill is part of a long session, it stays in the context during compaction. Re-attached skills share a 25,000 token budget to ensure they don't overwhelm the model.

## How to structure excellent skill packages

Excellent skills follow a modular structure. Keep the `SKILL.md` file focused on high level orchestration and move details to supporting files.

### Package Layout
A standard package often includes:
- `SKILL.md`: The entry point and core instructions.
- `workflows/`: Detailed step by step guides for complex tasks.
- `scripts/`: Executable code for deterministic operations.
- `docs/` or `reference/`: Static information and API definitions.

### Writing Instructions
Write instructions that assume Claude is already capable. Don't explain basic concepts. Focus on the specific patterns, constraints, and workflows unique to your project. Use clear headings and lists to organize the content.

## Workflow design patterns

Patterns from official sources and community references like Farzapedia and Karpathy's LLM Wiki suggest several effective designs.

### Routing and Delegation
Use a central dispatcher in `SKILL.md` to route requests to specific sub-workflows. This keeps the main instructions clean. For complex or risky tasks, use `context: fork` to delegate work to a subagent. This isolates the execution and prevents the subagent from polluting the main session's history.

### The Maintenance Loop
For knowledge management, follow an ingest, absorb, cleanup, and query loop. This ensures information is properly processed before it's used.

### Reviewable Writes
Avoid skills that write to files without user oversight. Use a preview and apply pattern. The skill generates a proposal, the user reviews it, and then a separate command applies the changes. This is a core requirement for Snowiki to maintain durable knowledge.

## Evaluation-first skill development

Build skills with testing in mind. Start by defining the expected outcome and the failure modes you want to avoid.

1. **Define Success**: What should the user see? What side effects are expected?
2. **Create Benchmarks**: Use a set of standard prompts to test the skill's discovery and execution.
3. **Iterate on Descriptions**: If Claude doesn't trigger the skill when it should, refine the description to be more specific about the triggers.
4. **Monitor Permissions**: Use the `/less-permission-prompts` skill to see which tools are being used and update `allowed-tools` to reduce friction.

## Anti-patterns and failure modes

Avoid these common mistakes to ensure your skills remain reliable.

- **Vague Descriptions**: "Helps with files" is too broad. Use "Processes PDF documents for data extraction" instead.
- **Deep Nesting**: Don't link files more than one level deep from `SKILL.md`. Claude might lose track of the context.
- **Over-explaining**: Don't waste tokens explaining things Claude already knows from its training data.
- **Implicit Writes**: Never allow a skill to modify critical files without a review step.
- **Ignoring Hooks**: Failing to use hooks for deterministic checks (like linting) can lead to broken code.

## Snowiki-specific constraints and non-goals

Snowiki has specific requirements that influence skill design.

- **CLI Truth First**: The skill must mirror the installed `snowiki` CLI. It should not invent new backend logic.
- **Reviewable Writes**: All mutations must flow through the `fileback preview` and `fileback apply` path.
- **Lexical Retrieval**: The current runtime uses lexical search. Don't assume hybrid or semantic search is available unless the CLI exposes it.
- **Read-only MCP**: The current MCP implementation is read-only. Skills should not attempt to write via MCP.
- **Non-goal**: This guide does not finalize Snowiki `/wiki` route design.
- **Non-goal**: This guide does not edit current skill package files.

## Source interpretation rule

- **Authoritative first**: official Anthropic and Claude Code documents define the normative baseline for skill behavior. Local durable note path: `docs/roadmap/external/claude-skills/official-guidance-notes.md`.
- **External pattern references**: community repos and wiki-like implementations are useful patterns, not product truth. Local durable note path: `docs/roadmap/external/claude-skills/reference-implementations-notes.md`.
- **Master provenance index**: use `docs/roadmap/external/claude-skills/SOURCE-INDEX.md` to navigate from this guide back to canonical URLs and local captured materials.

## Source index

These sources provided the authoritative facts and patterns for this guide.

### Local navigation anchors
- Master source index: `docs/roadmap/external/claude-skills/SOURCE-INDEX.md`
- Official guidance notes: `docs/roadmap/external/claude-skills/official-guidance-notes.md`
- Reference implementation notes: `docs/roadmap/external/claude-skills/reference-implementations-notes.md`

### Authoritative sources

| Source | Canonical URL | Local durable note path | Local raw capture |
| :--- | :--- | :--- | :--- |
| Claude Code Skills Docs | [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-skills.md` |
| Agent Skills Overview | [platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/platform-claude-agent-skills-overview.md` |
| Agent Skills Best Practices | [platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/platform-claude-agent-skills-best-practices.md` |
| The Complete Guide (PDF) | [resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/The-Complete-Guide-to-Building-Skill-for-Claude.pdf` |
| agentskills.io | [agentskills.io](https://agentskills.io) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/agentskills-io.md` |
| Claude Code Sub-agents | [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-sub-agents.md` |
| Claude Code Hooks | [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-hooks.md` |
| Claude Code Permissions | [code.claude.com/docs/en/permissions](https://code.claude.com/docs/en/permissions) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-permissions.md` |
| Claude Code Settings | [code.claude.com/docs/en/settings](https://code.claude.com/docs/en/settings) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-settings.md` |
| Claude Blog Guide | [claude.com/blog/complete-guide-to-building-skills-for-claude](https://claude.com/blog/complete-guide-to-building-skills-for-claude) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/claude-blog-guide.md` |
| Claude Code llms.txt | [code.claude.com/docs/llms.txt](https://code.claude.com/docs/llms.txt) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-llms-txt.txt` |
| Claude Code Commands | [code.claude.com/docs/en/commands](https://code.claude.com/docs/en/commands) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-commands.md` |
| Claude Code Features Overview | [code.claude.com/docs/en/features-overview](https://code.claude.com/docs/en/features-overview) | `docs/roadmap/external/claude-skills/official-guidance-notes.md` | `.cache/research/claude-skills/code-claude-features-overview.md` |

### Pattern references

| Source | Canonical URL | Local durable note path |
| :--- | :--- | :--- |
| anthropics/skills | [github.com/anthropics/skills](https://github.com/anthropics/skills) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |
| agentskills/agentskills | [github.com/agentskills/agentskills](https://github.com/agentskills/agentskills) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |
| Claude Skills Cookbook | [platform.claude.com/cookbook/skills-notebooks-01-skills-introduction](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |
| Farzapedia Pattern | [gist.github.com/farzaa/c35ac0cfbeb957788650e36aabea836d](https://gist.github.com/farzaa/c35ac0cfbeb957788650e36aabea836d) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |
| Karpathy LLM Wiki | [gist.github.com/karpathy/442a6bf555914893e9891c11519de94f](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |
| personal-os-skills | [github.com/ArtemXTech/personal-os-skills](https://github.com/ArtemXTech/personal-os-skills) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |
| seCall | [github.com/hang-in/seCall](https://github.com/hang-in/seCall) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |
| qmd | [github.com/tobi/qmd](https://github.com/tobi/qmd) | `docs/roadmap/external/claude-skills/reference-implementations-notes.md` |

