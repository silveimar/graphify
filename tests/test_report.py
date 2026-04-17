import json
from datetime import date
from pathlib import Path
import networkx as nx
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections
from graphify.report import generate, render_analysis, _compute_hot_cold

FIXTURES = Path(__file__).parent / "fixtures"

def make_inputs():
    extraction = json.loads((FIXTURES / "extraction.json").read_text())
    G = build_from_json(extraction)
    communities = cluster(G)
    cohesion = score_all(G, communities)
    labels = {cid: f"Community {cid}" for cid in communities}
    gods = god_nodes(G)
    surprises = surprising_connections(G)
    detection = {"total_files": 4, "total_words": 62400, "needs_graph": True, "warning": None}
    tokens = {"input": extraction["input_tokens"], "output": extraction["output_tokens"]}
    return G, communities, cohesion, labels, gods, surprises, detection, tokens

def test_report_contains_header():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "# Graph Report" in report

def test_report_contains_corpus_check():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "## Corpus Check" in report

def test_report_contains_god_nodes():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "## God Nodes" in report

def test_report_contains_surprising_connections():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "## Surprising Connections" in report

def test_report_contains_communities():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "## Communities" in report

def test_report_contains_ambiguous_section():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "## Ambiguous Edges" in report

def test_report_shows_token_cost():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "Token cost" in report
    assert "1,200" in report

def test_report_shows_raw_cohesion_scores():
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "Cohesion:" in report
    assert "✓" not in report
    assert "⚠" not in report


# --- render_analysis tests ---

def make_lens_results():
    return [
        {
            "lens": "security",
            "verdict": "Clean",
            "confidence": 1.0,
            "confidence_label": "high",
            "findings_text": "No security issues found.",
            "voting_rationale": "3-0 unanimous for incumbent.",
            "top_finding": "",
            "incumbent_summary": "No security issues detected in the graph.",
            "adversary_summary": "Agreed with incumbent assessment.",
            "synthesis_summary": "Confirmed clean security posture.",
            "scores": {"A": 6, "B": 0, "AB": 0},
        },
        {
            "lens": "architecture",
            "verdict": "Finding",
            "confidence": 0.67,
            "confidence_label": "medium",
            "findings_text": "God node X is overloaded with 42 connections spanning 5 communities.",
            "voting_rationale": "2-1 for synthesis over incumbent.",
            "top_finding": "God node X overloaded",
            "incumbent_summary": "Minor coupling concerns.",
            "adversary_summary": "X is a critical bottleneck risk.",
            "synthesis_summary": "God node X is overloaded with 42 connections spanning 5 communities.",
            "scores": {"A": 2, "B": 1, "AB": 3},
        },
        {
            "lens": "complexity",
            "verdict": "Clean",
            "confidence": 1.0,
            "confidence_label": "high",
            "findings_text": "No complexity issues found.",
            "voting_rationale": "3-0 unanimous for incumbent.",
            "top_finding": "",
            "incumbent_summary": "Complexity is well-managed.",
            "adversary_summary": "No compelling counter-argument.",
            "synthesis_summary": "Confirmed manageable complexity.",
            "scores": {"A": 6, "B": 0, "AB": 0},
        },
        {
            "lens": "onboarding",
            "verdict": "Finding",
            "confidence": 0.67,
            "confidence_label": "medium",
            "findings_text": "Community 3 has no entry point for newcomers.",
            "voting_rationale": "2-1 for adversary over incumbent.",
            "top_finding": "Community 3 has no entry point for newcomers.",
            "incumbent_summary": "Onboarding paths exist.",
            "adversary_summary": "Community 3 has no entry point for newcomers.",
            "synthesis_summary": "Most communities are accessible but Community 3 lacks entry points.",
            "scores": {"A": 1, "B": 3, "AB": 2},
        },
    ]


def test_render_analysis_returns_str():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert isinstance(out, str)


def test_render_analysis_contains_header():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "# Graph Analysis" in out


def test_render_analysis_contains_date():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert date.today().isoformat() in out


def test_render_analysis_contains_each_lens_section():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "## Security" in out
    assert "## Architecture" in out


