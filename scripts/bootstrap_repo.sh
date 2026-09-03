#!/usr/bin/env bash
#
# bootstrap_repo.sh - initialise this repository for its first push.
#
# Creates a fresh git history, verifies the tree is clean of environment data,
# and makes the initial commit. It does NOT push and it does NOT touch
# credentials -- authentication to GitHub is yours to perform.
#
# ---------------------------------------------------------------------------
# WHY A FRESH HISTORY
# ---------------------------------------------------------------------------
# This script refuses to run inside an existing git repository that already has
# commits. Scrubbing a working tree does nothing about what is reachable in
# earlier commits: a single addresses-and-hostnames commit from six months ago
# remains fetchable by anyone who clones a public repo, and `git log -p` will
# hand it over without being asked.
#
# If you want history from an existing repository, that is a separate and much
# more careful operation involving git-filter-repo, and it must be verified by
# scanning every reachable blob rather than the checkout. Do not shortcut it by
# copying a .git directory in here.
#
# ---------------------------------------------------------------------------
# USAGE
# ---------------------------------------------------------------------------
#   bash scripts/bootstrap_repo.sh
#   bash scripts/bootstrap_repo.sh --remote git@github.com:USER/REPO.git
#
# Options
#   --remote URL   Configure 'origin' after committing. Nothing is pushed.
#   --branch NAME  Initial branch name. Default: main
#   --force        Proceed even if the test suite fails. Prints a warning.
#                  Intended only for iterating on a broken tree locally.
# ---------------------------------------------------------------------------

set -o nounset
set -o pipefail

REMOTE=""
BRANCH="main"
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --remote) REMOTE="${2:-}"; shift 2 ;;
        --branch) BRANCH="${2:-main}"; shift 2 ;;
        --force)  FORCE=1; shift ;;
        -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
cd "${REPO_ROOT}" || exit 2

echo "repository root: ${REPO_ROOT}"
echo

# ---------------------------------------------------------------------------
# 1. Refuse to run on top of an existing history.
# ---------------------------------------------------------------------------
if [[ -d .git ]]; then
    if git rev-parse --verify HEAD >/dev/null 2>&1; then
        echo "REFUSING: .git exists and already has commits." >&2
        echo >&2
        echo "This script only bootstraps a fresh history. Publishing an" >&2
        echo "existing history exposes every prior commit, and scrubbing the" >&2
        echo "working tree does not change what earlier commits contain." >&2
        echo >&2
        echo "Current HEAD: $(git log -1 --oneline 2>/dev/null)" >&2
        exit 1
    fi
    echo "note: .git exists but has no commits -- continuing."
else
    git init --initial-branch="${BRANCH}" >/dev/null || {
        # Older git does not support --initial-branch.
        git init >/dev/null && git symbolic-ref HEAD "refs/heads/${BRANCH}"
    }
    echo "initialised empty repository on branch '${BRANCH}'"
fi

# ---------------------------------------------------------------------------
# 2. Refuse to commit a tree that has not passed its own tests.
# ---------------------------------------------------------------------------
echo
echo "running the test suite..."
echo
if bash tests/run_tests.sh; then
    TESTS_OK=1
else
    TESTS_OK=0
fi

echo
if [[ ${TESTS_OK} -eq 0 ]]; then
    if [[ ${FORCE} -eq 1 ]]; then
        echo "WARNING: tests failed and --force was given. Committing anyway."
        echo "         Do not push this. Fix the tree first."
    else
        echo "REFUSING: the test suite failed." >&2
        echo >&2
        echo "The leak check is part of that suite. A failure there means" >&2
        echo "something resembling real environment data is in the tree." >&2
        echo "Fix it before creating a commit -- once committed, removing it" >&2
        echo "means rewriting history rather than editing a file." >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# 3. Show exactly what is about to be committed.
# ---------------------------------------------------------------------------
git add -A

echo
echo "files staged for the initial commit:"
git diff --cached --name-only | sed 's/^/  /'
echo
echo "  total: $(git diff --cached --name-only | wc -l | tr -d ' ') file(s)"

# Nothing matching an .example counterpart should be staged -- those are the
# filled-in local copies and .gitignore should already exclude them. Check
# rather than trust, since a stale .gitignore is silent.
LEAKED_LOCAL=$(git diff --cached --name-only | while read -r f; do
    [[ -f "${f}.example" ]] && echo "${f}"
done)
if [[ -n "${LEAKED_LOCAL}" ]]; then
    echo >&2
    echo "REFUSING: these staged files have an .example counterpart," >&2
    echo "which means they are filled-in local copies, not templates:" >&2
    echo "${LEAKED_LOCAL}" | sed 's/^/  /' >&2
    echo >&2
    echo "Check .gitignore. Unstage with: git reset" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 4. Commit.
# ---------------------------------------------------------------------------
git commit -q -m "Initial commit: reference playbook repository

Clean-room reference implementations of network and systems automation
patterns. No content here derives from a working environment; every playbook
was written fresh against the technique rather than adapted from a live tree,
so there is no sanitisation step to have gotten wrong.

Structure:
  playbooks/{network,linux,tls,reporting}  grouped by function, not origin
  docs/gotchas.md                          failure modes that produce a PASS
  docs/conventions.md                      placeholder vocabulary, test policy
  scripts/leak_check.py                    CI gate against environment data
  tests/                                   fixture-driven, no hardware needed

The leak check runs in CI on every push and is itself tested before it is
trusted: tests/test_leak_check.sh asserts the scanner rejects a file of
planted leaks, category by category, before accepting its clean verdict on the
working tree. A scanner that has silently stopped matching is worse than none,
because it converts an active check into a false assurance.

Only .example files are tracked for inventory and vars. Filled-in copies are
gitignored, so the failure mode is a missing file rather than a committed
credential." || {
    echo "commit failed" >&2
    exit 1
}

echo
echo "initial commit created:"
git log -1 --stat --oneline | head -5

# ---------------------------------------------------------------------------
# 5. Optionally configure the remote. Never push.
# ---------------------------------------------------------------------------
if [[ -n "${REMOTE}" ]]; then
    git remote remove origin 2>/dev/null
    git remote add origin "${REMOTE}"
    echo
    echo "remote 'origin' set to: ${REMOTE}"
fi

cat <<'NEXT'

--------------------------------------------------------------------------
NOT PUSHED. Remaining steps are yours:

  1. Create the repository on GitHub. Leave it EMPTY -- no README, no
     .gitignore, no licence. Those exist here already and an auto-generated
     file will force a merge on the first push.

  2. Set the remote if you did not pass --remote:
       git remote add origin git@github.com:USER/REPO.git

  3. Review the diff one last time. This is the last cheap moment:
       git show --stat
       git show

  4. Push:
       git push -u origin main

  5. Install the pre-commit hook so the leak check runs locally from now on:
       pip install pre-commit && pre-commit install
--------------------------------------------------------------------------
NEXT
