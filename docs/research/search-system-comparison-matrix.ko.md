# Search 시스템 비교 매트릭스

## 목적

이 문서는 Snowiki와 비교할 만한 외부 시스템을 정리합니다.

이건 broad RAG survey가 아니라, 다음 질문에 답하기 위한 문서입니다.

> provenance-aware, compiled, local-first, agent-friendly knowledge engine인 Snowiki와 전략적으로 비교할 가치가 있는 시스템은 무엇인가?

## evidence note

이 매트릭스는 다음을 조합해 만든 decision-oriented 문서입니다.
- 가능한 경우 repository-level source inspection
- visible release / activity signal
- project documentation 및 positioning
- 아래 evidence appendix에 기록한 concrete public artifacts

즉 학술적으로 완전한 survey가 아니라, **의사결정 가능한 비교 자료**입니다.

따라서:
- trust / production signal은 절대 평가가 아니라 비교 평가에 가깝고
- evaluation-discipline은 충분히 visible할 때만 적으며
- strategic relevance가 raw popularity보다 우선합니다.

강한 artifact에서 직접 나온 판단이 아닌 경우, 그 항목은 “사실”이라기보다 design recommendation으로 읽어야 합니다.

## 비교 축
1. canonical artifact (compiled wiki / query-time output / memory layer)
2. retrieval substrate (lexical / hybrid / graph / workflow-mediated)
3. provenance / epistemic integrity
4. agent ergonomics
5. evaluation / benchmark discipline
6. local-first / operational posture

## direct peer

### `xoai/sage-wiki`
- self-improving wiki maintenance system
- maintained wiki artifact 자체를 product로 본다는 점에서 Snowiki와 가장 가까움
- trust signal: active OSS, release/self-host posture
- similarity: **High**
- evaluation discipline: 다른 wiki 계열보다 비교적 명시적
- Snowiki가 배울 것: maintenance-first posture
- evidence basis: visible self-description과 wiki-maintenance orientation

### `hang-in/seCall`
- local-first session/vault search + provenance-oriented workflow
- source/session seriousness와 local workflow에서 가장 가까운 sibling
- trust signal: real OSS workflow system
- similarity: **High**
- evaluation discipline: benchmark보단 workflow/structural discipline이 강함
- Snowiki가 배울 것: provenance-first workflow seriousness
- evidence basis: visible local-first workflow posture와 source/session emphasis

### `kenforthewin/atomic`
- atomic knowledge representation and linked workflow
- knowledge representation 설계 참고 가치가 큼
- trust signal: mature-looking OSS/product posture
- similarity: **High**
- evaluation discipline: benchmark는 약하지만 representation clarity는 강함
- Snowiki가 배울 것: representation discipline
- evidence basis: visible focus on atomic knowledge representation과 linked knowledge workflows

### `nashsu/llm_wiki`
- llm-wiki idea의 구현 descendant
- Snowiki 철학적 lineage에서 중요
- trust signal: implementation lineage로서 가치 있음
- similarity: **High**
- evaluation discipline: 상대적으로 약함
- Snowiki가 배울 것: compiled-wiki thesis, 단 provenance/evaluation은 더 강하게 가져가야 함
- evidence basis: llm-wiki idea에 직접 연결된 lineage와 generated wiki artifact 구현 방향

### `khoj-ai/khoj`
- local-first search / second-brain / assistant product
- local-first search product ergonomics 비교용으로 중요
- trust signal: strong adoption, release, product maturity
- similarity: **Medium-High**
- evaluation discipline: note/search tool 중에서는 강한 편
- Snowiki가 배울 것: local-first/agent ergonomics discipline
- evidence basis: visible local-first search product posture와 stronger operational maturity

## 인접하지만 덜 유사한 시스템

### `qmd`
- local retrieval/search substrate
- Snowiki retrieval lineage reference로 중요
- trust signal: strong OSS substrate
- similarity: **Medium**
- evaluation discipline: retrieval discipline은 좋지만 full product model은 아님
- Snowiki가 배울 것: lexical-first, local-first, strategy-aware retrieval
- evidence basis: explicit retrieval-substrate positioning과 local search emphasis

