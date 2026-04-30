#!/usr/bin/env bash
# Implements docs/LS-VAULT-UPDATE-GUIDE.md — update ls-vault (or another vault) with graphify.
#
# Usage:
#   ./scripts/ls-vault-update.sh
#   REPO=/path/to/graphify VAULT=/path/to/vault RAW=work-vault/raw ./scripts/ls-vault-update.sh
#   ./scripts/ls-vault-update.sh --apply <plan-id>
#
# Environment (defaults shown for a typical ls-vault layout):
#   REPO  — graphify git checkout (default: parent of scripts/)
#   VAULT — target Obsidian vault
#   RAW   — raw corpus for --input (default work-vault/raw; resolved vs VAULT, REPO, then cwd)

set -euo pipefail

_usage() {
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
    cat <<'EOF'

Options:
  --help                 Show this help
  --skip-pull            Skip git checkout main and pull (still runs pip install)
  --no-backup            Skip backup steps (not recommended)
  --backup-git           Commit all changes in VAULT before apply (default: on)
  --no-backup-git        Skip git backup
  --backup-copy          Also cp -R vault to VAULT-backup-YYYYMMDD-HHMMSS
  --graphify-install     Run graphify install after pip install
  --apply PLAN_ID        Run apply step (step 7); omit for preview-only (step 5)
  --stop-after-validate  Exit after profile validation (step 4)

Set REPO, VAULT, and RAW in the environment or edit defaults below.
EOF
}

# Defaults from LS-VAULT-UPDATE-GUIDE.md (override with env)
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${REPO:="$(cd "${_SCRIPT_DIR}/.." && pwd)"}"
: "${VAULT:=/Users/silveimar/Documents/ls-vault}"
: "${RAW:=work-vault/raw}"

_SKIP_PULL=0
_NO_BACKUP=0
_BACKUP_GIT=1
_BACKUP_COPY=0
_GRAPHIFY_INSTALL=0
_APPLY_PLAN_ID=""
_STOP_AFTER_VALIDATE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) _usage; exit 0 ;;
        --skip-pull) _SKIP_PULL=1; shift ;;
        --no-backup) _NO_BACKUP=1; shift ;;
        --backup-git) _BACKUP_GIT=1; shift ;;
        --no-backup-git) _BACKUP_GIT=0; shift ;;
        --backup-copy) _BACKUP_COPY=1; shift ;;
        --graphify-install) _GRAPHIFY_INSTALL=1; shift ;;
        --apply)
            shift
            [[ $# -gt 0 ]] || { echo "error: --apply requires PLAN_ID" >&2; exit 1; }
            _APPLY_PLAN_ID="$1"
            shift
            ;;
        --stop-after-validate) _STOP_AFTER_VALIDATE=1; shift ;;
        *) echo "error: unknown option: $1" >&2; _usage >&2; exit 1 ;;
    esac
done

