# Rust / Native Acceleration 로드맵

## 목적

이 문서는 Snowiki가 앞으로 Rust/native acceleration을 어떻게 생각해야 하는지 정의합니다.

이 문서가 막고자 하는 실수는 두 가지입니다.
- profiling 없이 native acceleration을 즉시 답처럼 여기는 것
- “나중에 Rust로”라고만 하고 무엇이 정당화 조건인지 말하지 않는 것

## 현재 posture

현재 Snowiki는 Python-first 시스템으로 남는 것이 맞습니다.

이유:
- retrieval / workflow layer가 아직 계속 정비되고 있음
- 지금도 Python-level architecture와 contract cleanup으로 얻을 수 있는 이익이 큼
- public/runtime contract가 아직 정의·안정화 단계에 있음

## 지금 Python에 남겨야 할 것
당분간 아래는 Python-first가 맞습니다.
- CLI orchestration
- MCP/read-facing integration
- workflow/skill orchestration
- provenance handling
- benchmark/evaluation integration
- rebuild/compilation orchestration

## 나중에 native acceleration 후보가 될 곳
native acceleration이 정당화된다면, 유력 후보는:
- lexical search hot path
- indexing/tokenization hot path
- stable해진 rerank kernel
- Python optimization 이후에도 CPU-bound로 남는 large corpus transform

다만 이건 후보일 뿐, 지금 결정 사항은 아닙니다.

## native work가 승격되기 위한 조건

### 1. Measured hotspot persistence
다음 이후에도 bottleneck이 남아야 합니다.
- retrieval contract hardening
- lexical/tokenization cleanup
- Python-level architecture optimization

### 2. Stable contract boundary
가속할 컴포넌트의 경계가 안정적이어야 합니다.
즉 아래를 깨지 않고 교체 가능해야 합니다.
- CLI contract
- MCP contract
- benchmark/evaluation posture
- provenance expectation

### 3. Operational fit
다음을 설명할 수 있어야 합니다.
- packaging/build impact
- local development cost
- debugging cost
- platform constraint
- 얻는 성능 이익이 complexity를 정당화하는지

### 4. Clear win profile
단순히 “hot해 보인다”가 아니라 아래 중 하나여야 합니다.
- profiling에서 반복적으로 dominant hotspot
- Python-level 개선 이후에도 잘 안 줄어듦
- lower-level implementation으로 의미 있는 gain이 날 가능성이 높음

## 너무 일찍 하면 안 되는 것
- orchestration layer를 먼저 Rust로 옮기기
- 측정을 건너뛰기 위해 native acceleration으로 도망가기
- backend swap과 retrieval strategy rewrite를 한 번에 하기
- 실제 성능 필요보다 packaging complexity가 먼저 커지게 만들기

## backend evolution과의 관계

Rust/native acceleration과 backend evolution은 관련 있지만 같은 것이 아닙니다.

- backend swap (예: Tantivy)는 product/architecture choice
- existing hotspot의 native acceleration은 implementation/performance choice

이 둘을 섞으면 안 됩니다.

## bottom line

Snowiki는 Rust/native acceleration을 serious long-term option으로 볼 수 있습니다.

하지만 그 전에 반드시 말할 수 있어야 합니다.
- 정확히 어떤 hotspot인지
- 정확히 어떤 boundary인지
- 정확히 어떤 gain을 기대하는지
- 정확히 어떤 operational cost를 치를 것인지

그전까지는 Python-level architecture hardening과 measured optimization이 정답입니다.
