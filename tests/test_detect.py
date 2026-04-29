from pathlib import Path
from graphify.detect import classify_file, count_words, detect, FileType, _looks_like_paper, _is_ignored, _load_graphifyignore

FIXTURES = Path(__file__).parent / "fixtures"

def test_classify_python():
    assert classify_file(Path("foo.py")) == FileType.CODE

def test_classify_typescript():
    assert classify_file(Path("bar.ts")) == FileType.CODE

def test_classify_markdown():
    assert classify_file(Path("README.md")) == FileType.DOCUMENT

def test_classify_pdf():
    assert classify_file(Path("paper.pdf")) == FileType.PAPER

def test_classify_pdf_in_xcassets_skipped():
    # PDFs inside Xcode asset catalogs are vector icons, not papers
    asset_pdf = Path("MyApp/Images.xcassets/icon.imageset/icon.pdf")
    assert classify_file(asset_pdf) is None

def test_classify_pdf_in_xcassets_root_skipped():
    asset_pdf = Path("Pods/HXPHPicker/Assets.xcassets/photo.pdf")
    assert classify_file(asset_pdf) is None

def test_classify_unknown_returns_none():
    assert classify_file(Path("archive.zip")) is None

def test_classify_image():
    assert classify_file(Path("screenshot.png")) == FileType.IMAGE
    assert classify_file(Path("design.jpg")) == FileType.IMAGE
    assert classify_file(Path("diagram.webp")) == FileType.IMAGE

def test_count_words_sample_md():
    words = count_words(FIXTURES / "sample.md")
    assert words > 5

def test_detect_finds_fixtures():
    result = detect(FIXTURES)
    assert result["total_files"] >= 2
    assert "code" in result["files"]
    assert "document" in result["files"]

def test_detect_warns_small_corpus():
    result = detect(FIXTURES)
    assert result["needs_graph"] is False
    assert result["warning"] is not None

def test_detect_skips_dotfiles():
    result = detect(FIXTURES)
    for files in result["files"].values():
        for f in files:
            assert "/." not in f


def test_classify_md_paper_by_signals(tmp_path):
    """A .md file with enough paper signals should classify as PAPER."""
    paper = tmp_path / "paper.md"
    paper.write_text(
        "# Abstract\n\nWe propose a new method. See [1] and [23].\n"
        "This work was published in the Journal of AI. ArXiv preprint.\n"
        "See Equation 3 for details. \\cite{vaswani2017}.\n"
    )
    assert classify_file(paper) == FileType.PAPER


def test_classify_md_doc_without_signals(tmp_path):
    """A plain .md file without paper signals should stay DOCUMENT."""
    doc = tmp_path / "notes.md"
    doc.write_text("# My Notes\n\nHere are some notes about the project.\n")
    assert classify_file(doc) == FileType.DOCUMENT


def test_classify_attention_paper():
    """The real attention paper file should be classified as PAPER."""
    paper_path = Path("/home/safi/graphify_eval/papers/attention_is_all_you_need.md")
    if paper_path.exists():
        result = classify_file(paper_path)
        assert result == FileType.PAPER


def test_graphifyignore_excludes_file(tmp_path):
    """Files matching .graphifyignore patterns are excluded from detect()."""
    (tmp_path / ".graphifyignore").write_text("vendor/\n*.generated.py\n")
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "lib.py").write_text("x = 1")
    (tmp_path / "main.py").write_text("print('hi')")
    (tmp_path / "schema.generated.py").write_text("x = 1")

    result = detect(tmp_path)
    file_list = result["files"]["code"]
    assert any("main.py" in f for f in file_list)
    assert not any("vendor" in f for f in file_list)
    assert not any("generated" in f for f in file_list)
    assert result["graphifyignore_patterns"] == 2


def test_graphifyignore_missing_is_fine(tmp_path):
    """No .graphifyignore is not an error."""
    (tmp_path / "main.py").write_text("x = 1")
    result = detect(tmp_path)
    assert result["graphifyignore_patterns"] == 0


