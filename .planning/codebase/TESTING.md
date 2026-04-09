# Testing Patterns

**Analysis Date:** 2026-04-09

## Test Framework

**Runner:**
- pytest (no version pinned in pyproject.toml, uses latest)
- CI: runs on Python 3.10 and 3.12 (see pyproject.toml and CLAUDE.md)

**Run Commands:**
```bash
pytest tests/ -q                  # Run all tests, quiet mode
pytest tests/test_extract.py -q   # Run single test file
pytest tests/test_extract.py::test_make_id_strips_dots_and_underscores -q  # Run single test
```

**Assertion Library:**
- pytest's built-in assertions (no external library)
- Direct equality: `assert x == y`
- Membership: `assert x in y`
- Exception checking: `with pytest.raises(ValueError, match="pattern"): ...`

**Test Coverage:**
- No coverage requirement enforced
- No coverage configuration file detected
- Tests are functional/integration-style rather than coverage-focused

## Test File Organization

**Location:**
- Co-located by module: `tests/test_extract.py` tests `graphify/extract.py`
- Shared fixtures in `tests/fixtures/` (sample files: `sample.py`, `sample.ts`, `sample.go`, etc.)
- One test file per module (not split by class or feature)

**Naming:**
- Test functions: `test_<what_is_being_tested>()`
- Examples:
  - `test_make_id_strips_dots_and_underscores()`
  - `test_extract_python_finds_class()`
  - `test_validate_url_accepts_https()`
  - `test_safe_fetch_raises_on_non_2xx()`

**Structure:**
```
tests/
├── __init__.py
├── fixtures/
│   ├── sample.py           # Python fixture
│   ├── sample.ts           # TypeScript fixture
│   ├── sample.go           # Go fixture
│   ├── sample.java         # Java fixture
│   ├── sample_calls.py     # Call graph test fixture
│   ├── sample.md           # Markdown document fixture
│   └── extraction.json     # Pre-built extraction result
├── test_extract.py         # 170 lines, 50+ tests
├── test_build.py           # Tests graph assembly
├── test_detect.py          # File discovery and classification
├── test_security.py        # 189 lines, URL/fetch validation
├── test_validate.py        # Schema validation
├── test_cluster.py         # Community detection
├── test_languages.py       # 510 lines, language-specific extractors
├── test_multilang.py       # 173 lines, JS/Go/Rust cross-lang tests
├── test_analyze.py         # God nodes, surprises, questions
├── test_wiki.py            # Wiki generation
├── test_watch.py           # File watching
└── ... (20+ test files total)
```

## Test Structure

**Suite Organization:**
All tests are organized as independent test functions (not classes). Pytest fixtures used only when needed.

**Example from `test_extract.py`:**
```python
from pathlib import Path
from graphify.extract import extract_python, extract, collect_files, _make_id

FIXTURES = Path(__file__).parent / "fixtures"

def test_make_id_strips_dots_and_underscores():
    assert _make_id("_auth") == "auth"
    assert _make_id(".httpx._client") == "httpx_client"

def test_make_id_consistent():
    """Same input always produces same output."""
    assert _make_id("foo", "Bar") == _make_id("foo", "Bar")

def test_extract_python_finds_class():
    result = extract_python(FIXTURES / "sample.py")
    labels = [n["label"] for n in result["nodes"]]
    assert "Transformer" in labels

def test_extract_python_no_dangling_edges():
    """All edge sources must reference a known node (targets may be external imports)."""
    result = extract_python(FIXTURES / "sample.py")
    node_ids = {n["id"] for n in result["nodes"]}
    for edge in result["edges"]:
        assert edge["source"] in node_ids, f"Dangling source: {edge['source']}"
```

**Patterns:**

1. **Setup via fixtures:** Load test data once, reuse in multiple tests
   ```python
   FIXTURES = Path(__file__).parent / "fixtures"

   def make_graph():
       return build_from_json(json.loads((FIXTURES / "extraction.json").read_text()))

   def test_cluster_returns_dict():
       G = make_graph()
       communities = cluster(G)
       assert isinstance(communities, dict)
   ```

2. **Assertion messages:** Error messages clarify what went wrong
   ```python
   assert edge["source"] in node_ids, f"Dangling source: {edge['source']}"
   ```

