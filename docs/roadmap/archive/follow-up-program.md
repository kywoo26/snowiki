# Follow-up Program

## Purpose

This document turns the architecture and research conclusions into an explicit ordered sequence of next big tasks.

It is more concrete than the former root roadmap (now `docs/archive/root-roadmap.md`), but broader than a single execution plan.

## Recently completed work

- canonical retrieval service hardening
- first retrieval performance deep dive
- manual benchmark workflow ergonomics

These no longer belong in the "next work" queue except as background context for later tasks.

## Ordered next work

### 1. Korean and mixed-language lexical benchmark
Reason:
- Korean retrieval is still an open lexical/tokenization question
- lexical strategy should be exhausted before semantic escalation

Non-goals:
- vector multilingual retrieval
- mandatory Kiwi adoption without evidence

### 2. Skill contract and agent interface design
Reason:
- the current install/use contract is now aligned, but the skill layer still needs first-class design work rather than patch-level cleanup
- agent-facing contracts should be designed deliberately, not left as accumulated workflow text

Non-goals:
- rewriting the whole product around skills
- reintroducing qmd-oriented runtime claims as present truth

### 3. Search architecture hardening (next layer)
Reason:
- now that the retrieval contract is canonical, the next architecture work should target boundary clarity between tokenization, indexing, evidence surfaces, and future extension seams

Non-goals:
- semantic/vector implementation
- backend replacement

### 4. Semantic / hybrid retrieval exploration
Reason:
- lexical-first remains the correct default, but semantic/hybrid work will eventually need explicit experiments and gating

Non-goals:
- making semantic retrieval the default runtime path prematurely
- backend swap by implication

## What not to do yet

- semantic/hybrid runtime implementation
- backend replacement
- local model lifecycle integration
- broad benchmark-system expansion
- treating old qmd-oriented workflow text as the product truth

## How to choose what comes next

Pick the next item by asking:
1. What blocks the most other work?
2. What reduces drift the most?
3. What improves evidence quality the most?
4. What expands capability without invalidating current assumptions?

By those criteria, Korean/mixed-language lexical evaluation is the strongest next move, followed by deeper skill/agent-interface design and then the next layer of retrieval architecture hardening.
