# Installation

How to install graphify **from this repository** (without using the PyPI package) and register it as a skill in your AI coding assistant.

**Requirements:** Python 3.10+ and a supported assistant (Claude Code, Codex, OpenCode, OpenClaw, Factory Droid, Trae, etc.). See the main [README](README.md) for platform notes.

## Install from the repo

Clone or copy this repository, then run these commands from the **repository root** (the directory that contains `pyproject.toml`).

### Recommended: virtual environment

```bash
cd /path/to/graphify
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
```

### Editable install (development)

Use this when you are modifying the codebase; changes take effect without reinstalling.

```bash
pip install -e .
```

### Regular install from a local path

Use this for a normal install that copies the built package into your environment.

```bash
pip install /path/to/graphify
```

Replace `/path/to/graphify` with the absolute path to your clone.

### Optional dependency groups

Extras are defined in `pyproject.toml` under `[project.optional-dependencies]`. Examples:

```bash
pip install -e ".[mcp]"
pip install -e ".[pdf]"
pip install -e ".[all]"
```

## Package name vs CLI

The PyPI distribution name is **`graphifyy`** (see `pyproject.toml`). The command-line tool is still **`graphify`**.

## Register the skill with your assistant

After installation, install the skill files into your tool’s expected locations:

```bash
graphify install
```

### Platform-specific registration

| Assistant        | Command                                      |
|-----------------|-----------------------------------------------|
| Default (Claude Code Linux/Mac) | `graphify install`                |
| Claude Code (Windows) | `graphify install` or `graphify install --platform windows` |
| Codex           | `graphify install --platform codex`           |
| OpenCode        | `graphify install --platform opencode`        |
| OpenClaw        | `graphify install --platform claw`            |
| Factory Droid   | `graphify install --platform droid`         |
| Trae            | `graphify install --platform trae`            |
| Trae CN         | `graphify install --platform trae-cn`       |

Then invoke the skill from your assistant (for example `/graphify .` in Claude Code; Codex uses `$graphify .`). See [README](README.md) for full usage.

## Using a specific Python interpreter

If your coding agent or IDE uses a different Python, install into **that** environment and run `graphify install` with that same environment active:

```bash
/path/to/python -m pip install -e /path/to/graphify
/path/to/python -m graphify install
```

Ensure the `graphify` executable on your `PATH` comes from the environment where you installed the package, or invoke `python -m graphify` from that environment.

## PyPI install (alternative)

If you prefer the published package instead of a local checkout:

```bash
pip install graphifyy && graphify install
```

The CLI and skill behavior are the same; only the install source differs.
