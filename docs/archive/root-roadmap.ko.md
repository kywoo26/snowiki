# ROADMAP

이 문서는 중장기 전략 backlog를 추적합니다.

## 현재 상태
- governance / path contract 정리 완료
- unit / integration test taxonomy 정리 완료
- `src/snowiki/` layout 정리 완료
- retrieval hot path 1차 성능 최적화 완료
- canonical retrieval service hardening 완료
- manual benchmark workflow 추가 완료

## Near-Term

### 1. Korean and mixed-language lexical benchmark
한국어 및 혼합언어 retrieval을 lexical/tokenization 문제로 먼저 측정하고 개선합니다.

Why:
- Korean retrieval은 여전히 unresolved lexical/tokenization question입니다.
- mixed-language retrieval은 Snowiki의 중요한 차별화 포인트가 될 가능성이 큽니다.
- semantic escalation 전에 lexical strategy를 충분히 검증해야 합니다.

Likely scope:
- current tokenizer vs Kiwi-backed alternative benchmark
- noun-heavy vs broader morphology tradeoff 비교
- Korean / mixed Korean-English retrieval lexical baseline 정리

### 2. Skill contract and agent interface design
현재 runtime truth에 맞는 skill/agent 인터페이스를 재설계합니다.

Why:
- install/use contract는 aligned 되었지만, skill layer 자체는 아직 patch-level cleanup 수준입니다.
- 좋은 skill은 usage text가 아니라 agent contract입니다.
- Snowiki는 CLI / MCP / skill / roadmap 중 무엇이 authoritative한지 더 명확히 해야 합니다.

Deferred because:
- immediate priority는 current runtime misunderstanding을 줄이는 것이었고, deeper redesign은 deliberate research가 필요합니다.

Likely scope:
- Claude/OpenCode/OMO skill contract comparison
- front matter / metadata / token-budget rules
- directory structure / canonical-owner rules
- runtime-truth vs deferred-work boundaries

Pull-forward trigger:
- skill docs와 runtime이 다시 drift할 때
- 여러 agent platform에서 divergent wrapper가 필요할 때
- skill ergonomics를 first-class product surface로 다룰 준비가 되었을 때

### 3. Coverage governance ratchet
report-only에서 non-regression coverage governance로 이동합니다.

Why:
- local/CI policy가 이제 더 명확해졌습니다.
- coverage를 noisy gate가 아니라 실제 품질 신호로 만들 필요가 있습니다.

Deferred because:
- 지금 중심 과제는 performance/retrieval 쪽이며, coverage baseline도 더 지켜볼 시간이 필요합니다.

Likely scope:
- baseline observation
- non-regression threshold policy
- changed-area testing expectations

Pull-forward trigger:
- coverage reports가 여러 PR에서 안정화될 때
- report-only visibility에도 regressions가 slipping될 때

### 4. Test taxonomy audit
느린 테스트와 integration 분류 drift를 주기적으로 점검합니다.

Why:
- unit/integration split은 들어갔지만 drift는 다시 생길 수 있습니다.

Deferred because:
- 가장 가치 있는 taxonomy 작업이 방금 끝났고, drift가 실제로 남았는지 시간을 두고 봐야 합니다.

Likely scope:
- borderline test audit
- marker / naming convention 강화
- default unit loop 속도 유지

Pull-forward trigger:
- 새로운 slow test가 default unit loop에 계속 들어올 때
- integration behavior가 unit file에 다시 새어 들어올 때

### 5. Benchmark workflow ergonomics
현재 수동 trigger 기반 benchmark workflow 위에 더 나은 review/ergonomics를 쌓습니다.

Why:
- benchmark command와 manual workflow는 이미 있으나, shared review flow는 더 좋아질 수 있습니다.

Deferred because:
- 지금 우선순위는 retrieval quality와 architecture이지 benchmark UX polish가 아닙니다.

Likely scope:
- richer artifact/report ergonomics
- better shared benchmark review flow
- selective benchmark execution patterns

Pull-forward trigger:
- perf-sensitive PR이 잦아질 때
- benchmark verification을 계속 수동으로 반복하게 될 때

## Mid / Long-Term 핵심 축
- 이 문서의 Mid/Long-Term 섹션은 아래에 상세히 이어집니다.

## Mid-Term

### 6. Search architecture hardening (next layer)
첫 canonical retrieval hardening 이후, tokenization / indexing / retrieval orchestration / benchmark-evidence surface 사이의 경계를 더 정교하게 다듬습니다.

Why:
- profiling이 더 쉬워짐
- hot path 교체가 더 쉬워짐
- product behavior와 benchmark code 사이의 coupling을 줄일 수 있음

Deferred because:
- 첫 canonical retrieval hardening pass가 막 끝났고, 다음 layer는 새 pressure point가 명확할 때만 올리는 게 맞음
- boundary 변경은 계속 measured hotspot과 concrete pressure에 의해 결정돼야 함