def test_render_analysis_clean_verdict_shows_clean():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "**Verdict:** Clean" in out


def test_render_analysis_clean_verdict_shows_rationale():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "3-0 unanimous" in out


def test_render_analysis_finding_verdict_shows_findings():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "God node X is overloaded with 42 connections spanning 5 communities." in out


def test_render_analysis_all_lenses_always_appear():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "## Security" in out
    assert "## Architecture" in out
    assert "## Complexity" in out
    assert "## Onboarding" in out


def test_render_analysis_contains_cross_lens_synthesis():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "## Cross-Lens Synthesis" in out


def test_render_analysis_contains_overall_verdict():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "## Overall Verdict" in out


def test_render_analysis_contains_tournament_rationale():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert out.count("### Tournament Rationale") >= 1


def test_render_analysis_contains_top_finding():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "God node X overloaded" in out


def test_render_analysis_convergences_section():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "### Convergences" in out


def test_render_analysis_tensions_section():
    results = make_lens_results()
    out = render_analysis(results, "myproject", ["security", "architecture", "complexity", "onboarding"])
    assert "### Tensions" in out


# --- _sanitize_md coverage via render_analysis (T-09-01) ---

def _make_malicious_lens_result(field: str, payload: str) -> dict:
    """Return a Finding lens result with `payload` injected into the named field."""
    base = {
        "lens": "security",
        "verdict": "Finding",
        "confidence": 0.67,
        "confidence_label": "medium",
        "findings_text": "clean",
        "voting_rationale": "clean",
        "top_finding": "clean",
        "incumbent_summary": "clean",
        "adversary_summary": "clean",
        "synthesis_summary": "clean",
        "scores": {"A": 2, "B": 3, "AB": 1},
    }
    base[field] = payload
    return base


def test_sanitize_md_backtick_stripped_from_findings_text():
    """Backticks in findings_text must not appear in rendered output (T-09-01)."""
    result = _make_malicious_lens_result("findings_text", "run `rm -rf /` now")
    out = render_analysis([result], "proj", ["security"])
    assert "`" not in out


def test_sanitize_md_angle_brackets_escaped_in_findings_text():
    """Angle brackets in findings_text must be HTML-escaped in rendered output (T-09-01)."""
    result = _make_malicious_lens_result("findings_text", "<script>alert(1)</script>")
    out = render_analysis([result], "proj", ["security"])
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_sanitize_md_backtick_stripped_from_voting_rationale():
    """Backticks in voting_rationale must not appear in rendered output (T-09-01)."""
    result = _make_malicious_lens_result("voting_rationale", "verdict: `override`")
    out = render_analysis([result], "proj", ["security"])
    assert "`" not in out


def test_sanitize_md_angle_brackets_escaped_in_voting_rationale():
    """Angle brackets in voting_rationale must be HTML-escaped (T-09-01)."""
    result = _make_malicious_lens_result("voting_rationale", "<b>bold injection</b>")
    out = render_analysis([result], "proj", ["security"])
    assert "<b>" not in out
    assert "&lt;b&gt;" in out


def test_sanitize_md_backtick_stripped_from_top_finding():
    """Backticks in top_finding must not appear in the Overall Verdict section (T-09-01)."""
    result = _make_malicious_lens_result("top_finding", "`code block injection`")
    out = render_analysis([result], "proj", ["security"])
    assert "`" not in out


def test_sanitize_md_angle_brackets_escaped_in_top_finding():
    """Angle brackets in top_finding must be HTML-escaped in the Overall Verdict section (T-09-01)."""
    result = _make_malicious_lens_result("top_finding", "<h1>heading injection</h1>")
    out = render_analysis([result], "proj", ["security"])
    assert "<h1>" not in out
    assert "&lt;h1&gt;" in out


def test_sanitize_md_backtick_stripped_from_incumbent_summary():
    """Backticks in incumbent_summary must not appear in rendered output (T-09-01)."""
    result = _make_malicious_lens_result("incumbent_summary", "says `eval(x)` is safe")
    out = render_analysis([result], "proj", ["security"])
    assert "`" not in out


