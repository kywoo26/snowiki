---
name: wiki
description: Maintain a persistent LLM wiki that compounds knowledge like a snowball. Ingest sources into structured wiki pages, query compiled knowledge, lint for health. Use when user says "wiki ingest", "wiki query", "wiki lint", "add to wiki", "search wiki", "check wiki health", "ingest this", "file this".
argument-hint: [ingest SOURCE|query QUESTION|lint|status]
allowed-tools: Bash(python3:*), Bash(qmd:*), Read, Write, Edit, Glob, Grep, WebFetch, mcp__plugin_qmd_qmd__query, mcp__plugin_qmd_qmd__get
---

# Snowiki — LLM Wiki Skill

A personal wiki that compounds knowledge like a snowball. Sources go in, the LLM integrates them into a persistent, interlinked wiki. Every source makes the wiki richer.

## Core Principle

- **Human**: curates sources, asks questions, directs analysis, thinks
- **LLM**: summarizes, cross-references, files, maintains consistency — all the bookkeeping humans abandon
- **sources/**: immutable raw material (never modified)
- **wiki/**: LLM-owned compiled knowledge (created, updated, cross-linked)

## Modes

### /wiki ingest <source>
Process a new source and integrate it into the wiki. Source can be a URL, file path, or inline text.

### /wiki query <question>
Search the wiki, synthesize an answer with citations. Good answers can be filed back as new pages.

### /wiki lint
Health-check: orphan pages, broken links, missing frontmatter, contradictions, stale content.

### /wiki status
Overview: page counts by type, source counts, last activity, qmd index state.

## Workflow

See `workflows/wiki.md` for detailed routing and step-by-step process.
