#!/usr/bin/env bash
#
# run_tests.sh - run every test in the repository.
#
# Usage: bash tests/run_tests.sh

set -o nounset
set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
cd "${REPO_ROOT}" || exit 2

FAILED=0

echo "== leak check =================================================="
bash tests/test_leak_check.sh || FAILED=1

echo
echo "== baseline evaluation logic (fixture-driven) =================="
# Explicit inventory. Running against the project inventory risks picking up
# group_vars that set ansible_connection, which outranks the play-level
# connection keyword and would dispatch these tasks at a device.
ansible-playbook -i localhost, tests/test_baseline_logic.yml || FAILED=1

echo
if [[ ${FAILED} -ne 0 ]]; then
    echo "TEST SUITE FAILED"
    exit 1
fi
echo "TEST SUITE PASSED"