def test_sanitize_md_angle_brackets_escaped_in_adversary_summary():
    """Angle brackets in adversary_summary must be HTML-escaped (T-09-01)."""
    result = _make_malicious_lens_result("adversary_summary", "<img src=x onerror=alert()>")
    out = render_analysis([result], "proj", ["security"])
    assert "<img" not in out
    assert "&lt;img" in out


def test_sanitize_md_backtick_stripped_from_synthesis_summary():
    """Backticks in synthesis_summary must not appear in rendered output (T-09-01)."""
    result = _make_malicious_lens_result("synthesis_summary", "use `sudo` carefully")
    out = render_analysis([result], "proj", ["security"])
    assert "`" not in out


def test_sanitize_md_angle_brackets_escaped_in_synthesis_summary():
    """Angle brackets in synthesis_summary must be HTML-escaped (T-09-01)."""
    result = _make_malicious_lens_result("synthesis_summary", "<a href='x'>link</a>")
    out = render_analysis([result], "proj", ["security"])
    assert "<a href" not in out
    assert "&lt;a href" in out


def test_sanitize_md_all_fields_clean_when_injected_simultaneously():
    """All 6 LLM-sourced fields sanitized when all contain injection payloads simultaneously (T-09-01)."""
    result = {
        "lens": "security",
        "verdict": "Finding",
        "confidence": 0.5,
        "confidence_label": "low",
        "findings_text": "`backtick` and <b>bold</b>",
        "voting_rationale": "`tick` <i>italic</i>",
        "top_finding": "`top` <em>em</em>",
        "incumbent_summary": "`inc` <span>span</span>",
        "adversary_summary": "`adv` <div>div</div>",
        "synthesis_summary": "`syn` <p>para</p>",
        "scores": {"A": 2, "B": 3, "AB": 1},
    }
    out = render_analysis([result], "proj", ["security"])
    assert "`" not in out
    assert "<b>" not in out
    assert "<i>" not in out
    assert "<em>" not in out
    assert "<span>" not in out
    assert "<div>" not in out
    assert "<p>" not in out


# --- _compute_hot_cold tests (T-09.1-09) ---

def test_compute_hot_cold():
    """Hot/cold classification with 12+ edges uses percentile thresholds."""
    G = nx.Graph()
    edges = [
        ("a", "b"), ("c", "d"), ("e", "f"), ("g", "h"),
        ("i", "j"), ("k", "l"), ("m", "n"), ("o", "p"),
        ("q", "r"), ("s", "t"), ("u", "v"), ("w", "x"),
    ]
    for u, v in edges:
        G.add_edge(u, v)
    counters = {
        "a:b": 50, "c:d": 40, "e:f": 30, "g:h": 20,
        "i:j": 15, "k:l": 10, "m:n": 8, "o:p": 5,
        "q:r": 3, "s:t": 2, "u:v": 1, "w:x": 1,
    }
    result = _compute_hot_cold(G, counters)
    assert result["hot"], "hot list should not be empty"
    assert result["cold"], "cold list should not be empty"
    # Highest-count edge should be in hot
    hot_keys = [k for k, _ in result["hot"]]
    assert "a:b" in hot_keys
    # Lowest-count edges should be in cold
    cold_keys = [k for k, _ in result["cold"]]
    assert any(k in cold_keys for k in ("u:v", "w:x"))
    assert result["total_queries"] == sum(counters.values())


def test_compute_hot_cold_empty():
    """Empty counters return zeroed result with never_traversed count."""
    G = nx.Graph()
    G.add_edge("a", "b")
    G.add_edge("c", "d")
    result = _compute_hot_cold(G, {})
    assert result["total_queries"] == 0
    assert result["hot"] == []
    assert result["cold"] == []
    assert result["never_traversed"] >= 0


def test_compute_hot_cold_small_data():
    """Fewer than 10 entries uses max/min fallback without raising StatisticsError."""
    G = nx.Graph()
    G.add_edge("a", "b")
    G.add_edge("c", "d")
    G.add_edge("e", "f")
    counters = {"a:b": 10, "c:d": 5, "e:f": 1}
    result = _compute_hot_cold(G, counters)
    assert "hot" in result
    assert "cold" in result
    assert "never_traversed" in result
    assert "total_queries" in result
    assert result["total_queries"] == 16


