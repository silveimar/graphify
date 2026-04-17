"""Regression guard for pyproject.toml packaging metadata.

Ensures Phase 1 Foundation's obsidian extras group survives future merges —
merge commit 15b97be silently dropped `obsidian = ["PyYAML"]` and the PyYAML
entry from `all` when reconciling v3's video/audio additions. This test
fails loudly if that recurs.
"""
from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 via pytest's transitive dep


def _load_pyproject() -> dict:
    root = Path(__file__).resolve().parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def test_obsidian_extras_group_exists():
    data = _load_pyproject()
    extras = data["project"]["optional-dependencies"]
    assert "obsidian" in extras, (
        "pyproject.toml is missing the 'obsidian' optional-dependencies group. "
        "Phase 1 Foundation requires `obsidian = [\"PyYAML\"]` for profile.yaml "
        "loading. If you hit this after a merge, restore the line under "
        "[project.optional-dependencies]."
    )
    assert "PyYAML" in extras["obsidian"], (
        "'obsidian' extras group exists but does not declare PyYAML. "
        "profile.py's fallback path prints `pip install graphifyy[obsidian]` "
        "as its install hint — that command must install PyYAML."
    )


def test_all_extras_includes_pyyaml():
    data = _load_pyproject()
    all_extras = data["project"]["optional-dependencies"]["all"]
    assert "PyYAML" in all_extras, (
        "'all' extras group is missing PyYAML. `pip install graphifyy[all]` "
        "must include every optional dep — if obsidian is in extras, its "
        "package must be in 'all' too."
    )


def test_package_data_includes_builtin_templates():
    data = _load_pyproject()
    package_data = data["tool"]["setuptools"]["package-data"]["graphify"]
    assert "builtin_templates/*.md" in package_data, (
        "pyproject.toml package-data for graphify is missing 'builtin_templates/*.md'. "
        "Phase 2 requires built-in template files to be included in wheel installs. "
        "Add 'builtin_templates/*.md' to [tool.setuptools.package-data] graphify list."
    )
    assert "skill.md" in package_data, (
        "pyproject.toml package-data for graphify is missing 'skill.md'. "
        "This entry must not be removed — it is required for graphify install to work."
    )


def test_templates_module_is_pure_stdlib():
    """IN-10: graphify/templates.py must not import any third-party package.

    The template engine is pure stdlib so that it works without the optional
    `[obsidian]` extras group (which only carries PyYAML for profile.yaml
    parsing). If you find yourself wanting to add a new top-level import to
    templates.py, it must come from the stdlib. New optional deps must live
    behind a guarded `try: import` in profile.py or another adapter module.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    source = (root / "graphify" / "templates.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    # stdlib whitelist for templates.py — extend deliberately, not casually.
    allowed_stdlib_roots = {
        "__future__",
        "datetime",
        "importlib",
        "re",
        "string",
        "sys",
        "pathlib",
        "typing",
    }
    # graphify.profile is fine — it's the only intra-package dep we accept here.
    allowed_internal_prefixes = ("graphify",)

    offending: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if (
                    root_pkg not in allowed_stdlib_roots
                    and not alias.name.startswith(allowed_internal_prefixes)
                ):
                    offending.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            root_pkg = node.module.split(".")[0]
            if (
                root_pkg not in allowed_stdlib_roots
                and not node.module.startswith(allowed_internal_prefixes)
            ):
                offending.append(node.module)

    assert offending == [], (
        f"graphify/templates.py imports non-stdlib packages: {offending}. "
        "The template engine must remain pure stdlib so it works without "
        "the [obsidian] extras group. See the IN-10 docstring at the top "
        "of templates.py for the policy."
    )


def test_dedup_optional_extra_present():
    """Phase 10 D-01: [dedup] optional extra must be defined with sentence-transformers."""
    data = _load_pyproject()
    extras = data["project"]["optional-dependencies"]
    assert "dedup" in extras, "Missing [dedup] optional-dependency group"
    assert "sentence-transformers" in extras["dedup"]
    # All-extras bundle must also include sentence-transformers
    assert "sentence-transformers" in extras["all"]
