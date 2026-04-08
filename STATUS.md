# Snowiki V2 - Status Report

## ✅ 완료된 작업

### 1. Python 3.14 업그레이드
- pyproject.toml: requires-python >=3.14
- basedpyright: pythonVersion 3.14

### 2. 저장소 중앙집중화 (~/.snowiki)
- Karpathy 철학: 모든 세션/프로젝트의 지식을 한 곳에
- 환경변수 SNOWIKI_ROOT로 오버라이드 가능
- CLI --root 옵션 지원

### 3. 형상관리 정리
- ✅ raw/, normalized/, compiled/, index/ → .gitignore
- ✅ 프로젝트 디렉토리에서 생성된 파일 정리
- ✅ ~/.snowiki에 실제 데이터 저장

### 4. 테스트 통과
- 131 passed, 26 subtests passed

## 🔧 진행 중인 작업

### Quality 향상 TODO
- [ ] Fix Claude adapter fixture mismatch
- [ ] Fix retrieval benchmark JSON shape mismatch  
- [ ] Register mcp/daemon commands in CLI main.py
- [ ] Add missing evidence files
- [ ] Remove/fix 326 Any types
- [ ] Fix MCP circular imports
- [ ] Add 219 missing docstrings
- [ ] Improve test coverage 71% → 90%+

## 📝 AGENTS.md 개선 필요사항

## ⚙️ Tooling 결정사항

### ty (Astral) vs basedpyright
- ty: Rust 기반, 10-100x faster, beta (0.0.x)
- basedpyright: 안정적, strict mode, 현재 사용 중

**제안**: basedpyright 유지 + ty 추가 (optional, 향후 전환 고려)