Pull-forward trigger:
- hotspot analysis가 하나의 isolated function보다 search-layer coupling을 반복적으로 가리킬 때
- benchmark와 product code가 너무 얽혀 안전한 최적화가 어려울 때
- backend 또는 local-model experiment가 cleaner boundary를 요구할 때

### 7. Semantic quality and linting expansion
구조적 무결성을 넘어 knowledge quality까지 품질 체크를 확장합니다.

Examples:
- contradiction detection
- stale claim detection
- weak-link / orphan-topic 탐지
- citation / provenance quality check

### 8. Incremental rebuild and ingest efficiency
Snowiki workspace의 반복적인 partial update 비용을 줄입니다.

Why:
- 큰 vault에서는 매번 full rebuild보다 incremental rebuild가 필요함

Deferred because:
- 현재 performance work는 search/query/index latency에 집중되어 있음
- incremental rebuild 변화는 첫 retrieval performance pass보다 더 넓은 범위임

Pull-forward trigger:
- rebuild 시간이 대표적인 사용자 체감 병목이 될 때
- 실제 vault 크기에서 full rebuild가 비현실적일 때
- daemon/warm-index 최적화만으로 충분하지 않을 때

## Long-Term

### 9. Optional native acceleration for hot paths
Python을 public orchestration/API layer로 유지하면서, 가장 가치 있는 hot path에 Rust/native acceleration을 검토합니다.

Important:
- public import surface는 `snowiki.*`를 유지해야 함
- 이건 명시적으로 later-stage optimization이며, current implementation goal이 아님

Potential candidates:
- search/index/query hot paths
- tokenization/ranking utilities
- Python overhead가 지배적인 large-scale data transform

Deferred because:
- profiling-first 작업으로 실제 Python bottleneck을 먼저 밝혀야 native complexity가 정당화됨
- backend/layout 기반이 이제 막 안정화됨

Pull-forward trigger:
- Python-level optimization 이후에도 hotspot이 CPU-bound로 남을 때
- Tantivy/native 계열 tradeoff가 migration cost를 정당화할 만큼 매력적일 때
- 현재 Python 구현으로는 local performance target을 맞출 수 없을 때

### 10. Local semantic and hybrid retrieval layer
lexical backbone 위에 embeddings, reranking, query expansion, hybrid retrieval을 additive layer로 붙이는 방향을 검토합니다.

Why:
- semantic recall은 paraphrase, vague query, cross-language meaning gap에 도움을 줌
- qmd류 시스템은 local embeddings/reranker를 신중하게 쓸 때 retrieval quality를 실제로 끌어올릴 수 있음을 보여줌

Deferred because:
- 현재 다음 plan은 의도적으로 lexical/profiling-first임
- semantic/hybrid 작업은 baseline clarity 이후에 붙어야 함
- local model CPU/GPU tradeoff는 performance PR 안에 묻히면 안 됨

Likely scope:
- embedding index insertion point
- rerank / query-expansion hook
- CPU-only fallback + GPU-optional acceleration policy
- warm/cold model lifecycle 및 caching strategy

Pull-forward trigger:
- benchmark나 사용자 evidence가 lexical retrieval이 semantically relevant result를 너무 많이 놓친다고 보여줄 때
- 강한 lexical baseline이 확보되고 다음 bottleneck이 latency보다 quality일 때
- local model ergonomics가 agent-facing retrieval quality에 중요해질 때

### 11. Broader benchmark and evaluation system
현재 deterministic backend benchmark를 넘어 더 풍부한 evaluation framework로 확장합니다.

Examples:
- scheduled benchmark runs
- benchmark history / trend tracking
- more slices and workload classes
- memory / higher-percentile latency measurement

Deferred because:
- 첫 performance deep dive에는 현재 benchmark만으로 충분함
- evaluation-system 확장은 실제 optimization work와 real measurement pain이 생긴 뒤에 가야 함

Pull-forward trigger:
- 현재 benchmark slice가 실제 회귀를 충분히 반영하지 못할 때
- one-off report보다 history/trend visibility가 필요해질 때
- semantic/hybrid retrieval이 더 넓은 evaluation dimension을 요구할 때

## Pull-Forward Triggers

다음 중 하나 이상이 성립하면 roadmap 항목을 `.sisyphus/plans/`로 승격합니다.
- 현재 product / architecture work를 막고 있을 때
- 팀이 같은 작업을 수동으로 반복하고 있을 때
- 충분한 자동화 없이 regressions가 계속 들어올 때
- acceptance criteria와 verification commands를 정의할 만큼 scope가 구체화됐을 때

## 원칙
- 실행 직전 계획은 `.sisyphus/plans/*.md`
- 이 문서는 전략 backlog입니다.
- deferred 항목은 “안 한다”가 아니라 “증거가 생길 때까지 올리지 않는다”는 뜻입니다.

## 명시적으로 여기서 다루지 않는 것
- one-off bug
- single-PR cleanup work
- execution-ready implementation breakdown
- 우선순위 없는 일시적 brainstorming
