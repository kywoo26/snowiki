# Retrieval 결정 매트릭스

## 목적

이 문서는 Snowiki retrieval 방향에 대한 **현재 설계 결정**을 명시합니다.

즉 survey가 아니라 decision document입니다.

## 프레이밍
- **Now**: 지금 적극적으로 해야 하는 것
- **Later**: 유효한 방향이지만 아직은 아님
- **Reserved question**: 구현 전에 증거가 더 필요한 명시적 질문

## 현재 결정

| 축 | Now | Later | Reserved question |
|---|---|---|---|
| Lexical backbone | active runtime backbone으로 유지 | contract hardening + lexical evaluation 이후 재검토 | 현재 scorer를 나중에 교체/보강할지 |
| Canonical retrieval unit | 하나의 shared retrieval/corpus contract 표준화 | specialized corpus variant는 나중에 | normalized record, compiled page, staged blend 중 장기 canonical unit은 무엇인지 |
| Hybrid retrieval | deferred extension seam으로 유지 | lexical 한계가 증명된 뒤 추가 | 어떤 query class가 hybrid를 정당화하는지 |
| Reranking | default path에 넣지 않음 | optional later quality layer | rerank가 어떤 candidate set에 적용돼야 하는지 |
| Local models | default runtime path 밖에 둠 | CPU/GPU policy가 명확해진 후 추가 | warm/cold lifecycle, fallback, agent semantics |
| Backend evolution | defer | later architecture move | SQLite FTS5 vs Tantivy vs Qdrant vs native acceleration |
| Korean lexical strategy | lexical/tokenization 문제로 먼저 다룸 | selectable strategy는 later | 어떤 tokenizer/morphology choice가 Korean/mixed slice에서 이기는지 |
| Agent-facing constraints | 지금 non-negotiable | contracts가 안정적일 때만 확장 | retrieval complexity를 agent에게 얼마나 노출할지 |

## stable modern patterns vs unsettled areas

### 현재 best practice로 볼 수 있는 것
- lexical retrieval은 exact identifier / path / literal / provenance-bearing text에 대한 안전망이다
- hybrid retrieval은 lexical을 대체하는 게 아니라 additive layer인 경우가 많다
- reranking은 poor first-stage candidate generation을 대신하는 것이 아니라 second-stage precision layer다
- retrieval quality와 latency는 answer-generation quality와 분리해서 평가해야 한다
- machine-readable agent-facing contract는 내부 retrieval complexity보다 단순해야 한다

### 아직 decision gate 뒤에 둬야 하는 것
- default multilingual / Korean retrieval stack이 무엇인지
- local CPU/GPU model split의 현실적인 ergonomics
- backend swap이 operational cost를 정당화하는 시점
- retrieval strategy complexity를 agent에게 얼마나 노출할지

## 아직 하지 말아야 할 것
- semantic/vector runtime integration
- default rerank path
- backend swap
- mainline runtime에서 local model lifecycle complexity
- benchmark evidence만으로 product architecture를 결정하는 것

## promotion gates

deferred work는 아래 증거 중 하나 이상이 있어야 승격됩니다.
- measured lexical limits
- benchmark quality deltas
- operational fit
- contract stability

## gate를 해석하는 방법

### measured lexical limits
다음 이후에도 lexical이 실패할 때를 말합니다.
- canonical corpus assembly
- tokenization cleanup
- query-routing cleanup

이후에도 relevant result를 반복적으로 놓친다면 semantic/hybrid work가 정당화됩니다.

### benchmark quality deltas
아래 지표에서 일관된 개선이 있어야 합니다.
- Recall@k
- MRR
- nDCG@k

one-off win이나 cherry-pick된 예시로는 부족합니다.

### operational fit
다음이 명시돼야 합니다.
- acceptable latency
- acceptable memory
- warm/cold behavior
- CPU-only fallback / GPU-optional semantics

이게 명시되지 않으면 아직 ready가 아닙니다.

### contract stability
다음이 유지돼야 합니다.
- CLI JSON stability
- MCP/tool behavior
- agent loop에서 충분히 deterministic한 retrieval
- provenance / benchmark discipline

## 현재 bottom line

지금 Snowiki의 practical rule은 이렇습니다.

1. **lexical backbone first**
2. **canonical retrieval contract before more sophistication**
3. **Korean/mixed-language lexical evaluation before semantic escalation**
4. **hybrid/rerank/local-model/backend work only when benchmark evidence and operational fit both justify it**