def test_graphifyignore_comments_ignored(tmp_path):
    """Comment lines in .graphifyignore are not treated as patterns."""
    (tmp_path / ".graphifyignore").write_text("# this is a comment\n\nmain.py\n")
    (tmp_path / "main.py").write_text("x = 1")
    (tmp_path / "other.py").write_text("x = 2")
    result = detect(tmp_path)
    assert not any("main.py" in f for f in result["files"]["code"])
    assert any("other.py" in f for f in result["files"]["code"])


def test_detect_follows_symlinked_directory(tmp_path):
    real_dir = tmp_path / "real_lib"
    real_dir.mkdir()
    (real_dir / "util.py").write_text("x = 1")
    (tmp_path / "linked_lib").symlink_to(real_dir)

    result_no = detect(tmp_path, follow_symlinks=False)
    result_yes = detect(tmp_path, follow_symlinks=True)

    assert any("real_lib" in f for f in result_no["files"]["code"])
    assert not any("linked_lib" in f for f in result_no["files"]["code"])
    assert any("linked_lib" in f for f in result_yes["files"]["code"])


def test_detect_follows_symlinked_file(tmp_path):
    (tmp_path / "real.py").write_text("x = 1")
    (tmp_path / "link.py").symlink_to(tmp_path / "real.py")

    result = detect(tmp_path, follow_symlinks=True)
    code = result["files"]["code"]
    assert any("real.py" in f for f in code)
    assert any("link.py" in f for f in code)


def test_graphifyignore_discovered_from_parent(tmp_path):
    """A .graphifyignore in a parent directory applies to subdirectory scans."""
    (tmp_path / ".graphifyignore").write_text("vendor/\n")
    sub = tmp_path / "packages" / "mylib"
    sub.mkdir(parents=True)
    (sub / "main.py").write_text("x = 1")
    vendor = sub / "vendor"
    vendor.mkdir()
    (vendor / "dep.py").write_text("y = 2")

    result = detect(sub)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert not any("vendor" in f for f in code_files)
    assert result["graphifyignore_patterns"] >= 1


