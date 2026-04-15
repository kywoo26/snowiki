# Snowiki 비전

## Snowiki는 무엇인가

Snowiki는 **provenance-aware, compiled knowledge engine**입니다.

Snowiki의 목적은 매 질의마다 raw source를 다시 뒤져 답을 만들거나, 메모를 그냥 searchable bucket에 쌓아두는 것이 아닙니다. 대신 raw material을 지속적으로 **inspectable하고 interlinked된 지식 artifact**로 compile하여, 이후 query, lint, recall, improvement의 기반으로 삼는 것입니다.

실질적으로 Snowiki는 아래 사이에 위치합니다.
- raw source / session 저장
- retrieval / search infrastructure
- 유지·개선되는 wiki형 knowledge artifact

즉 Snowiki는 generic chat-with-documents RAG보다는 **knowledge compiler / knowledge operating substrate**에 가깝습니다.

## 기반 철학

### 1. 저장이 아니라 compilation
핵심 가치는 저장이 아니라 compilation에서 생깁니다.

source, session trace, note는 최종 결과물이 아닙니다. 최종 결과물은 그것들로부터 만들어지는:
- summary
- concept
- entity
- topic
- comparison
- question
- overview
같은 고차 지식 artifact입니다.

즉 Snowiki는 “일단 다 넣고 나중에 찾기”보다, **source를 더 높은 수준의 지식 구조로 바꾸고 그 구조를 계속 유용하게 유지하는 것**을 최적화합니다.

### 2. 인식론적 무결성
Snowiki는 다음 차이를 보존하려는 시스템입니다.
- fact 와 inference
- evidence 와 synthesis
- source truth 와 derived knowledge

그래서 provenance가 중요합니다. Snowiki의 장기 방향은 “검색을 더 잘한다”를 넘어, **더 근거 있는 retrieval과 더 근거 있는 compiled knowledge**를 만드는 것입니다.

### 3. 지식의 누적 성장
Snowiki는 Karpathy의 llm-wiki 계열 철학 중 가장 중요한 축을 계승합니다: artifact는 시간이 갈수록 더 좋아져야 한다는 점입니다.

한 번 잘 답하는 것이 아니라, 다음 답이 더 쉬워지고 더 구조화되고 더 grounded되도록 만들어야 합니다. query, ingest, correction은 모두 이 compounding process에 기여해야 합니다.

### 4. Local-first와 inspectability
Snowiki는 local-first posture를 전제로 합니다.

즉:
- deterministic local operation
- explicit benchmark / evaluation discipline
- inspectable machine-readable output
- hidden cloud-only magic 비의존

이건 나중 semantic/model layer를 금지한다는 뜻은 아니지만, 그것들이 **이해 가능하고 locally operable한 시스템** 위에 올라가야 한다는 뜻입니다.

### 5. Agent-friendly by design
Snowiki는 사람만을 위한 도구가 아니라, LLM/agent에게도 강력한 도구가 되어야 합니다.

따라서 다음이 중요합니다.
- stable CLI contract
- machine-readable JSON output
- MCP-friendly retrieval primitive
- composable workflow / skill
- agent loop에서 신뢰할 수 있을 정도의 deterministic behavior

agent ergonomics는 문서 꾸밈이 아니라 아키텍처의 일부입니다.

## lineage와 무엇을 계승할 것인가

### Karpathy / llm-wiki
이건 철학적 출발점입니다. query-time retrieval만 잘하는 시스템이 아니라, source와 대화를 흡수하면서 더 좋아지는 maintained wiki입니다.

계승할 것:
- compounding knowledge
- ephemeral answer generation보다 persistent artifact
- human-in-the-loop knowledge growth

무비판적으로 계승하면 안 되는 것:
- organization만으로 epistemic 문제가 해결된다는 낙관
- provenance와 verification의 과소 명시

### qmd
qmd는 **retrieval substrate reference**로 중요합니다.

계승할 것:
- lexical-first discipline
- local-first operation
- default가 아닌 optional hybrid/rerank hook
- UX surface가 아니라 evidence-producing subsystem으로서의 retrieval

제품 정체성으로까지 계승하면 안 되는 것:
- “그냥 검색 엔진”이 되는 것
- retrieval power를 완전한 knowledge system과 동일시하는 것

### seCall
seCall은 provenance-first, local workflow sibling으로 중요합니다.

계승할 것:
- session/source/workflow seriousness
- maintenance discipline
- real-world local usage에 대한 감각

무비판적으로 가져오면 안 되는 것:
- seCall의 product boundary에 속하는 가정들

## 제품 정체성

Snowiki는 다음처럼 이해되어야 합니다.

> source와 session을 maintained knowledge artifact로 compile하고, 그 artifact를 CLI/MCP/agent-facing contract를 통해 search, recall, lint, 그리고 앞으로의 reasoning workflow에 활용하는 local-first, provenance-aware system

Snowiki는 다음으로 설명되면 안 됩니다.
- generic RAG
- chat with docs
- pure memory layer
- plain markdown search engine

이들은 인접 시스템일 수는 있어도 Snowiki 정체성의 중심은 아닙니다.

## 현재 전략 방향

지금 단계에서 Snowiki는 다음을 우선해야 합니다.
1. canonical retrieval / corpus contract
2. lexical-first retrieval quality 및 성능
3. 더 강한 evidence / benchmark discipline
4. 더 명확한 agent-facing runtime contract

그리고 당분간 다음은 defer해야 합니다.
- default semantic/vector retrieval
- default-path rerank
- backend replacement
- mainline architecture로서의 model-heavy local flow

## 성공 조건

Snowiki가 진짜 성공하려면:
- 실제 source/session material을 ingest하고
- 그것을 유용한 evolving knowledge artifact로 compile하며
- 그 artifact를 CLI/MCP/agent-facing contract를 통해 안정적으로 노출하고
- provenance와 structural health를 지키면서
- 다음 지식 작업을 더 쉽게 만들어야 합니다.
