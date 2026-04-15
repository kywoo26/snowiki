# Step 2 Analysis Notes

## Current wiring map

### Runtime search path (non-Kiwi)
- `src/snowiki/search/tokenizer.py` — runtime lexical tokenizer; regex + NFKC normalization.
- `src/snowiki/search/indexer.py` — inverted index that tokenizes title/path/summary/content with the runtime tokenizer.
- `src/snowiki/search/workspace.py` — builds runtime retrieval snapshot; **no Kiwi seam here**.

### Benchmark-only Kiwi path
- `src/snowiki/search/kiwi_tokenizer.py` — defines `KoreanTokenizer` and `BilingualTokenizer`.
- `src/snowiki/search/bm25_index.py` — **the only place Kiwi is injected** into search.
  - When `use_kiwi_tokenizer=True`, builds a `KoreanTokenizer`.
  - Appends Kiwi tokens to `bm25s` corpus/query tokens.
  - Persists `use_kiwi_tokenizer` + `kiwi_lexical_candidate_mode` in metadata.

### Benchmark harness tokenizer swap
- `src/snowiki/bench/presets.py` — selects baseline names only.
- `src/snowiki/bench/baselines.py` — maps baseline names to Kiwi modes:
  - `bm25s_kiwi_nouns` → `nouns`
  - `bm25s_kiwi_full` / `bm25s_kiwi_morphology` → `morphology` (aliases)
- `src/snowiki/cli/commands/benchmark.py` — exposes only `--preset`; **no CLI tokenizer strategy knob**.

## Test coverage assessment

### Strong coverage
- Korean-only unit/integration:
  - `tests/search/test_kiwi_tokenizer.py`
  - `tests/search/test_kiwi_tokenizer_integration.py`
  - `tests/search/test_bm25_index.py`
  - `tests/search/test_bm25_index_integration.py`

### Weak coverage
- **Mixed-language tokenization**: `BilingualTokenizer` is only smoke-tested on Korean text and an all-English case that returns empty output. No test exercises true Korean+English mixed segmentation.
- **Cross-tokenizer quality comparison**: benchmark slices report `ko`/`en`/`mixed`, but there are no assertions comparing quality deltas *across tokenizers* on mixed-language queries.
- **Runtime/benchmark parity**: runtime search and benchmark search use different tokenization stacks, so comparability is not guaranteed by tests.

## Gaps to close before selection

1. **True mixed-language test corpus and assertions**
   - Need dedicated tests for `BilingualTokenizer` (or its replacement) on Korean+English+code mixed input.
2. **Extensible tokenizer registry**
   - Current benchmark only supports hardcoded baseline names. A registry/factory would let us add Kkma/Okt/Lindera candidates cleanly.
3. **Runtime tokenizer abstraction**
   - Decide whether to:
     - A) Promote one tokenizer to runtime default, or
     - B) Introduce a pluggable tokenizer interface in `workspace.py` / `indexer.py` so multiple strategies can coexist.
4. **Quality delta measurement**
   - Need automated reporting of Recall@k / MRR / nDCG differences between candidates on mixed-language slices.

## External patterns — detailed comparison

### `vlwkaos/ir` — standalone preprocessor executables
- Korean preprocessing is a **standalone executable** (`preprocessors/ko/lindera-tokenize`).
- Protocol: read UTF-8 stdin **line by line**, emit **one output line per input line**, keep empty lines empty, fallback to original line on tokenizer error.
- Uses embedded `ko-dic`, `Mode::Decompose`, filters to content morphemes only.
- Subprocess contract: write line → flush → read one line back.
- **Limitation**: command strings are split on whitespace, so paths with spaces are unsupported.
- Install/bind flow: `ko` is a bundled binary, install supports **macOS/Linux x86_64+aarch64** only.
- Schema metadata stores `has_preprocessor` so FTS is rebuilt when preprocessing changes.

### `seCall` — in-process tokenizer abstraction
- `Tokenizer::tokenize()` returns `Vec<String>`.
- **Lindera path**: embedded `ko-dic`, `Mode::Normal`, keep `NNG/NNP/NNB/VV/VA/SL`, lowercase, drop 1-char tokens, fallback to whitespace tokenization.
- **Kiwi path**: compiled only on **non-Windows** and **non-Linux-aarch64**, wrapped in `Mutex`, initialized via `Kiwi::init()`.
- Falls back to Lindera when Kiwi init/tokenization fails or platform is unsupported.
- User config: `search.tokenizer` only allows `lindera|kiwi`; Windows warns Kiwi is unsupported.

### `bab2min/Kiwi` / `kiwi-rs`
- Upstream Kiwi ships prebuilt binaries for **Windows/Linux/macOS/Android**; Linux source build needs CMake + Git LFS.
- `kiwi-rs` (Rust binding) supports three init modes:
  - `Kiwi::init()` — bootstrap/download into cache (needs `curl`, `tar`, `powershell` on Windows)
  - `Kiwi::new()` — env-managed paths
  - `Kiwi::from_config()` — explicit pinned paths
- Production docs prefer `new`/`from_config` over `init()` to avoid hidden global singletons.
- UTF-8 offsets are **character indices**, not byte offsets.

## Recommendation for Snowiki

1. **Pluggable by default.** Lindera is the safest baseline; Kiwi should be an opt-in quality backend, not a hard dependency.
2. **Return structured tokens**, not `Vec<String>`: surface, tag, start/end char offsets, backend name/version. Kiwi already exposes char-index semantics; current `ir`/`seCall` string-only flows throw that away.
3. **Support both in-process and exec adapters.** If subprocess backends are used, store `program + argv` (not a shell string) to avoid whitespace-splitting bugs.
4. **Persist backend/version per collection and invalidate on change.** Follow `ir`’s `has_preprocessor` flag pattern.
5. **Fail open at query time, fail loud at index time.** Search can degrade to raw tokenization; indexing should record the fallback so collections can be rebuilt deterministically.

## File references
- `src/snowiki/search/kiwi_tokenizer.py` — Kiwi-backed tokenizers
- `src/snowiki/search/bm25_index.py` — Kiwi injection point
- `src/snowiki/search/tokenizer.py` — runtime lexical tokenizer (non-Kiwi)
- `src/snowiki/bench/baselines.py` — baseline-to-Kiwi-mode mapping
- `src/snowiki/cli/commands/benchmark.py` — benchmark CLI surface
- `tests/search/test_kiwi_tokenizer.py` — tokenizer unit tests
- `tests/search/test_bm25_index.py` — BM25 + Kiwi integration tests
- `benchmarks/queries.json` — benchmark query corpus with `mixed` group