3. **Descriptive docstrings:** Tests document intent
   ```python
   def test_extract_python_no_dangling_edges():
       """All edge sources must reference a known node (targets may be external imports)."""
   ```

4. **Input validation testing:** Comprehensive error cases
   ```python
   def test_validate_url_rejects_file():
       with pytest.raises(ValueError, match="file"):
           validate_url("file:///etc/passwd")

   def test_validate_url_rejects_ftp():
       with pytest.raises(ValueError, match="ftp"):
           validate_url("ftp://files.example.com/data.zip")
   ```

## Mocking

**Framework:** `unittest.mock` (Python stdlib)

**Patterns from `test_security.py`:**
```python
from unittest.mock import MagicMock, patch

def _make_mock_response(content: bytes, status: int = 200):
    """Create a mock HTTP response for testing safe_fetch."""
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.status = status
    mock.code = status
    chunks = [content[i:i+65536] for i in range(0, len(content), 65536)] + [b""]
    mock.read.side_effect = chunks
    return mock

def test_safe_fetch_returns_bytes(tmp_path):
    mock_resp = _make_mock_response(b"hello world")
    with patch("graphify.security._build_opener") as mock_opener_fn:
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp
        mock_opener_fn.return_value = mock_opener
        result = safe_fetch("https://example.com/")
    assert result == b"hello world"
```

