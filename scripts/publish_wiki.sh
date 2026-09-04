#!/usr/bin/env bash
#
# Publish build/wiki to the GitHub wiki remote.
#
#   bash scripts/publish_wiki.sh                     # stage and show the diff, do not push
#   bash scripts/publish_wiki.sh --push              # push
#   bash scripts/publish_wiki.sh --remote <url>      # override the remote
#
# The wiki is a separate git repository at <repo>.wiki.git. It is public,
# it is cloneable, and its history is fetchable — exactly like the main
# repository. Everything in docs/gotchas.md that must not leak must also not
# leak here, so the leak checker runs against the built tree before anything
# is staged.
#
# GitHub does not create the wiki repository until the first page exists.
# If the clone below fails with "repository not found", enable Settings →
# Features → Wikis and create any page in the web UI once, then re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUILD_DIR="build/wiki"
REMOTE=""
DO_PUSH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push)   DO_PUSH=1; shift ;;
    --remote) REMOTE="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$REMOTE" ]]; then
  origin="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -z "$origin" ]]; then
    echo "error: no origin remote and no --remote given" >&2
    exit 1
  fi
  REMOTE="${origin%.git}.wiki.git"
fi

echo "==> Rebuilding"
python3 scripts/build_wiki.py

echo
echo "==> Leak check on the built wiki"
# The wiki is as public as the repository. A generated page that inlines an
# example from a source file the scanner already cleared is fine; a page that
# introduces new content is not automatically covered by anything else.
python3 scripts/leak_check.py "$BUILD_DIR"

echo
echo "==> Cloning wiki remote"
echo "    $REMOTE"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! git clone --quiet "$REMOTE" "$TMP/wiki" 2>"$TMP/err"; then
  echo
  echo "error: could not clone the wiki remote." >&2
  sed 's/^/    /' "$TMP/err" >&2
  echo >&2
  echo "If this says the repository does not exist, the wiki has never been" >&2
  echo "initialised. GitHub creates it on first page save: enable Settings ->" >&2
  echo "Features -> Wikis, create any page in the web UI, then re-run this." >&2
  exit 1
fi

echo
echo "==> Staging"
# Delete tracked pages that the build no longer produces, so a removed page
# does not linger. .git is preserved; nothing else in the wiki repo is
# authoritative, because the wiki is generated.
find "$TMP/wiki" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp "$BUILD_DIR"/*.md "$TMP/wiki/"

cd "$TMP/wiki"
git add -A

if git diff --cached --quiet; then
  echo "    no changes — the wiki is already current"
  exit 0
fi

echo
echo "==> Changes"
git diff --cached --stat
echo
echo "==> Full diff"
git diff --cached

if [[ "$DO_PUSH" -eq 0 ]]; then
  echo
  echo "-----------------------------------------------------------------"
  echo "Staged but NOT pushed. Review the diff above, then re-run with:"
  echo "    bash scripts/publish_wiki.sh --push"
  echo "-----------------------------------------------------------------"
  exit 0
fi

MSG="Regenerate wiki from $(cd "$REPO_ROOT" && git rev-parse --short HEAD)"
git -c user.name="$(cd "$REPO_ROOT" && git config user.name)" \
    -c user.email="$(cd "$REPO_ROOT" && git config user.email)" \
    commit --quiet -m "$MSG"

branch="$(git rev-parse --abbrev-ref HEAD)"
git push --quiet origin "$branch"

echo
echo "==> Pushed to $branch: $MSG"
