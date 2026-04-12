# 현재 기능 수준과 격차

## 목적

이 문서는 세 가지를 답합니다.
1. 지금 Snowiki가 실제로 무엇을 할 수 있는가
2. 그 기능들이 얼마나 성숙한가
3. 의도한 역할을 제대로 수행하려면 무엇이 아직 부족한가

이 문서는 wishlist가 아니라 현재 상태에 대한 현실 문서입니다.

## 현재 capability level

현재 Snowiki는 **usable Phase 1 backend이자 knowledge-compilation substrate**로 보는 것이 가장 정확합니다. 완성된 end-to-end knowledge product는 아직 아닙니다.

즉 이미:
- 설치 가능한 CLI
- 테스트 가능한 runtime behavior
- benchmark/evidence discipline
을 갖고 있지만,
vision에서 말한 product/workflow/knowledge-quality story 전체를 완성하진 못했습니다.

이 판단은 deferred workflow 텍스트가 아니라, **현재 shipped runtime과 tests**를 기준으로 합니다.

## 지금 실제로 할 수 있는 것

### 1. 설치 가능한 CLI runtime
현재 Snowiki는 `snowiki` 명령으로 설치 가능한 CLI입니다.

현재 shipped commands:
- `ingest`
- `rebuild`
- `query`
- `recall`
- `status`
- `lint`
- `export`
- `benchmark`
- `daemon`
- `mcp`

**근거:**
- `pyproject.toml`
- `src/snowiki/cli/main.py`
- `README.md` Quick Start

### 2. source/session ingest → normalized storage
Snowiki는 특히 Claude/OpenCode 계열 session-like source를 normalized storage로 ingest할 수 있습니다.

**근거:**
- `src/snowiki/cli/commands/ingest.py`
- `tests/cli/test_ingest.py`
- `tests/adapters/test_opencode_adapter.py`
- `tests/privacy/test_redaction.py`

**아직 부족한 점:**
- source 종류가 아직 좁음
- end-user ingest workflow가 더 다듬어져야 함

### 3. compiled artifact rebuild
Snowiki는 normalized records로부터 compiled wiki-like pages를 rebuild할 수 있습니다.

**근거:**
- `src/snowiki/cli/commands/rebuild.py`
- `src/snowiki/compiler/engine.py`
- `tests/cli/test_rebuild.py`
- `tests/compiler/test_rebuild_determinism.py`

**아직 부족한 점:**
- richer compiled artifact semantics
- broader authoring/maintenance flow

### 4. lexical query / recall
현재는 lexical retrieval path가 실제로 동작합니다.

포함:
- query
- recall
- daemon-backed warm retrieval

**근거:**
- `src/snowiki/cli/commands/query.py`
- `src/snowiki/cli/commands/recall.py`
- `src/snowiki/search/indexer.py`
- `src/snowiki/search/workspace.py`
- `tests/cli/test_query.py`
- `tests/retrieval/test_mixed_language_queries_integration.py`

**아직 부족한 점:**
- Korean/mixed-language lexical policy
- semantic/hybrid/rerank의 실제 runtime 도입

### 5. read-only MCP surface
Snowiki는 agent/tool이 쓸 수 있는 read-only MCP surface를 갖고 있습니다.

**근거:**
- `src/snowiki/cli/commands/mcp.py`
- `src/snowiki/mcp/server.py`
- `src/snowiki/mcp/tools/*`
- `src/snowiki/mcp/resources/*`
- `tests/mcp/test_search.py`
- `tests/mcp/test_readonly.py`

**아직 부족한 점:**
- 더 넓은 knowledge workflow에 비하면 MCP surface는 여전히 좁음

### 6. benchmark / evaluation discipline
현재 Snowiki는 이미:
- deterministic benchmark preset
- retrieval quality threshold
- latency threshold
- structural gate
- manual benchmark workflow
를 갖고 있습니다.

**근거:**
- `src/snowiki/cli/commands/benchmark.py`
- `src/snowiki/bench/*`
- `benchmarks/README.md`
- `tests/cli/test_benchmark.py`
- `tests/bench/test_retrieval_benchmarks_integration.py`

**아직 부족한 점:**
- answer-quality / provenance quality evaluation
- benchmark history / trend tooling
- broader workflow-level evaluation

### 7. unit/integration split + governance
엔지니어링 substrate 자체도 많이 좋아졌습니다.

포함:
- fast unit loop
- explicit integration tests
- governance/path-contract discipline
- `src/snowiki/` layout

**근거:**
- `AGENTS.md`
- `tests/governance/*`
- current CI workflow

## 지금 solid한 영역
- packaged CLI runtime
- lexical retrieval backbone
- rebuild/compile path
- deterministic benchmark harness
- MCP read surface
- governance and path discipline
- fast unit + explicit integration taxonomy

즉, 이 영역들은 이제 prototype라기보다 **serious maintained engineering system**에 가깝습니다.

## 지금 partial한 영역
- broader wiki workflow beyond core CLI/retrieval
- cross-session install/use story beyond the newly aligned CLI-first contract
- deeper skill/runtime/agent contract design
- multilingual/Korean lexical strategy
- richer answer-quality and provenance quality evaluation

즉 방향은 있고 일부는 이미 작동하지만, 아직 “finished product surface”라고 말하긴 이른 영역입니다.

## 지금 deferred / placeholder인 영역
- semantic retrieval as active runtime path
- default-path reranking
- real hybrid shipped mode
- local model lifecycle management
- backend migration (SQLite FTS5/Tantivy/Qdrant/native)
- contradiction detection / richer semantic lint
- broad edit/sync/merge style workflow as stable shipped behavior

이건 중요하지만, **현재 할 수 있는 것처럼 말하면 안 되는 영역**입니다.

## “제기능”을 하려면 남은 큰 gap
1. canonical retrieval contract
2. better language strategy (Korean / mixed-language)
3. stronger knowledge-quality layer
4. better skill/agent contract
5. stronger productized ingest-to-wiki flow

## bottom line

Snowiki는 이미 toy는 아닙니다. 실제 CLI/MCP/benchmark-backed local knowledge substrate입니다.

하지만 아직 fully realized provenance-aware, agent-native knowledge product도 아닙니다.

즉 다음 phase의 핵심은 “처음부터 다시 만들기”가 아니라,
**이미 강한 backend/research substrate를 더 coherent하고 trustworthy한 knowledge system으로 끌어올리는 것**입니다.
