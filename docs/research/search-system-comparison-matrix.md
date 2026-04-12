# Search System Comparison Matrix

## Purpose

This document captures the most relevant external comparison set for Snowiki.

It is not meant to be a broad survey of RAG tools. It exists to answer a narrower question:

> Which systems are strategically useful reference points for a provenance-aware, compiled, local-first, agent-friendly knowledge engine?

## Evidence note

This matrix is built from a combination of:
- repository-level source inspection where available
- visible release/activity signals
- project documentation and positioning
- the source appendix below, which records the concrete public artifacts used for comparison

It is intended to be **decision-useful**, not academically complete.

That means:
- trust / production signals are comparative rather than absolute
- evaluation-discipline notes are included only where they are visible enough to matter
- systems are judged primarily by strategic relevance to Snowiki, not by raw popularity

Where a judgment is interpretive rather than strongly evidenced from a visible artifact, it should be read as a design recommendation rather than a factual guarantee.

## Comparison dimensions

The comparison should stay stable across future revisions. These are the main dimensions that matter:

1. **Canonical artifact**
   - compiled wiki / maintained knowledge artifact
   - query-time retrieval output
   - memory layer only

2. **Retrieval substrate**
   - lexical
   - hybrid lexical+dense
   - graph-assisted
   - workflow-mediated search

3. **Provenance / epistemic integrity**
   - whether the system treats source traceability as a first-class concern

4. **Agent ergonomics**
   - machine-usable interfaces
   - composable retrieval primitives
   - local-first / deterministic bias

5. **Evaluation discipline**
   - whether the system exposes real benchmark/evaluation posture or only product claims

6. **Operational posture**
   - local-first
   - self-hostable
   - production-ready vs mostly experimental

## Direct peers Snowiki should study closely

These are the systems that are strategically closest to Snowiki’s actual direction.

### `xoai/sage-wiki`
- **What it is**: self-improving wiki maintenance system
- **Why it matters**: closest visible example of a system treating the maintained wiki artifact itself as the product
- **Trust / production signal**: active OSS project with releases and self-hostable posture
- **Similarity to Snowiki**: **High**
- **Evaluation discipline**: meaningful enough to matter; more explicit evaluation than most “wiki” projects
- **What Snowiki should learn**: inherit the maintenance-first posture; do not let retrieval quality be the only measure of progress
- **Evidence basis**: visible self-description and wiki-maintenance orientation

### `hang-in/seCall`
- **What it is**: local-first session/vault search and provenance-oriented workflow system
- **Why it matters**: closest sibling for source/session seriousness, vault workflow, and provenance-aware behavior
- **Trust / production signal**: real OSS workflow system with local-first operational intent
- **Similarity to Snowiki**: **High**
- **Evaluation discipline**: stronger workflow/structural discipline than explicit benchmark discipline
- **What Snowiki should learn**: inherit workflow seriousness and provenance-first thinking; avoid overfitting the product to one session shape
- **Evidence basis**: visible local-first workflow posture and source/session emphasis

### `kenforthewin/atomic`
- **What it is**: atomic knowledge representation and linked knowledge workflow system
- **Why it matters**: useful reference for how knowledge units and relationships can become the center of the product
- **Trust / production signal**: mature-looking OSS/product posture
- **Similarity to Snowiki**: **High**
- **Evaluation discipline**: weaker benchmark posture, stronger representational clarity
- **What Snowiki should learn**: inherit representation discipline; avoid unnecessary product-surface sprawl early
- **Evidence basis**: visible focus on atomic knowledge representation and linked knowledge workflows

### `nashsu/llm_wiki`
- **What it is**: an implementation descendant of the llm-wiki idea
- **Why it matters**: direct conceptual lineage for “LLM-maintained wiki” thinking
- **Trust / production signal**: useful implementation lineage, though not as strong in benchmark posture as some production systems
- **Similarity to Snowiki**: **High**
- **Evaluation discipline**: relatively weak; more philosophical/implementation lineage than rigorous evidence system
- **What Snowiki should learn**: inherit the compiled-wiki thesis; avoid leaving provenance and evaluation underspecified
- **Evidence basis**: direct lineage to the llm-wiki idea and visible implementation focus on generated wiki artifacts

### `khoj-ai/khoj`
- **What it is**: local-first search / second-brain / assistant product
- **Why it matters**: useful product-quality contrast for local-first search and agent-facing ergonomics
- **Trust / production signal**: strong adoption, releases, and real product maturity
- **Similarity to Snowiki**: **Medium-High**
- **Evaluation discipline**: notably stronger than many OSS note/search tools
- **What Snowiki should learn**: inherit local-first/agent ergonomics discipline; avoid drifting into a generic assistant product
- **Evidence basis**: visible local-first search product posture and stronger operational maturity than most note-search tools

## Important adjacent systems

These are not as strategically similar, but they are still useful reference points.

### `qmd`
- **What it is**: local retrieval/search substrate
- **Why it matters**: one of Snowiki’s clearest substrate references
- **Trust / production signal**: strong OSS substrate signal
- **Similarity to Snowiki**: **Medium**
- **Evaluation discipline**: solid retrieval discipline, but not the full product model Snowiki needs
- **What Snowiki should learn**: inherit lexical-first, local-first, strategy-aware retrieval; avoid becoming “just search”
- **Evidence basis**: explicit retrieval-substrate orientation and local-first search design

### `Onyx`
- **What it is**: enterprise retrieval platform
- **Why it matters**: useful for contrast on retrieval orchestration and connector-heavy production posture
- **Trust / production signal**: strong production/enterprise signal
- **Similarity to Snowiki**: **Medium-Low**
- **Evaluation discipline**: stronger product/ops signal than artifact-centric knowledge design
- **What Snowiki should learn**: inherit rigor where useful; avoid enterprise sprawl
- **Evidence basis**: visible production/connector posture and retrieval platform framing

