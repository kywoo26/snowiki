# Agent 및 Evaluation Contract

## 목적

이 문서는 Snowiki가 명확히 유지해야 하는 두 가지를 정의합니다.

1. 시스템을 어떻게 평가할 것인가
2. agent가 오늘 시점에서 무엇을 안정적인 계약으로 의존할 수 있는가

목표는 evaluation과 agent-facing ergonomics를 1급 제약으로 유지하되, vague한 product promise로 섞지 않는 것입니다.

## Evaluation 축

Snowiki는 “quality”를 하나로 뭉개지 않고 분리해서 봐야 합니다.

### 1. Retrieval quality
시스템이 관련 자료를 얼마나 잘 찾는가.

현재 유효한 지표:
- Recall@k
- MRR
- nDCG@k

### 2. Latency
ingest, rebuild, query가 실제 사용에 충분히 빠른가.

현재 benchmark posture는 이미:
- P50 latency
- P95 latency
를 포함합니다.

### 3. Structural integrity
workspace가 내부적으로 건강한가.

예:
- path / index consistency
- lint health
- broken links
- orphan pages
- stale artifacts

### 4. Provenance quality
claim과 compiled artifact가 source까지 trace 가능한가.

이건 retrieval quality보다 더 넓은 축이며, 반드시 분리해서 유지해야 합니다.

### 5. Answer quality
최종 synthesis / response의 유용성과 정확성입니다.

이건 retrieval quality와 동일하지 않으며, 명시적 근거 없이 같은 것으로 취급하면 안 됩니다.

## 현재 검증된 agent-facing 계약

### CLI JSON 계약
현재 runtime truth:
- authoritative contract는 installed `snowiki` CLI
- `--output json`을 지원하는 command는 machine-readable output을 제공

현재 안전하게 말할 수 있는 예:
- `snowiki query ... --output json`
- `snowiki recall ... --output json`
- `snowiki export ... --output json`

### MCP 계약
Snowiki는 read-only MCP surface를 제공합니다.

현재 안전하게 말할 수 있는 것:
- read-oriented search/retrieval
- MCP를 통한 mutation 없음
- agent loop에서 쓸 만큼 deterministic한 retrieval primitive

### Skill/workflow의 역할
skill layer는 shipped runtime을 감싸는 workflow layer로 봐야지, runtime truth의 별도 소스로 보면 안 됩니다.

즉:
- CLI가 authoritative
- skill은 orchestration 가능
- skill이 Snowiki의 현재 기능을 몰래 다시 정의하면 안 됨

## agent가 아직 가정하면 안 되는 것
- semantic retrieval이 default path라고 가정하지 말 것
- hybrid mode가 mature shipped behavior라고 가정하지 말 것
- default path에 reranking이 있다고 가정하지 말 것
- edit/sync/merge style broader workflow가 stable runtime feature라고 가정하지 말 것
- model-backed retrieval availability를 기본 가정으로 두지 말 것

## 설계 규칙

Snowiki가 성장하더라도 새로운 retrieval / workflow layer는 다음을 지켜야 합니다.
- stable machine-readable contract
- automation에 충분히 deterministic한 behavior
- explicit failure semantics
- retrieval quality와 answer quality의 분리

이걸 설명하지 못하는 제안은 아직 준비되지 않은 것입니다.