def test_graphifyignore_stops_at_git_boundary(tmp_path):
    """Upward search stops at the git repo root (.git directory)."""
    (tmp_path / ".graphifyignore").write_text("main.py\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    sub = repo / "sub"
    sub.mkdir()
    (sub / "main.py").write_text("x = 1")

    result = detect(sub)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert result["graphifyignore_patterns"] == 0


def test_graphifyignore_at_git_root_is_included(tmp_path):
    """A .graphifyignore at the git repo root is included when scanning a subdir."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".graphifyignore").write_text("vendor/\n")
    sub = repo / "packages" / "mylib"
    sub.mkdir(parents=True)
    (sub / "main.py").write_text("x = 1")
    vendor = sub / "vendor"
    vendor.mkdir()
    (vendor / "dep.py").write_text("y = 2")

    result = detect(sub)
    code_files = result["files"]["code"]
    assert any("main.py" in f for f in code_files)
    assert not any("vendor" in f for f in code_files)
    assert result["graphifyignore_patterns"] == 1


def test_detect_handles_circular_symlinks(tmp_path):
    sub = tmp_path / "a"
    sub.mkdir()
    (sub / "main.py").write_text("x = 1")
    (sub / "loop").symlink_to(tmp_path)

    result = detect(tmp_path, follow_symlinks=True)
    assert any("main.py" in f for f in result["files"]["code"])


def test_classify_video_extensions():
    """Video and audio file extensions should classify as VIDEO."""
    from graphify.detect import FileType
    assert classify_file(Path("lecture.mp4")) == FileType.VIDEO
    assert classify_file(Path("podcast.mp3")) == FileType.VIDEO
    assert classify_file(Path("talk.mov")) == FileType.VIDEO
    assert classify_file(Path("recording.wav")) == FileType.VIDEO
    assert classify_file(Path("webinar.webm")) == FileType.VIDEO
    assert classify_file(Path("audio.m4a")) == FileType.VIDEO


def test_detect_includes_video_key(tmp_path):
    """detect() result always includes a 'video' key even with no video files."""
    (tmp_path / "main.py").write_text("x = 1")
    result = detect(tmp_path)
    assert "video" in result["files"]


def test_detect_finds_video_files(tmp_path):
    """detect() correctly counts video files and does not add them to word count."""
    (tmp_path / "lecture.mp4").write_bytes(b"fake video data")
    (tmp_path / "notes.md").write_text("# Notes\nSome content here.")
    result = detect(tmp_path)
    assert len(result["files"]["video"]) == 1
    assert any("lecture.mp4" in f for f in result["files"]["video"])
    # total_words should not include video files (they have no readable text)
    assert result["total_words"] >= 0  # won't crash


def test_detect_video_not_in_words(tmp_path):
    """Video files do not contribute to total_words."""
    (tmp_path / "clip.mp4").write_bytes(b"\x00" * 100)
    result = detect(tmp_path)
    # Only video file present — total_words should be 0
    assert result["total_words"] == 0


def test_detect_skips_graphify_out_subtree(tmp_path):
    """detect() must NOT re-ingest its own graphify-out/ output (self-ingestion bug)."""
    out_dir = tmp_path / "graphify-out" / "obsidian"
    out_dir.mkdir(parents=True)
    (out_dir / "foo.md").write_text("# Some prior export\n\nA simple note.\n")
    (tmp_path / "main.py").write_text("x = 1")

    result = detect(tmp_path)
    for ftype, file_list in result["files"].items():
        for f in file_list:
            assert "/graphify-out/obsidian" not in f, f"leaked self-output: {f}"
            assert "foo.md" not in f, f"leaked self-output: {f}"
    assert any("main.py" in f for f in result["files"]["code"])


def test_detect_skips_graphify_out_at_any_depth(tmp_path):
    """graphify-out/ should be pruned at any nesting depth, not just the root."""
    nested = tmp_path / "sub" / "graphify-out" / "obsidian"
    nested.mkdir(parents=True)
    (nested / "note.md").write_text("# Nested export\n\nNote body.\n")
    keeper = tmp_path / "sub" / "keeper.md"
    keeper.write_text("# Keep me\n\nThis is a real document.\n")

    result = detect(tmp_path)
    for ftype, file_list in result["files"].items():
        for f in file_list:
            assert "/graphify-out/" not in f, f"leaked self-output: {f}"
            assert "note.md" not in f, f"leaked self-output: {f}"
    assert any("keeper.md" in f for f in result["files"]["document"])


def test_detect_still_includes_graphify_out_memory(tmp_path):
    """graphify-out/memory/ allow-list must be preserved after the fix."""
    memory = tmp_path / "graphify-out" / "memory"
    memory.mkdir(parents=True)
    (memory / "recall.md").write_text("# recall content\n\nremembered fact\n")
    obsidian = tmp_path / "graphify-out" / "obsidian"
    obsidian.mkdir(parents=True)
    (obsidian / "note.md").write_text("# excluded export\n")

    result = detect(tmp_path)
    all_files = [f for fs in result["files"].values() for f in fs]
    assert any("recall.md" in f for f in all_files), "memory allow-list broken"
    assert not any("obsidian" in f and "note.md" in f for f in all_files), \
        "obsidian export leaked despite memory allow-list"


def test_detect_skips_graphify_out_underscore_variant(tmp_path):
    """The graphify_out/ underscore variant should also be pruned defensively."""
    out_dir = tmp_path / "graphify_out"
    out_dir.mkdir()
    (out_dir / "some.md").write_text("# stale output\n")
    (tmp_path / "main.py").write_text("y = 2")

    result = detect(tmp_path)
    for ftype, file_list in result["files"].items():
        for f in file_list:
            assert "some.md" not in f, f"leaked underscore variant: {f}"
            assert "/graphify_out/" not in f, f"leaked underscore variant: {f}"
    assert any("main.py" in f for f in result["files"]["code"])


# ---------------------------------------------------------------------------
# Phase 28-02: nesting guard + exclude_globs tests (Wave 0 RED)
# ---------------------------------------------------------------------------

from graphify.output import ResolvedOutput


def test_detect_nesting_guard_resolved_notes_dir_basename(tmp_path):
    """VAULT-12: detect() prunes directories whose basename matches resolved.notes_dir.name."""
    resolved = ResolvedOutput(False, None, tmp_path / "Atlas", tmp_path / "knowledge-graph-out", "profile", ())
    atlas = tmp_path / "Atlas"
    atlas.mkdir()
    (atlas / "foo.md").write_text("# Exported note\n")
    (tmp_path / "main.py").write_text("x = 1")

    result = detect(tmp_path, resolved=resolved)
    all_files = [f for fs in result["files"].values() for f in fs]
    assert not any("Atlas" in f and "foo.md" in f for f in all_files), \
        "Atlas/foo.md should be pruned by nesting guard"
    assert any("main.py" in f for f in result["files"]["code"])


def test_detect_nesting_guard_resolved_artifacts_dir_basename(tmp_path):
    """VAULT-12: detect() prunes directories whose basename matches resolved.artifacts_dir.name."""
    resolved = ResolvedOutput(False, None, tmp_path / "Atlas", tmp_path / "knowledge-graph-out", "profile", ())
    kg_out = tmp_path / "knowledge-graph-out"
    kg_out.mkdir()
    (kg_out / "graph.json").write_text("{}")
    (tmp_path / "main.py").write_text("x = 1")

    result = detect(tmp_path, resolved=resolved)
    all_files = [f for fs in result["files"].values() for f in fs]
    assert not any("knowledge-graph-out" in f for f in all_files), \
        "knowledge-graph-out/ should be pruned by nesting guard"
    assert any("main.py" in f for f in result["files"]["code"])


def test_detect_nesting_guard_summary_emits_once(tmp_path, capsys):
    """VAULT-12 / D-20: exactly ONE summary warning line, not per-directory."""
    resolved = ResolvedOutput(False, None, tmp_path / "Atlas", tmp_path / "knowledge-graph-out", "profile", ())
    # Create three nested directories at different depths all matching the notes_dir basename
    (tmp_path / "Atlas").mkdir()
    (tmp_path / "Atlas" / "foo.md").write_text("# note\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "Atlas").mkdir()
    (sub / "Atlas" / "bar.md").write_text("# note\n")
    sub2 = tmp_path / "other" / "deep"
    sub2.mkdir(parents=True)
    (sub2 / "Atlas").mkdir()
    (sub2 / "Atlas" / "baz.md").write_text("# note\n")
    (tmp_path / "main.py").write_text("x = 1")

    detect(tmp_path, resolved=resolved)
    captured = capsys.readouterr()
    warning_lines = [line for line in captured.err.splitlines() if "WARNING: skipped" in line]
    assert len(warning_lines) == 1, \
        f"Expected exactly 1 WARNING line, got {len(warning_lines)}: {warning_lines}"
    assert "nested output path" in warning_lines[0]


def test_detect_nesting_guard_no_warning_when_no_nesting(tmp_path, capsys):
    """D-20: no WARNING emitted when no nested output paths are found."""
    resolved = ResolvedOutput(False, None, tmp_path / "Atlas", tmp_path / "knowledge-graph-out", "profile", ())
    # No Atlas/ or knowledge-graph-out/ directories — no nesting
    (tmp_path / "main.py").write_text("x = 1")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n")

    detect(tmp_path, resolved=resolved)
    captured = capsys.readouterr()
    warning_lines = [line for line in captured.err.splitlines() if "WARNING: skipped" in line]
    assert len(warning_lines) == 0, \
        f"Expected no WARNING lines, got {len(warning_lines)}: {warning_lines}"


def test_detect_exclude_globs_prunes_files(tmp_path):
    """VAULT-11: exclude_globs from resolved are applied via _is_ignored()."""
    resolved = ResolvedOutput(False, None, tmp_path / "Atlas", tmp_path / "artifacts", "profile", ("**/cache/**", "*.tmp"))
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "big.bin").write_text("binary")
    (tmp_path / "foo.tmp").write_text("temp file")
    (tmp_path / "keep.md").write_text("# Keep me\n\nReal document.\n")

    result = detect(tmp_path, resolved=resolved)
    all_files = [f for fs in result["files"].values() for f in fs]
    assert any("keep.md" in f for f in all_files), "keep.md should be included"
    assert not any("big.bin" in f for f in all_files), "cache/big.bin should be excluded"
    assert not any("foo.tmp" in f for f in all_files), "foo.tmp should be excluded"


def test_detect_exclude_globs_with_cli_flag(tmp_path):
    """D-15: exclusions apply even when source='cli-flag' (--output overrides destination only)."""
    resolved = ResolvedOutput(False, None, tmp_path / "notes", tmp_path / "artifacts", "cli-flag", ("private/**",))
    private_dir = tmp_path / "private"
    private_dir.mkdir()
    (private_dir / "secret.md").write_text("# Secret\n")
    (tmp_path / "public.md").write_text("# Public\n\nVisible content.\n")

    result = detect(tmp_path, resolved=resolved)
    all_files = [f for fs in result["files"].values() for f in fs]
    assert any("public.md" in f for f in all_files), "public.md should be included"
    assert not any("secret.md" in f for f in all_files), "private/secret.md should be excluded"


def test_detect_exclude_globs_empty_tuple_no_op(tmp_path):
    """VAULT-11: empty exclude_globs=() does not suppress any files."""
    resolved = ResolvedOutput(False, None, tmp_path / "Atlas", tmp_path / "artifacts", "profile", ())
    (tmp_path / "keep.md").write_text("# Keep\n\nContent.\n")
    (tmp_path / "also_keep.py").write_text("x = 1")

    result = detect(tmp_path, resolved=resolved)
    all_files = [f for fs in result["files"].values() for f in fs]
    assert any("keep.md" in f for f in all_files)
    assert any("also_keep.py" in f for f in all_files)


# ---------------------------------------------------------------------------
# Phase 28-03: output-manifest tests (VAULT-13)
# ---------------------------------------------------------------------------


def test_save_and_load_output_manifest_round_trip(tmp_path):
    """VAULT-13: _save_output_manifest then _load_output_manifest round-trips correctly."""
    from graphify.detect import _save_output_manifest, _load_output_manifest

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    f = tmp_path / "notes" / "note.md"
    f.write_text("# Note\n")

    _save_output_manifest(artifacts_dir, notes_dir, [str(f)])
    data = _load_output_manifest(artifacts_dir)

    assert data["version"] == 1
    assert len(data["runs"]) == 1
    run = data["runs"][0]
    assert str(f.resolve()) in run["files"]
    assert "run_id" in run
    assert "timestamp" in run
    assert run["notes_dir"] == str(notes_dir.resolve())
    assert run["artifacts_dir"] == str(artifacts_dir.resolve())


def test_load_output_manifest_missing_returns_silent_empty(tmp_path, capsys):
    """VAULT-13: no manifest file → empty envelope; NO warning on stderr."""
    from graphify.detect import _load_output_manifest

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    data = _load_output_manifest(artifacts_dir)
    captured = capsys.readouterr()

    assert data == {"version": 1, "runs": []}
    assert captured.err == ""


def test_load_output_manifest_malformed_warns_once(tmp_path, capsys):
    """VAULT-13: malformed JSON → empty envelope + exactly one warning line."""
    from graphify.detect import _load_output_manifest

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "output-manifest.json").write_text("not json{{")

    data = _load_output_manifest(artifacts_dir)
    captured = capsys.readouterr()

    assert data == {"version": 1, "runs": []}
    warning_lines = [l for l in captured.err.splitlines() if "output-manifest.json unreadable" in l]
    assert len(warning_lines) == 1


def test_load_output_manifest_wrong_shape_warns_once(tmp_path, capsys):
    """VAULT-13: valid JSON but wrong shape (missing 'runs') → empty envelope + warning."""
    from graphify.detect import _load_output_manifest

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "output-manifest.json").write_text('{"version": 1}')

    data = _load_output_manifest(artifacts_dir)
    captured = capsys.readouterr()

    assert data == {"version": 1, "runs": []}
    warning_lines = [l for l in captured.err.splitlines() if "output-manifest.json unreadable" in l]
    assert len(warning_lines) == 1


def test_save_output_manifest_fifo_caps_at_5(tmp_path):
    """VAULT-13 D-24: rolling N=5 cap; oldest entries dropped FIFO after 7 saves."""
    from graphify.detect import _save_output_manifest, _load_output_manifest

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    for i in range(7):
        nd = tmp_path / f"notes_{i}"
        nd.mkdir(exist_ok=True)
        _save_output_manifest(artifacts_dir, nd, [])

    data = _load_output_manifest(artifacts_dir)
    assert len(data["runs"]) == 5
    # Oldest two should be gone; most recent notes_dir should be notes_6
    notes_dirs_in_manifest = [r["notes_dir"] for r in data["runs"]]
    assert not any("notes_0" in d for d in notes_dirs_in_manifest)
    assert not any("notes_1" in d for d in notes_dirs_in_manifest)
    assert any("notes_6" in d for d in notes_dirs_in_manifest)


def test_save_output_manifest_gc_removes_missing_files(tmp_path):
    """VAULT-13 D-28: GC removes file entries whose paths no longer exist on disk."""
    from graphify.detect import _save_output_manifest, _load_output_manifest

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    f1 = notes_dir / "gone.md"
    f1.write_text("# Gone\n")
    _save_output_manifest(artifacts_dir, notes_dir, [str(f1)])
    # Delete f1 to simulate a file that was exported and then removed
    f1.unlink()

    f2 = notes_dir / "present.md"
    f2.write_text("# Present\n")
    _save_output_manifest(artifacts_dir, notes_dir, [str(f2)])

    data = _load_output_manifest(artifacts_dir)
    assert len(data["runs"]) == 2
    # Run 1's files should no longer contain f1 (GC'd)
    assert str(f1.resolve()) not in data["runs"][0]["files"]
    # Run 2's files should contain f2
    assert str(f2.resolve()) in data["runs"][1]["files"]


def test_save_output_manifest_atomic_no_partial_on_oserror(tmp_path, monkeypatch):
    """VAULT-13 D-29: OSError during os.replace leaves no partial file; .tmp cleaned up."""
    import pytest
    from graphify.detect import _save_output_manifest

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    monkeypatch.setattr("os.replace", lambda *a, **kw: (_ for _ in ()).throw(OSError("simulated")))

    with pytest.raises(OSError):
        _save_output_manifest(artifacts_dir, notes_dir, [])

    # No partial .tmp should be left
    assert not list(artifacts_dir.glob("*.tmp"))
    # Original manifest should not exist (first write attempted)
    assert not (artifacts_dir / "output-manifest.json").exists()


def test_save_mtime_manifest_round_trip(tmp_path):
    """Incremental ``manifest.json`` (mtime map) round-trips and uses atomic replace."""
    import json

    import pytest

    from graphify.detect import load_manifest, save_manifest

    src = tmp_path / "mod.py"
    src.write_text("x = 1\n")
    manifest_file = tmp_path / "graphify-out" / "manifest.json"
    files_map = {"code": [str(src)]}

    save_manifest(files_map, manifest_path=str(manifest_file))

    assert manifest_file.exists()
    raw = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    assert set(raw.keys()) == {str(src)}
    loaded = load_manifest(str(manifest_file))
    assert loaded[str(src)] == pytest.approx(Path(src).stat().st_mtime)


def test_detect_skips_prior_files_from_manifest(tmp_path):
    """VAULT-13 D-27: detect() prunes files listed in output-manifest.json prior runs."""
    from graphify.detect import _save_output_manifest

    # Simulate a prior run that exported old_notes/note.md
    old_notes = tmp_path / "old_notes"
    old_notes.mkdir()
    prior_note = old_notes / "note.md"
    prior_note.write_text("# Prior note\n\nContent.\n")
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    _save_output_manifest(artifacts_dir, old_notes, [str(prior_note)])

    # New run with a different notes_dir
    new_notes = tmp_path / "new_notes"
    new_notes.mkdir()
    resolved = ResolvedOutput(False, None, new_notes, artifacts_dir, "profile", ())

    result = detect(tmp_path, resolved=resolved)
    all_files = [f for fs in result["files"].values() for f in fs]

    assert not any(str(prior_note.resolve()) == f for f in all_files), (
        "Prior note should have been pruned by manifest lookup"
    )


def test_detect_renamed_notes_dir_no_re_ingest(tmp_path):
    """VAULT-13 D-26/D-27: renaming notes_dir between runs does not re-ingest old files."""
    from graphify.detect import _save_output_manifest

    # Simulate run-1 with notes at Atlas/Graph
    old_notes = tmp_path / "Atlas" / "Graph"
    old_notes.mkdir(parents=True)
    old_file = old_notes / "foo.md"
    old_file.write_text("# Foo\n\nContent.\n")
    artifacts_dir = tmp_path / "knowledge-graph-out"
    artifacts_dir.mkdir()
    _save_output_manifest(artifacts_dir, old_notes, [str(old_file)])

    # Run-2: notes_dir renamed to Spaces/Graph (same artifacts_dir)
    new_notes = tmp_path / "Spaces" / "Graph"
    new_notes.mkdir(parents=True)
    resolved = ResolvedOutput(False, None, new_notes, artifacts_dir, "profile", ())

    result = detect(tmp_path, resolved=resolved)
    all_files = [f for fs in result["files"].values() for f in fs]

    assert not any(str(old_file.resolve()) == f for f in all_files), (
        "Old file from renamed notes_dir should be pruned via manifest"
    )


def test_detect_no_manifest_lookup_when_resolved_none(tmp_path, capsys):
    """VAULT-13 D-21: when resolved=None, no manifest access occurs (no error, no warning)."""
    (tmp_path / "keep.md").write_text("# Keep\n\nContent.\n")

    result = detect(tmp_path)
    captured = capsys.readouterr()

    # No manifest-related warnings should appear
    assert "output-manifest.json" not in captured.err
    # The file should still be detected normally
    all_files = [f for fs in result["files"].values() for f in fs]
    assert any("keep.md" in f for f in all_files)


def test_detect_skip_reasons(tmp_path):
    """Plan 29-02 (D-39): detect() returns a `skipped` dict with all 5 stable
    reason buckets, each populated by the matching pruning site."""
    # Create a corpus with at least one pruned noise dir + a normal file.
    (tmp_path / ".git").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("// noise")
    (tmp_path / "main.py").write_text("x = 1\n")

    result = detect(tmp_path)

    assert "skipped" in result
    assert isinstance(result["skipped"], dict)
    # D-38 stable label set — downstream consumers (Plan 29-03 doctor.py) depend on these.
    assert set(result["skipped"].keys()) >= {
        "nesting",
        "exclude-glob",
        "manifest",
        "sensitive",
        "noise-dir",
    }
    # node_modules must be recorded under noise-dir (pruning site verified).
    assert any("node_modules" in p for p in result["skipped"]["noise-dir"])


def test_detect_return_shape_backcompat(tmp_path):
    """Plan 29-02: ABI preservation — every pre-existing detect() return key
    must remain present after the additive `skipped` extension."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("x = 1\n")

    result = detect(tmp_path)

    for key in (
        "files",
        "total_files",
        "total_words",
        "needs_graph",
        "warning",
        "skipped_sensitive",
        "graphifyignore_patterns",
    ):
        assert key in result, f"detect() return is missing pre-existing key: {key}"