**What to Mock:**
- Network calls: HTTP requests in `safe_fetch()` tests (use `patch()`)
- File I/O when testing data transformations (use `tmp_path`)
- External library calls (e.g., graspologic's leiden - mocked in output suppression tests)

**What NOT to Mock:**
- Real extractors - test with actual fixture files (sample.py, sample.ts, etc.)
- Graph construction - use real NetworkX graphs
- File discovery - use actual fixtures directory
- Language-specific parsing - test with real source files

## Fixtures and Factories

**Test Data (`tests/fixtures/`):**
- `sample.py`: Contains `Transformer` class with methods for testing Python extraction
- `sample_calls.py`: Functions with call relationships for call-graph testing
- `sample.ts`: TypeScript class with methods for JS/TS extraction
- `sample.go`: Go struct with methods for Go extraction
- `sample.java`: Java class/interface for Java extraction
- `sample.md`: Markdown document for document extraction
- `extraction.json`: Pre-built extraction result (nodes + edges) for graph tests

**Pattern from `test_extract.py`:**
```python
FIXTURES = Path(__file__).parent / "fixtures"

def test_extract_python_finds_class():
    result = extract_python(FIXTURES / "sample.py")
    # Test uses real file, not mocked
    labels = [n["label"] for n in result["nodes"]]
    assert "Transformer" in labels
```

**Pytest tmp_path fixture:**
Used for temporary file/directory creation in path validation and symbolic link tests:
```python
def test_collect_files_follows_symlinked_directory(tmp_path):
    real_dir = tmp_path / "real_src"
    real_dir.mkdir()
    (real_dir / "lib.py").write_text("x = 1")
    (tmp_path / "linked_src").symlink_to(real_dir)

    files_no = collect_files(tmp_path, follow_symlinks=False)
    files_yes = collect_files(tmp_path, follow_symlinks=True)

    assert [f.name for f in files_no].count("lib.py") == 1
    assert [f.name for f in files_yes].count("lib.py") == 2
```

## Coverage

**Requirements:** None enforced (no coverage configuration in pyproject.toml)

**Current state:** Tests focus on functional correctness rather than line coverage

**Test distribution (across 20+ files, ~3700 lines of test code):**
- Language extractors: 510 lines (test_languages.py)
- Extraction/AST: 170 lines (test_extract.py)
- Security/validation: 189 lines (test_security.py)
- Multi-language: 173 lines (test_multilang.py)
- Confidence scoring: 192 lines (test_confidence.py)
- Analysis (god nodes, surprises): 232 lines (test_analyze.py)
- Installation: 227 lines (test_install.py)
- Hypergraph: 205 lines (test_hypergraph.py)
- Other: detect, build, cluster, wiki, watch, serve, etc.

## Test Types

**Unit Tests (most common):**
- Small, focused, test one function
- Pure logic: `_make_id()`, `validate_url()`, `cohesion_score()`
- No side effects outside `tmp_path`
- Example:
  ```python
  def test_make_id_strips_dots_and_underscores():
      assert _make_id("_auth") == "auth"
  ```

**Integration Tests (language/file discovery):**
- Test multiple functions together: `extract()` integrates multiple extractors
- Use real fixture files
- Verify extraction schema is maintained
- Example from `test_multilang.py`:
  ```python
  def test_ts_no_dangling_edges():
      r = extract_js(FIXTURES / "sample.ts")
      node_ids = {n["id"] for n in r["nodes"]}
      for e in r["edges"]:
          if e["relation"] in ("contains", "method", "calls"):
              assert e["source"] in node_ids
  ```

**End-to-End Tests:**
- Not present in test suite (skill.md does E2E testing)
- Tests stop at graph construction and export formats
- Example: JSON/HTML/Obsidian export tested, but not full CLI flow

## Common Patterns

**Assertion helpers (define once, use many):**
```python
# From test_languages.py
def _labels(r):
    return [n["label"] for n in r["nodes"]]

def _relations(r):
    return {e["relation"] for e in r["edges"]}

def _calls(r):
    node_by_id = {n["id"]: n["label"] for n in r["nodes"]}
    return {
        (node_by_id.get(e["source"], e["source"]), node_by_id.get(e["target"], e["target"]))
        for e in r["edges"] if e["relation"] == "calls"
    }

# Usage
def test_java_finds_class():
    r = extract_java(FIXTURES / "sample.java")
    assert any("DataProcessor" in l for l in _labels(r))

def test_java_finds_imports():
    r = extract_java(FIXTURES / "sample.java")
    assert "imports" in _relations(r)
```

**Async Testing:**
- Not used (graphify is synchronous)

**Error Testing:**
Pattern: raise exceptions for invalid input, check with `pytest.raises()`
```python
def test_validate_url_rejects_file():
    with pytest.raises(ValueError, match="file"):
        validate_url("file:///etc/passwd")

def test_validate_graph_path_blocks_traversal(tmp_path):
    base = tmp_path / "graphify-out"
    base.mkdir()
    evil = tmp_path / "graphify-out" / ".." / "etc_passwd"
    with pytest.raises(ValueError, match="escapes"):
        validate_graph_path(str(evil), base=base)
```

**Parametrized tests (none detected):**
- No `@pytest.mark.parametrize()` used
- Instead: multiple assertions in one test or separate test functions per case
- Example:
  ```python
  def test_classify_python():
      assert classify_file(Path("foo.py")) == FileType.CODE

  def test_classify_typescript():
      assert classify_file(Path("bar.ts")) == FileType.CODE

  def test_classify_markdown():
      assert classify_file(Path("README.md")) == FileType.DOCUMENT
  ```

**Capsys for output testing:**
Used to verify functions don't leak output (important for cluster() and library integration):
```python
def test_cluster_does_not_write_to_stdout(capsys):
    """Clustering should not emit ANSI escape codes or other output."""
    G = make_graph()
    cluster(G)
    captured = capsys.readouterr()
    assert captured.out == "", f"cluster() wrote to stdout: {captured.out!r}"

def test_cluster_does_not_write_to_stderr(capsys):
    G = make_graph()
    cluster(G)
    captured = capsys.readouterr()
    for line in captured.err.splitlines():
        assert "\x1b" not in line, f"cluster() wrote ANSI to stderr: {line!r}"
```

## Data-Driven Tests

**Test fixtures as data:**
From `test_build.py`:
```python
VALID = {
    "nodes": [
        {"id": "n1", "label": "Foo", "file_type": "code", "source_file": "foo.py"},
        {"id": "n2", "label": "Bar", "file_type": "document", "source_file": "bar.md"},
    ],
    "edges": [
        {"source": "n1", "target": "n2", "relation": "references",
         "confidence": "EXTRACTED", "source_file": "foo.py", "weight": 1.0},
    ],
}

def test_valid_passes():
    assert validate_extraction(VALID) == []
```

---

*Testing analysis: 2026-04-09*
