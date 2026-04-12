# 현재 Retrieval 아키텍처

## 목적

이 문서는 Snowiki의 현재 retrieval architecture를 shipped runtime 기준으로 설명합니다.

목표는 앞으로의 변경을 “의도된 변경”으로 만들고, CLI/daemon/MCP/benchmark/workflow surface 사이의 drift를 줄이는 것입니다.

## 현재 active retrieval surfaces

Snowiki의 retrieval stack은 지금 네 가지 active surface를 통해 드러납니다.

1. **CLI query / recall**
   - `src/snowiki/cli/commands/query.py`
   - `src/snowiki/cli/commands/recall.py`

2. **Daemon warm retrieval**
   - `src/snowiki/daemon/warm_index.py`
   - `src/snowiki/daemon/server.py`
   - `src/snowiki/daemon/cache.py`
   - `src/snowiki/daemon/invalidation.py`

3. **Read-only MCP retrieval**
   - `src/snowiki/mcp/server.py`
   - `src/snowiki/mcp/tools/*`
   - `src/snowiki/mcp/resources/*`

4. **Benchmark / evidence paths**
   - `src/snowiki/bench/*`
   - `benchmarks/README.md`

## lexical backbone

현재 active backbone은 lexical이며 deterministic합니다.

핵심 모듈:
- `src/snowiki/search/indexer.py`
- `src/snowiki/search/index_lexical.py`
- `src/snowiki/search/index_wiki.py`
- `src/snowiki/search/tokenizer.py`
- `src/snowiki/search/queries/*`

즉 현재 runtime truth는:
- lexical blended index 기반
- semantic/rerank가 default path가 아님
- strategy 차이는 같은 lexical core 위의 routing/policy 차이

## canonical retrieval seam

현재 canonical seam은:
- `src/snowiki/search/workspace.py`

이 파일이 맡는 것:
- normalized record → search-ready structure
- compiled page → search-ready structure
- blended retrieval snapshot 생성
- 여러 runtime surface가 공통으로 기대할 retrieval contract 제공

즉 지금 코드에서 가장 중요한 architecture seam입니다.

## strategy layers

현재 retrieval policy wrapper는 아래에 있습니다.
- `src/snowiki/search/queries/known_item.py`
- `src/snowiki/search/queries/topical.py`
- `src/snowiki/search/queries/temporal.py`

이건 separate search engine이 아니라, 같은 lexical core 위에 얹힌 strategy layer입니다.

## semantic / rerank status

### semantic
- `src/snowiki/search/semantic_abstraction.py`
- 현재는 hook / abstraction point
- active runtime retrieval path는 아님

### rerank
- `src/snowiki/search/rerank.py`
- 역시 seam은 있지만 main deployed path는 아님

## benchmark path의 의미

benchmark는 retrieval evidence를 만드는 데 중요하지만, runtime query path와 항상 1:1은 아닙니다.

주요 파일:
- `src/snowiki/bench/baselines.py`
- `src/snowiki/bench/report.py`
- `src/snowiki/bench/phase1_correctness.py`
- `src/snowiki/bench/phase1_latency.py`

중요한 점:
- benchmark evidence는 강력함
- 하지만 benchmark baseline이 항상 runtime query path와 동일한 것은 아님
- benchmark/runtime equivalence는 명시적으로 말해야지 자동으로 가정하면 안 됨

## cache와 daemon semantics

Snowiki에는 여러 cache-like layer가 있습니다.

### query-path cache
- 반복 query에 대한 cheap in-process reuse

### daemon warm snapshot
- long-lived prebuilt retrieval surface

### TTL response cache
- daemon request/response reuse

즉 중요한 architecture rule은:
- cache ownership 명시
- invalidation 명시
- cache가 retrieval contract를 몰래 바꾸지 않게 하기

## agent-facing retrieval surfaces

retrieval architecture는 agent usability 제약을 받습니다.

즉 반드시 보존해야 하는 것:
- CLI JSON output
- MCP search/recall/page/link tools
- workflow/skill composability

따라서 “검색을 더 좋게 한다”는 명분으로 machine-facing contract를 깨면 안 됩니다.

## 현재 가장 큰 risk

현재 가장 큰 architecture risk는 **drift**입니다.

즉:
- CLI
- daemon
- MCP
- benchmark/evidence
- skill/workflow expectation

이 surface들이 서로 다른 retrieval 언어를 말하기 시작하는 것입니다.

그래서 near-term에는 semantic/rerank/backend 추가보다
**retrieval contract canonicalization**이 더 중요합니다.

## 현재 코드가 암시하는 우선순위
1. canonical retrieval contract
2. lexical quality / language strategy
3. profiling / performance
4. semantic / rerank / local model questions
5. backend evolution / native acceleration

이 순서는 evidence가 뒤집지 않는 한 기본값으로 유지하는 게 맞습니다.