### `Onyx`
- enterprise retrieval platform
- orchestration / connector / ops contrast 용도
- trust signal: strong production/enterprise signal
- similarity: **Medium-Low**
- evaluation discipline: product/ops signal은 강함
- Snowiki가 배울 것: rigor는 취하되 enterprise sprawl은 피하기
- evidence basis: visible production/connector posture와 retrieval platform framing

### `RAGFlow`
- workflow-heavy RAG/document pipeline
- ingestion/pipeline-heavy product contrast
- trust signal: 높은 visibility
- similarity: **Low-Medium**
- evaluation discipline: pipeline/product 쪽에 더 가깝다
- Snowiki가 배울 것: pipeline rigor는 참고, generic RAG workflow tool로 drift하지 말 것
- evidence basis: visible workflow-heavy document/RAG pipeline orientation

### `mem0`
- agent memory layer
- memory와 compiled knowledge를 구분하기 위한 negative control
- trust signal: 높은 visibility와 product signal
- similarity: **Low**
- evaluation discipline: memory utility 쪽 근거는 있으나 다른 product axis
- Snowiki가 배울 것: memory != compiled wiki/knowledge artifact
- evidence basis: explicit memory-layer/product framing rather than compiled knowledge artifact posture

## direct comparison shortlist
1. `xoai/sage-wiki`
2. `hang-in/seCall`
3. `kenforthewin/atomic`
4. `nashsu/llm_wiki`
5. `khoj-ai/khoj`

## popular but less strategically similar
- `mem0`
- `RAGFlow`
- `Onyx`
- `qmd` (중요한 lineage/reference이지만 product peer는 아님)

## 핵심 결론

Snowiki는 generic chat-with-docs나 memory product보다는,
**persistent knowledge artifact / provenance / local-first usability**를 핵심으로 하는 시스템과 비교해야 합니다.

## evidence appendix

Reviewed as of: 2026-04-12

### direct peer — evidence basis
- `xoai/sage-wiki`
  - URL: https://github.com/xoai/sage-wiki
  - inspected artifacts: repository landing page / README-level positioning
  - supports: wiki-maintenance posture, artifact-centric framing, visible OSS maturity signal
- `hang-in/seCall`
  - URL: https://github.com/hang-in/seCall
  - inspected artifacts: repository landing page / workflow-oriented positioning
  - supports: local-first workflow framing, session/source seriousness, provenance-aware sibling comparison
- `kenforthewin/atomic`
  - URL: https://github.com/kenforthewin/atomic
  - inspected artifacts: repository landing page / atomic knowledge representation framing
  - supports: strong knowledge-unit representation comparison and linked-knowledge orientation
- `nashsu/llm_wiki`
  - URL: https://github.com/nashsu/llm_wiki
  - inspected artifacts: repository landing page / llm-wiki lineage framing
  - supports: direct conceptual lineage to the llm-wiki idea and generated wiki artifact orientation
- `khoj-ai/khoj`
  - URL: https://github.com/khoj-ai/khoj
  - inspected artifacts: repository landing page / product posture / release maturity signals
  - supports: local-first search product ergonomics, stronger operational maturity, assistant-style contrast

### adjacent system — evidence basis
- `qmd`
  - URL: https://github.com/tobi/qmd
  - inspected artifacts: public retrieval-substrate positioning and local search framing
  - supports: lexical-first / local-first substrate comparison
- `Onyx`
  - URL: https://github.com/onyx-dot-app/onyx
  - inspected artifacts: public product/repo posture
  - supports: enterprise retrieval-platform contrast
- `RAGFlow`
  - URL: https://github.com/infiniflow/ragflow
  - inspected artifacts: public workflow/pipeline-oriented RAG framing
  - supports: ingestion/pipeline-heavy contrast rather than compiled-knowledge equivalence
- `mem0`
  - URL: https://github.com/mem0ai/mem0
  - inspected artifacts: public memory-layer/product framing
  - supports: negative-control comparison between memory systems and compiled knowledge engines

### how to read
- 이 비교는 strategic comparison과 roadmap sequencing 용도입니다.
- immutable ranking이 아니라 design-oriented reference입니다.
- 특정 시스템에 강하게 의존하는 미래 결정이 필요해지면, 그 시스템은 별도 deeper source review를 해야 합니다.
