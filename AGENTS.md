# Snowiki V2

Personal wiki that compounds knowledge like a snowball.

## Stack

- **Python**: 3.14+
- **Package Manager**: uv (always use `uv run`, never direct python)
- **Type Checker**: ty (primary)
- **Linter/Formatter**: ruff (E, F, I, N, W, UP, B, C4, SIM rules)
- **CLI Framework**: Click
- **Data Validation**: Pydantic v2
- **Testing**: pytest with coverage

## Commands

```bash
# Dependencies
uv sync --group dev

# Type checking
uv run ty check

# Linting
uv run ruff check snowiki tests
uv run ruff format snowiki tests

# Testing
uv run pytest
uv run pytest tests/cli/test_query.py -v

# CLI usage
uv run snowiki --help
uv run snowiki ingest <file> --source {claude|opencode}
uv run snowiki rebuild
uv run snowiki query "search terms"

# Verification
python -m compileall snowiki/
```

## Conventions

### Python Style
- Google style docstrings when documenting
- Explicit type hints on all function signatures
- Named exports, avoid `__all__` manipulation
- Keep functions under 50 lines when possible

### Example: Error Handling
```python
# Correct - explicit error types
def load_session(path: Path) -> Session:
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {path}")
    return Session.parse_raw(path.read_text())

# Wrong - bare except, no type hints
def load_session(path):
    try:
        return Session.parse_raw(open(path).read())
    except:  # never bare except
        return None
```

### Example: CLI Command Pattern
```python
@click.command("ingest")
@click.argument("path", type=click.Path(exists=True))
def command(path: Path) -> None:
    """Short description here."""
    root = get_snowiki_root()
    # implementation
```

## Storage Architecture

- **Centralized storage**: `~/.snowiki` (configurable via `SNOWIKI_ROOT`)
- **3-layer architecture**:
  - `raw/` - immutable source files
  - `normalized/` - canonical records (JSON)
  - `compiled/` - generated markdown wiki
  - `index/` - search indexes

## Boundaries

### ✅ Always
- Run `uv run ruff check` before committing
- Run `uv run pytest` for any logic changes
- Use explicit types, avoid `Any`
- Commit with descriptive messages

### ⚠️ Ask First
- Adding new dependencies to pyproject.toml
- Modifying storage layer interfaces
- Changing schema models
- Major CLI command signature changes

### 🚫 Never
- Commit secrets, API keys, or credentials
- Modify `~/.snowiki/raw/` directly (read-only)
- Use `print()` for logging (use proper logging)
- Skip tests for new features
- Modify generated files in `compiled/` or `index/`

## Key Files

- `snowiki/config.py` - Centralized ~/.snowiki configuration
- `snowiki/cli/main.py` - CLI entry point
- `snowiki/storage/` - 4-zone storage implementation
- `snowiki/adapters/` - Claude & OMO source adapters
- `snowiki/search/` - Bilingual lexical retrieval

## Testing Rules

- Unit tests alongside source in `tests/`
- Coverage target: 90%+
- Mock external dependencies (DB, filesystem)
- Use fixtures in `fixtures/` for test data
- Run full suite before PR: `uv run pytest`

## CI/Pre-commit

Pre-commit runs:
1. `ruff check --fix`
2. `ruff format`
3. `ty check`

Install: `uv run pre-commit install`