# --- Usage Patterns section tests (T-09.1-10 through T-09.1-12) ---

def test_report_usage_patterns():
    """Usage Patterns section appears when usage_data with counters is provided."""
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    # Build counters from actual graph edges to get 12+ entries
    edge_keys = []
    for u, v in G.edges():
        key = f"{min(u, v)}:{max(u, v)}"
        edge_keys.append(key)
    counters = {}
    for i, key in enumerate(edge_keys):
        counters[key] = 50 - i * 3  # descending counts
    usage_data = {"counters": counters, "threshold": 5}
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project", usage_data=usage_data)
    assert "## Usage Patterns" in report
    assert "### Hot Paths" in report
    assert "Total edge traversals" in report


def test_report_no_usage_data():
    """generate() without usage_data kwarg produces no Usage Patterns section."""
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project")
    assert "## Usage Patterns" not in report


def test_report_usage_empty_counters():
    """Empty counters dict does not produce a Usage Patterns section."""
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    usage_data = {"counters": {}, "threshold": 5}
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project", usage_data=usage_data)
    assert "## Usage Patterns" not in report


def test_hot_paths_labels():
    """Hot Paths table uses node labels, not raw IDs."""
    G, communities, cohesion, labels, gods, surprises, detection, tokens = make_inputs()
    # Pick two connected nodes and set their labels
    edges = list(G.edges())
    u, v = edges[0]
    G.nodes[u]["label"] = "MyClassA"
    G.nodes[v]["label"] = "MyClassB"
    key = f"{min(u, v)}:{max(u, v)}"
    # Make this edge the hottest with 12+ entries
    counters = {key: 100}
    for uu, vv in edges[1:]:
        k = f"{min(uu, vv)}:{max(uu, vv)}"
        counters[k] = 1
    usage_data = {"counters": counters, "threshold": 5}
    report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, "./project", usage_data=usage_data)
    assert "MyClassA" in report
    assert "MyClassB" in report


# --- Entity Dedup section tests (Phase 10, D-04 / T-10-02) ---

def _make_minimal_graph():
    """Minimal graph fixture for dedup section tests."""
    G = nx.Graph()
    G.add_node("n1", label="A", file_type="code", source_file="a.py", community=0)
    return G


def test_generate_no_dedup_section_when_none(tmp_path):
    """Omitting dedup_report (default None) produces no Entity Dedup section."""
    G = _make_minimal_graph()
    out = generate(
        G=G,
        communities={0: ["n1"]},
        cohesion_scores={0: 1.0},
        community_labels={0: "C0"},
        god_node_list=[],
        surprise_list=[],
        detection_result={"files": {"code": ["a.py"]}, "total_files": 1, "total_words": 100, "needs_graph": True, "warning": None},
        token_cost={"total": 0},
        root=str(tmp_path),
        # dedup_report omitted -> defaults to None
    )
    assert "## Entity Dedup" not in out


def test_generate_no_dedup_section_when_empty(tmp_path):
    """dedup_report with zero merges does not render the Entity Dedup section."""
    G = _make_minimal_graph()
    empty_report = {
        "version": "1",
        "summary": {"total_nodes_before": 1, "total_nodes_after": 1, "merges": 0},
        "alias_map": {},
        "merges": [],
    }
    out = generate(
        G=G,
        communities={0: ["n1"]},
        cohesion_scores={0: 1.0},
        community_labels={0: "C0"},
        god_node_list=[],
        surprise_list=[],
        detection_result={"files": {"code": ["a.py"]}, "total_files": 1, "total_words": 100, "needs_graph": True, "warning": None},
        token_cost={"total": 0},
        root=str(tmp_path),
        dedup_report=empty_report,
    )
    assert "## Entity Dedup" not in out