### `RAGFlow`
- **What it is**: workflow-heavy RAG/document pipeline system
- **Why it matters**: useful contrast for ingestion/pipeline-heavy document systems
- **Trust / production signal**: strong visibility and product-like posture
- **Similarity to Snowiki**: **Low-Medium**
- **Evaluation discipline**: more pipeline/product oriented than Snowiki’s intended artifact-centric direction
- **What Snowiki should learn**: inherit pipeline rigor where useful; avoid becoming a generic RAG workflow tool
- **Evidence basis**: visible workflow-heavy document/RAG pipeline orientation

### `mem0`
- **What it is**: agent memory layer
- **Why it matters**: useful negative control when distinguishing memory systems from compiled knowledge systems
- **Trust / production signal**: high visibility, strong product signal
- **Similarity to Snowiki**: **Low**
- **Evaluation discipline**: useful memory-oriented evidence posture, but on a different product axis
- **What Snowiki should learn**: be clear that memory != compiled wiki/knowledge artifact
- **Evidence basis**: explicit memory-layer/product framing rather than compiled knowledge artifact posture

## Shortlist summary

### Top direct comparison candidates
1. `xoai/sage-wiki`
2. `hang-in/seCall`
3. `kenforthewin/atomic`
4. `nashsu/llm_wiki`
5. `khoj-ai/khoj`

### Popular but strategically less similar
- `mem0`
- `RAGFlow`
- `Onyx`
- `qmd` (critical lineage/reference, but more substrate than product peer)

## Main takeaway

Snowiki should compare itself primarily to **persistent knowledge systems** with a maintained artifact, provenance discipline, and local-first usability — not to generic chat-with-docs or memory products.

If a system is strong at retrieval but weak on compiled artifact maintenance, provenance, or agent-friendly local operation, it should be treated as a contrast reference rather than a product peer.

## Evidence appendix

These judgments were formed from concrete public-facing signals rather than from popularity alone.

Reviewed as of: 2026-04-12

### Direct peers — evidence basis
- `xoai/sage-wiki`
  - URL: https://github.com/xoai/sage-wiki
  - Inspected artifacts: repository landing page / README-level positioning
  - Supports: wiki-maintenance posture, artifact-centric framing, visible OSS maturity signal
- `hang-in/seCall`
  - URL: https://github.com/hang-in/seCall
  - Inspected artifacts: repository landing page / workflow-oriented positioning
  - Supports: local-first workflow framing, session/source seriousness, provenance-aware sibling comparison
- `kenforthewin/atomic`
  - URL: https://github.com/kenforthewin/atomic
  - Inspected artifacts: repository landing page / atomic knowledge representation framing
  - Supports: strong knowledge-unit representation comparison and linked-knowledge orientation
- `nashsu/llm_wiki`
  - URL: https://github.com/nashsu/llm_wiki
  - Inspected artifacts: repository landing page / llm-wiki lineage framing
  - Supports: direct conceptual lineage to the llm-wiki idea and generated wiki artifact orientation
- `khoj-ai/khoj`
  - URL: https://github.com/khoj-ai/khoj
  - Inspected artifacts: repository landing page / product posture / release maturity signals
  - Supports: local-first search product ergonomics, stronger operational maturity, assistant-style contrast

### Adjacent systems — evidence basis
- `qmd`
  - URL: https://github.com/tobi/qmd
  - Inspected artifacts: repository positioning / local retrieval-substrate framing
  - Supports: lexical-first, local-first substrate comparison rather than full product identity
- `Onyx`
  - URL: https://github.com/onyx-dot-app/onyx
  - Inspected artifacts: public product/repo posture
  - Supports: enterprise retrieval-platform contrast and stronger ops/product framing
- `RAGFlow`
  - URL: https://github.com/infiniflow/ragflow
  - Inspected artifacts: public workflow/pipeline-oriented RAG framing
  - Supports: ingestion/pipeline-heavy contrast rather than compiled-knowledge equivalence
- `mem0`
  - URL: https://github.com/mem0ai/mem0
  - Inspected artifacts: public memory-layer/product framing
  - Supports: negative-control comparison between memory systems and compiled knowledge engines

## Traceability: evidence → conclusion → roadmap consequence

### Persistent artifact systems should be the primary peers
- Evidence: `sage-wiki`, `seCall`, `atomic`, and `llm_wiki` all present themselves around maintained artifacts / workflow / durable knowledge structures, not generic document chat.
- Conclusion: Snowiki’s direct peers are persistent knowledge systems, not generic RAG apps.
- Roadmap consequence: comparison and future plans should prioritize artifact/provenance/maintenance questions first.

### qmd matters as substrate, not as product identity
- Evidence: qmd is publicly framed as a local retrieval/search substrate rather than a full provenance-aware knowledge system.
- Conclusion: Snowiki should inherit qmd’s retrieval discipline, not collapse into qmd’s product scope.
- Roadmap consequence: lexical/hybrid discipline is relevant now; product identity decisions belong elsewhere.

### Popularity alone is not enough for comparison value
- Evidence: systems like `mem0` and `RAGFlow` have strong visibility but differ substantially in artifact model and product posture.
- Conclusion: high-visibility repos may still be low strategic-similarity references.
- Roadmap consequence: they should remain contrast references, not direct templates.

### How to read this appendix
- These references are sufficient for strategic comparison and roadmap sequencing.
- They are not intended as immutable factual rankings.
- If a future architecture decision depends heavily on one candidate, that candidate should get a dedicated deeper source review at that time.
