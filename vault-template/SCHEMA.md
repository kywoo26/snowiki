# Snowiki Schema

LLM이 위키를 유지하기 위한 규칙서. 이 파일은 사람과 LLM이 함께 발전시킨다.

## 철학

- 사람은 소싱, 질문, 방향 설정, 사고를 한다
- LLM은 요약, 교차참조, 파일링, 일관성 유지를 한다
- sources/는 불변(immutable) — 진실의 원천
- wiki/는 LLM이 소유 — 컴파일된 지식
- 지식은 복리로 축적된다 — 눈덩이처럼

## Vault 구조

```
vault/
├── sources/              ← 불변 원본 (절대 수정 금지)
│   ├── articles/         ← 웹 클리핑, PDF
│   ├── sessions/         ← cc 세션 md
│   └── notes/            ← 수동 메모, 회의록
│
├── wiki/                 ← LLM이 유지하는 컴파일된 지식
│   ├── index.md          ← 전체 카탈로그 (자동 갱신)
│   ├── log.md            ← append-only 변경 기록
│   ├── concepts/         ← 단일 개념 (BM25, GGUF, MCP 등)
│   ├── topics/           ← 교차 주제 (한국어 NLP, WSL2 환경)
│   ├── decisions/        ← 기술 의사결정 (날짜 prefix)
│   ├── tools/            ← 도구 사용법
│   └── setup/            ← 시스템 구축 가이드
│
├── SCHEMA.md             ← 이 파일
└── .obsidian/
```

## 페이지 Frontmatter

모든 wiki/ 페이지에 필수:

```yaml
---
title: "페이지 제목"
type: concept | topic | decision | tool | guide
created: 2026-04-07
updated: 2026-04-07
sources:
  - "session:a68eb32b"
  - "article:karpathy-llm-wiki"
tags: [qmd, 검색, 한국어]
---
```

## 페이지 유형별 규칙

### concept (개념)
- 하나의 개념을 깊이 설명
- "이게 뭐야?"에 답하는 페이지
- 예: `concepts/bm25.md`, `concepts/gguf.md`

### topic (주제)
- 여러 개념이 교차하는 영역
- "이 분야는 어떻게 돌아가?"에 답하는 페이지
- 예: `topics/korean-search.md`, `topics/wsl2-dev-env.md`

### decision (의사결정)
- "왜 A를 선택하고 B를 버렸는가"
- 날짜 prefix: `decisions/2026-04-07-embedding-model.md`
- 반드시 포함: 선택지, 트레이드오프, 최종 결정, 근거

### tool (도구)
- 설치, 설정, 핵심 명령어
- 예: `tools/fzf.md`, `tools/qmd.md`

### guide (가이드)
- 단계별 절차
- 예: `setup/qmd-system/install-guide.md`

## 작성 규칙

### 하지 말 것
- sources/ 파일 수정 (절대 불변)
- 기존 wiki 내용 삭제 (업데이트/추가만)
- 근거 없는 주장 작성
- 모호한 요약 ("다양한 방법이 있다" 같은)

### 반드시 할 것
- 구체적 기술 정보 보존 (명령어, 에러 메시지, 수치)
- 모순 발견 시 `> ⚠️ 모순:` callout으로 표시 (삭제하지 말고)
- sources 배열에 참조 출처 기록
- 교차참조는 `[[wiki/concepts/bm25]]` wikilink 사용
- 코드/설정은 실제 동작 확인된 것만

### index.md 갱신
ingest 또는 페이지 생성/수정 시 반드시 갱신:
```markdown
- [페이지 제목](경로) — 한 줄 요약 `#태그1` `#태그2`
```

### log.md 기록
모든 변경에 append:
```markdown
## [2026-04-07] ingest | 소스 제목
- 생성: concepts/bm25.md, topics/korean-search.md
- 수정: index.md
- 요약: BM25 검색 방식과 한국어 형태소 분석 관계 정리
```

## Lint 규칙

주기적으로 점검해야 할 항목:

| 코드 | 검사 | 심각도 |
|------|------|--------|
| S001 | 고아 페이지 (inbound 링크 없음) | WARN |
| S002 | sources에서 wiki 미반영 항목 | INFO |
| S003 | frontmatter 불완전 (필수 필드 누락) | ERROR |
| S004 | 깨진 wikilink ([[존재하지 않는 페이지]]) | ERROR |
| S005 | 모순 표시(⚠️)가 3개 이상인 페이지 | WARN |
| S006 | 30일 이상 미갱신 페이지 | INFO |
