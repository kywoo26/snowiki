# Extend Claude Code

> Understand when to use CLAUDE.md, Skills, subagents, hooks, MCP, and plugins.

Claude Code combines a model that reasons about your code with [built-in tools](/en/how-claude-code-works#tools) for file operations, search, execution, and web access. The built-in tools cover most coding tasks. This guide covers the extension layer: features you add to customize what Claude knows, connect it to external services, and automate workflows.

<Note>
  For how the core agentic loop works, see [How Claude Code works](/en/how-claude-code-works).
</Note>

**New to Claude Code?** Start with [CLAUDE.md](/en/memory) for project conventions, then add other extensions [as specific triggers come up](#build-your-setup-over-time).

## Overview

Extensions plug into different parts of the agentic loop:

* **[CLAUDE.md](/en/memory)** adds persistent context Claude sees every session
* **[Skills](/en/skills)** add reusable knowledge and invocable workflows
* **[MCP](/en/mcp)** connects Claude to external services and tools
* **[Subagents](/en/sub-agents)** run their own loops in isolated context, returning summaries
* **[Agent teams](/en/agent-teams)** coordinate multiple independent sessions with shared tasks and peer-to-peer messaging
* **[Hooks](/en/hooks)** run outside the loop entirely as deterministic scripts
* **[Plugins](/en/plugins)** and **[marketplaces](/en/plugin-marketplaces)** package and distribute these features

[Skills](/en/skills) are the most flexible extension. A skill is a markdown file containing knowledge, workflows, or instructions. You can invoke skills with a command like `/deploy`, or Claude can load them automatically when relevant. Skills can run in your current conversation or in an isolated context via subagents.

## Match features to your goal

Features range from always-on context that Claude sees every session, to on-demand capabilities you or Claude can invoke, to background automation that runs on specific events. The table below shows what's available and when each one makes sense.

| Feature                            | What it does                                               | When to use it                                                                  | Example                                                                         |
| ---------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **CLAUDE.md**                      | Persistent context loaded every conversation               | Project conventions, "always do X" rules                                        | "Use pnpm, not npm. Run tests before committing."                               |
| **Skill**                          | Instructions, knowledge, and workflows Claude can use      | Reusable content, reference docs, repeatable tasks                              | `/deploy` runs your deployment checklist; API docs skill with endpoint patterns |
| **Subagent**                       | Isolated execution context that returns summarized results | Context isolation, parallel tasks, specialized workers                          | Research task that reads many files but returns only key findings               |
| **[Agent teams](/en/agent-teams)** | Coordinate multiple independent Claude Code sessions       | Parallel research, new feature development, debugging with competing hypotheses | Spawn reviewers to check security, performance, and tests simultaneously        |
| **MCP**                            | Connect to external services                               | External data or actions                                                        | Query your database, post to Slack, control a browser                           |
| **Hook**                           | Deterministic script that runs on events                   | Predictable automation, no LLM involved                                         | Run ESLint after every file edit                                                |

**[Plugins](/en/plugins)** are the packaging layer. A plugin bundles skills, hooks, subagents, and MCP servers into a single installable unit. Plugin skills are namespaced (like `/my-plugin:review`) so multiple plugins can coexist. Use plugins when you want to reuse the same setup across multiple repositories or distribute to others via a **[marketplace](/en/plugin-marketplaces)**.

### Build your setup over time

You don't need to configure everything up front. Each feature has a recognizable trigger, and most teams add them in roughly this order:

| Trigger                                                                          | Add                                             |
| :------------------------------------------------------------------------------- | :---------------------------------------------- |
| Claude gets a convention or command wrong twice                                  | Add it to [CLAUDE.md](/en/memory)               |
| You keep typing the same prompt to start a task                                  | Save it as a user-invocable [skill](/en/skills) |
| You paste the same playbook or multi-step procedure into chat for the third time | Capture it as a [skill](/en/skills)             |
| You keep copying data from a browser tab Claude can't see                        | Connect that system as an [MCP server](/en/mcp) |
| A side task floods your conversation with output you won't reference again       | Route it through a [subagent](/en/sub-agents)   |
| You want something to happen every time without asking                           | Write a [hook](/en/hooks-guide)                 |
| A second repository needs the same setup                                         | Package it as a [plugin](/en/plugins)           |

The same triggers tell you when to update what you already have. A repeated mistake or a recurring review comment is a CLAUDE.md edit, not a one-off correction in chat. a workflow you keep tweaking by hand is a skill that needs another revision.
