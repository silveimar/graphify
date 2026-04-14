import json
from datetime import date
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections
from graphify.report import generate, render_analysis

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