# Resolve RAW: absolute, else first existing path among VAULT/REPO/cwd (per guide)
_resolve_raw() {
    local r="$RAW"
    if [[ "$r" = /* ]]; then
        echo "$r"
        return
    fi
    local base
    for base in "$VAULT" "$REPO" "$(pwd)"; do
        if [[ -d "${base}/${r}" ]]; then
            echo "${base}/${r}"
            return
        fi
    done
    echo "$r"
}

RAW_RESOLVED="$(_resolve_raw)"

echo "[ls-vault-update] REPO=$REPO"
echo "[ls-vault-update] VAULT=$VAULT"
echo "[ls-vault-update] RAW (resolved)=$RAW_RESOLVED"
echo

if [[ ! -d "$REPO" ]]; then
    echo "error: REPO is not a directory: $REPO" >&2
    exit 1
fi
if [[ ! -d "$VAULT" ]]; then
    echo "error: VAULT is not a directory: $VAULT" >&2
    exit 1
fi
if [[ ! -d "$RAW_RESOLVED" ]]; then
    echo "error: raw corpus directory not found: $RAW_RESOLVED" >&2
    echo "hint: set RAW to your corpus path (see docs/LS-VAULT-UPDATE-GUIDE.md)" >&2
    exit 1
fi

PROFILE_SRC="${REPO}/profile-example-complete.yaml"
PROFILE_DST="${VAULT}/.graphify/profile.yaml"
if [[ ! -f "$PROFILE_SRC" ]]; then
    echo "error: profile example missing: $PROFILE_SRC" >&2
    exit 1
fi

# --- 1) Update graphify code and local package ---
echo "[ls-vault-update] Step 1: update graphify and pip install"
if [[ "$_SKIP_PULL" -eq 0 ]]; then
    git -C "$REPO" checkout main
    git -C "$REPO" pull
fi
(
    cd "$REPO"
    pip install -e ".[all]"
)
if [[ "$_GRAPHIFY_INSTALL" -eq 1 ]]; then
    echo "[ls-vault-update] Optional: graphify install"
    graphify install
fi
echo

# --- 2) Back up the vault ---
if [[ "$_NO_BACKUP" -eq 0 ]]; then
    echo "[ls-vault-update] Step 2: backup vault"
    if [[ "$_BACKUP_GIT" -eq 1 ]]; then
        if git -C "$VAULT" rev-parse --git-dir >/dev/null 2>&1; then
            git -C "$VAULT" add -A
            if git -C "$VAULT" diff --staged --quiet; then
                echo "[ls-vault-update] git: nothing staged to commit (working tree backup skipped)"
            else
                git -C "$VAULT" commit -m "backup before graphify vault update"
                echo "[ls-vault-update] git: backup commit created"
            fi
        else
            echo "[ls-vault-update] warning: $VAULT is not a git repo; skipping git backup" >&2
        fi
    fi
    if [[ "$_BACKUP_COPY" -eq 1 ]]; then
        _ts="$(date +%Y%m%d-%H%M%S)"
        echo "[ls-vault-update] cp: ${VAULT}-backup-${_ts}"
        cp -R "$VAULT" "${VAULT}-backup-${_ts}"
    fi
    echo
else
    echo "[ls-vault-update] Step 2: skipped (--no-backup)"
    echo
fi

# --- 3) Install profile ---
echo "[ls-vault-update] Step 3: install profile to .graphify/profile.yaml"
mkdir -p "${VAULT}/.graphify"
cp "$PROFILE_SRC" "$PROFILE_DST"
echo

# --- 4) Validate profile ---
echo "[ls-vault-update] Step 4: validate profile"
graphify --validate-profile "$VAULT"
echo

if [[ "$_STOP_AFTER_VALIDATE" -eq 1 ]]; then
    echo "[ls-vault-update] Done (--stop-after-validate)."
    exit 0
fi

# --- 5) Preview (no writes to vault) ---
if [[ -z "$_APPLY_PLAN_ID" ]]; then
    echo "[ls-vault-update] Step 5: preview update-vault (no vault writes)"
    graphify update-vault --input "$RAW_RESOLVED" --vault "$VAULT"
    echo
    _mig_parent="$(cd "$(dirname "$VAULT")" && pwd)"
    echo "[ls-vault-update] Step 6: review migration artifacts under:"
    echo "  ${_mig_parent}/graphify-out/migrations/"
    echo "  (sibling-of-vault layout; see graphify/output.py resolve_output)"
    echo
    echo "When satisfied, apply with:"
    echo "  RAW=$RAW VAULT=$VAULT REPO=$REPO $0 --apply '<plan-id>'"
    echo
    echo "See docs/LS-VAULT-UPDATE-GUIDE.md steps 7–10 for apply, Obsidian checks, and rollback."
    exit 0
fi

# --- 7) Apply reviewed plan ---
echo "[ls-vault-update] Step 7: apply plan $_APPLY_PLAN_ID"
graphify update-vault --input "$RAW_RESOLVED" --vault "$VAULT" --apply --plan-id "$_APPLY_PLAN_ID"
echo
echo "[ls-vault-update] Step 8: verify in Obsidian (Maps, Things, Dataview, links/tags) — see guide."
echo "[ls-vault-update] Rollback: docs/LS-VAULT-UPDATE-GUIDE.md section 9."
