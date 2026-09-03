#!/usr/bin/env bash
#
# test_bare_lint.sh - reproduce CI's lint job faithfully.
#
# CI runs three separate jobs on three separate runners. The lint job gets a
# fresh `actions/checkout` and installs only yamllint and ansible-lint: no
# ansible.cfg, no staged inventory, no collections. The syntax job stages all
# of those.
#
# simulate_ci.sh runs ansible-lint AFTER staging, because that is convenient.
# That is a DIFFERENT TEST. ansible-lint resolves modules through the
# collections path, so a repo that lints clean with collections installed can
# fail on a bare checkout, and vice versa. This script covers the bare case.
#
# It tests the tree as it WOULD BE PUSHED -- committed content plus uncommitted
# working-tree changes plus untracked files -- rather than the working
# directory as-is, so build artefacts and generated config cannot mask a
# problem the runner would hit.
#
# Usage:
#   bash tests/test_bare_lint.sh
#   ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/test_bare_lint.sh

set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tests/_ansible_env.sh
. "${HERE}/_ansible_env.sh"

resolve_ansible || exit 2
SRC="$(cd "${HERE}/.." && pwd)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cd "$SRC" || exit 2
if [ ! -d .git ]; then
    echo "not a git repository: $SRC" >&2
    echo "This script reconstructs what actions/checkout would receive," >&2
    echo "which requires git metadata." >&2
    exit 2
fi

# Committed content is what the runner starts from.
git archive HEAD | tar -x -C "$TMP"

# Plus anything modified or untracked, since that is what is about to be
# pushed. .gitignore is respected for untracked files -- collections/ and
# generated config must NOT appear, exactly as on the runner.
git diff --name-only HEAD | while IFS= read -r f; do
    [ -f "$f" ] && { mkdir -p "$TMP/$(dirname "$f")"; cp "$f" "$TMP/$f"; }
done
git ls-files --others --exclude-standard | while IFS= read -r f; do
    mkdir -p "$TMP/$(dirname "$f")"; cp "$f" "$TMP/$f"
done

cd "$TMP" || exit 2

echo "== environment =="
report_ansible
echo "bare tree:           $TMP"
echo "ansible.cfg present: $([ -f ansible.cfg ] && echo 'YES - unexpected' || echo no)"
echo "collections present: $([ -d collections ] && echo 'YES - unexpected' || echo no)"

echo
echo "== yamllint . =="
yamllint .
YL=$?
echo "yamllint exit=$YL"

echo
echo "== ansible-lint =="
ansible-lint
AL=$?
echo "ansible-lint exit=$AL"

echo
if [ $YL -eq 0 ] && [ $AL -eq 0 ]; then
    echo "BARE LINT JOB PASSES"
    exit 0
fi
echo "BARE LINT JOB FAILS"
exit 1
