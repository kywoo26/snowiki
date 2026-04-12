# Follow-up Program

## 목적

이 문서는 architecture와 research 결론을 바탕으로, 다음 큰 작업의 순서를 명시합니다.

`ROADMAP.md`보다 더 구체적이지만, 개별 execution plan보다는 넓습니다.

## 최근 완료된 작업
- canonical retrieval service hardening
- 첫 retrieval performance deep dive
- manual benchmark workflow ergonomics

즉 이 항목들은 이제 “다음 할 일”이라기보다, 이후 판단의 전제로 취급합니다.

## Ordered next work

### 1. Korean and mixed-language lexical benchmark
이유:
- Korean retrieval은 여전히 lexical/tokenization open question임
- semantic escalation 전에 lexical 전략을 충분히 검증해야 함

Non-goals:
- vector multilingual retrieval
- evidence 없는 mandatory Kiwi adoption

### 2. Skill contract and agent interface design
이유:
- 현재 install/use contract는 정렬됐지만 skill layer는 아직 patch-level cleanup 수준
- agent-facing contract는 문서가 아니라 설계 문제임

Non-goals:
- 제품 전체를 skill 중심으로 재작성하는 것
- qmd-oriented runtime claims를 현재 truth로 되돌리는 것

### 3. Search architecture hardening (next layer)
이유:
- retrieval contract가 canonicalized 된 이후, 다음 architecture work는 tokenization/indexing/evidence surface 경계를 더 분명히 하는 것임

Non-goals:
- semantic/vector implementation
- backend replacement

### 4. Semantic / hybrid retrieval exploration
이유:
- lexical-first가 현재 정답이지만, eventually semantic/hybrid의 실험과 gating이 필요함

Non-goals:
- semantic retrieval을 default runtime path로 premature하게 만드는 것
- backend swap을 사실상 밀어 넣는 것

## 아직 하지 말아야 할 것
- semantic/hybrid runtime implementation
- backend replacement
- local model lifecycle integration
- broad benchmark-system expansion
- old qmd-oriented workflow text를 product truth로 대하는 것

## 다음 우선순위를 고르는 법
다음을 물으면 됩니다.
1. 무엇이 가장 많은 다른 작업을 막는가
2. 무엇이 drift를 가장 줄이는가
3. 무엇이 evidence quality를 가장 올리는가
4. 무엇이 현재 가정을 깨지 않고 capability를 늘리는가

이 기준으로 보면,
**Korean/mixed-language lexical evaluation → skill/agent-interface design → next-layer retrieval hardening**
순서가 가장 자연스럽습니다.
