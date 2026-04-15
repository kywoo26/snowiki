# qmd lineage와 Korean strategy

## 목적

이 문서는 두 가지를 다룹니다.
1. Snowiki가 qmd 및 인접 lineage로부터 무엇을 계승해야 하는가
2. Korean / mixed-language retrieval을 semantic/vector 이전에 어떻게 다뤄야 하는가

## evidence note

이 문서는 다음을 바탕으로 한 design-oriented research synthesis입니다.
- qmd의 visible public positioning (local retrieval substrate)
- qmd가 Snowiki lineage와 roadmap 논의에서 차지하는 역할
- Snowiki 로컬 코드/benchmark surface, 특히 현재 lexical backbone과 `kiwi_tokenizer.py`의 존재
- 아래 evidence appendix에 기록한 concrete artifact

즉 학술적으로 완전한 Korean IR survey가 아니라, **설계 결정을 돕는 문서**입니다.

따라서:
- qmd의 역할에 대한 서술은 visible retrieval posture와 Snowiki의 design history를 바탕으로 하고
- Korean strategy에 대한 서술은 일부는 직접 근거(현재 코드 구조), 일부는 design inference(다음에 무엇을 benchmark해야 하는가)입니다.
- recommendation은 현재 verified fact와 구분해서 읽어야 합니다.

## qmd의 위치

qmd는 Snowiki에 중요하지만, 역할이 명확해야 합니다.

qmd는 **retrieval substrate reference**이지, Snowiki의 full product blueprint가 아닙니다.

### qmd로부터 계승할 것
- lexical-first discipline
- local-first operation
- optional hybrid / rerank posture
- retrieval을 evidence-producing subsystem으로 다루는 태도

### qmd로부터 그대로 가져오면 안 되는 것
- product identity를 search engine으로 축소하는 것
- provenance-aware compiled knowledge 문제를 retrieval 하나로 치환하는 것

즉:
> Snowiki는 qmd의 retrieval seriousness를 계승하되, “search engine only”로 붕괴하면 안 됩니다.

## Korean retrieval에 대한 현재 결론

현재 Korean retrieval은 **lexical/tokenization 문제로 먼저 다루는 게 맞습니다.**

즉 지금 바로 필요한 질문은:
- Korean text를 어떻게 tokenization할 것인가
- mixed Korean-English를 어떻게 처리할 것인가
- lexical strategy 중 어떤 것이 benchmark slice에서 실제로 이기는가

이것이지, 곧바로 semantic/vector를 넣는 것이 아닙니다.

## 핵심 Korean design question

### 1. current tokenizer vs Kiwi-backed morphology
가장 먼저 benchmark해야 하는 질문입니다.

비교 대상:
- 현재 tokenizer
- Kiwi-backed morphological tokenization

비교 맥락:
- Korean-only retrieval
- mixed Korean-English retrieval
- known-item vs topical retrieval

### 2. noun-heavy vs broader morphology
한국어 retrieval 품질은 명사 위주로 자를지, 더 넓은 morphology를 허용할지에 따라 크게 달라질 수 있습니다.

이건 반드시 benchmark question으로 다뤄야 합니다.

### 3. exact surface vs normalized form
aggressive normalization은 recall을 높일 수 있지만 precision이나 snippet trust를 해칠 수 있습니다.

provenance-aware system에서는 이 점이 특히 중요합니다.

### 4. mixed-language retrieval
Snowiki는 Korean retrieval을 Korean-only 문제로 보면 안 됩니다.

실제 note는 보통:
- 한국어 prose
- English identifier
- library name
- file path
- code literal
이 같이 들어 있습니다.

따라서 진짜 benchmark 대상은 **mixed-language lexical retrieval**입니다.

## 지금 해야 할 것 / 하지 말아야 할 것

### Keep
- lexical-first retrieval backbone
- qmd-like retrieval discipline

### Avoid
- vectors를 Korean retrieval의 default 답으로 취급하기
- 하나의 Korean tokenizer가 항상 정답이라고 가정하기
- Korean strategy를 mixed-language 현실과 분리하기

### Research later
- selectable Korean strategy가 필요한지
- Korean lexical 개선이 future hybrid retrieval과 어떻게 상호작용하는지
- lexical을 충분히 소진한 뒤 semantic layer가 정당화되는지

## bottom line

Snowiki는 qmd를 retrieval lineage로 취급해야 하고, Korean retrieval은 semantic/vector 이전에 **benchmark된 lexical design problem**으로 다뤄야 합니다.

## evidence appendix

Reviewed as of: 2026-04-12

### qmd evidence basis
- URL: https://github.com/tobi/qmd
- inspected artifacts: public repository positioning and qmd의 visible local retrieval/search framing
- supports:
  - qmd를 retrieval substrate로 보는 판단
  - lexical-first / local-first retrieval discipline
  - optional hybrid/rerank posture를 later sophistication layer로 두는 판단

### Korean strategy evidence basis
- current active runtime evidence:
  - `src/snowiki/search/indexer.py`
  - `src/snowiki/search/tokenizer.py`
  - `src/snowiki/search/workspace.py`
  - `src/snowiki/cli/commands/query.py`
  - `src/snowiki/cli/commands/recall.py`
- adjacent Korean-specific evidence:
  - `src/snowiki/search/kiwi_tokenizer.py`
- mixed-language concern evidence:
  - retrieval architecture and retrieval-focused integration tests
- supports:
  - current runtime은 lexical-first임
  - Kiwi는 adjacent strategy candidate이지 default runtime path가 아님
  - semantic/vector escalation 전에 Korean lexical benchmark가 우선이라는 판단

### how to read
- 이 정도 근거는 roadmap/architecture sequencing에는 충분합니다.
- 나중에 current tokenizer vs Kiwi-backed default 같은 concrete lexical decision을 내릴 때는 별도 benchmark/result 문서가 필요합니다.

## Traceability: evidence → conclusion → roadmap consequence

### qmd는 identity가 아니라 lineage
- evidence: qmd의 public posture는 substrate-oriented이고 local retrieval 중심입니다.
- conclusion: Snowiki는 qmd의 retrieval discipline을 계승하되, product identity 전체를 qmd와 동일시하면 안 됩니다.
- roadmap consequence: qmd는 retrieval strategy와 discipline을 inform하지만 Snowiki product identity의 full template는 아닙니다.

### Korean retrieval은 lexical-first여야 함
- evidence: Snowiki의 shipped runtime은 lexical-first이고, Kiwi는 adjacent candidate path로만 존재합니다.
- conclusion: 다음 Korean 관련 작업은 benchmark-driven lexical/tokenization evaluation이어야 합니다.
- roadmap consequence: semantic/hybrid implementation보다 Korean and mixed-language lexical benchmark가 앞섭니다.