def test_generate_renders_dedup_section_with_merges(tmp_path):
    """Populated dedup_report appends a sanitized Entity Dedup section."""
    G = _make_minimal_graph()
    populated_report = {
        "version": "1",
        "summary": {"total_nodes_before": 3, "total_nodes_after": 1, "merges": 1},
        "alias_map": {"n2": "n1", "n3": "n1"},
        "merges": [{
            "canonical_id": "n1",
            "canonical_label": "AuthService",
            "eliminated": [
                {"id": "n2", "label": "auth_service", "source_file": "b.py"},
                {"id": "n3", "label": "Auth", "source_file": "c.py"},
            ],
            "fuzzy_score": 0.957,
            "cosine_score": 0.912,
        }],
    }
    out = generate(
        G=G,
        communities={0: ["n1"]},
        cohesion_scores={0: 1.0},
        community_labels={0: "C0"},
        god_node_list=[],
        surprise_list=[],
        detection_result={"files": {"code": ["a.py"]}, "total_files": 1, "total_words": 100, "needs_graph": True, "warning": None},
        token_cost={"total": 0},
        root=str(tmp_path),
        dedup_report=populated_report,
    )
    assert "## Entity Dedup" in out
    assert "AuthService" in out
    assert "auth_service" in out
    assert "fuzzy=0.957" in out
    assert "cos=0.912" in out
    # Summary line present
    assert "3 nodes" in out and "1 nodes" in out


def test_generate_dedup_section_sanitizes_labels(tmp_path):
    """T-10-02: HTML/markdown injection attempts in canonical labels are neutralized."""
    G = _make_minimal_graph()
    evil_report = {
        "version": "1",
        "summary": {"total_nodes_before": 2, "total_nodes_after": 1, "merges": 1},
        "alias_map": {"n2": "n1"},
        "merges": [{
            "canonical_id": "n1",
            "canonical_label": "<script>alert(1)</script>",
            "eliminated": [{"id": "n2", "label": "<img src=x>", "source_file": "b.py"}],
            "fuzzy_score": 0.95,
            "cosine_score": 0.90,
        }],
    }
    out = generate(
        G=G,
        communities={0: ["n1"]},
        cohesion_scores={0: 1.0},
        community_labels={0: "C0"},
        god_node_list=[],
        surprise_list=[],
        detection_result={"files": {"code": ["a.py"]}, "total_files": 1, "total_words": 100, "needs_graph": True, "warning": None},
        token_cost={"total": 0},
        root=str(tmp_path),
        dedup_report=evil_report,
    )
    # Raw < / > must not appear in dedup section (sanitized to &lt;/&gt;)
    section_start = out.index("## Entity Dedup")
    section = out[section_start:]
    assert "<script>" not in section
    assert "<img" not in section
    assert "&lt;script&gt;" in section or "[script]" not in section
    # Canonical content still present in escaped form
    assert "alert" in section


def test_generate_dedup_section_truncates_above_10():
    """More than 10 merges: only first 10 rendered, overflow line appears."""
    G = _make_minimal_graph()
    merges = [{
        "canonical_id": f"n{i}",
        "canonical_label": f"Label{i}",
        "eliminated": [{"id": f"x{i}", "label": f"elim{i}", "source_file": "x.py"}],
        "fuzzy_score": 0.95,
        "cosine_score": 0.90,
    } for i in range(15)]
    report = {
        "version": "1",
        "summary": {"total_nodes_before": 30, "total_nodes_after": 15, "merges": 15},
        "alias_map": {},
        "merges": merges,
    }
    out = generate(
        G=G,
        communities={0: ["n1"]},
        cohesion_scores={0: 1.0},
        community_labels={0: "C0"},
        god_node_list=[],
        surprise_list=[],
        detection_result={"files": {"code": ["a.py"]}, "total_files": 1, "total_words": 100, "needs_graph": True, "warning": None},
        token_cost={"total": 0},
        root=".",
        dedup_report=report,
    )
    # First 10 labels present
    for i in range(10):
        assert f"Label{i}" in out
    # Overflow line present
    assert "+5 more" in out
    # 11th-15th labels NOT in the rendered section
    section_start = out.index("## Entity Dedup")
    section = out[section_start:]
    assert "Label14" not in section
