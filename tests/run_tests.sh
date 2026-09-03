#!/usr/bin/env bash
#
# run_tests.sh - run every test in the repository.
#
# Usage:
#   bash tests/run_tests.sh
#   ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/run_tests.sh
#
# Ordered fastest-first, and within that, by how badly a failure would hurt.
# The unit tests guard the masking filters -- the code most capable of leaking
# data if it breaks -- and take milliseconds, so they run first.
#
# NOT run from here:
#   tests/simulate_ci.sh    reproduces the CI jobs from a clean slate; it wipes
#                           collections/ and generated config, which is too
#                           destructive for a default `run_tests` invocation.
#   tests/test_bare_lint.sh reproduces CI's lint job on a bare checkout.
#
# Run both of those before pushing. See tests/README.md.

set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tests/_ansible_env.sh
. "${HERE}/_ansible_env.sh"

resolve_ansible || exit 2
cd "$(cd "${HERE}/.." && pwd)" || exit 2

FAILED=0

echo "== environment ================================================"
report_ansible

echo
echo "== filter plugin unit tests ==================================="
# No Ansible needed. Fastest check, guarding the code most likely to leak
# data if it breaks.
python3 -m unittest discover -s tests -p 'test_*.py' || FAILED=1

echo
echo "== leak check =================================================="
bash tests/test_leak_check.sh || FAILED=1

echo
echo "== filter plugin reachable from a playbook ====================="
# test_mask.py proves the functions work; this proves a playbook in a
# subdirectory can actually resolve them through ansible.cfg.
bash tests/test_filter_path.sh || FAILED=1

echo
echo "== report masking (dual-render) ================================"
# Renders the inventory template both ways from fixtures and asserts no
# fixture value survives into the masked copy. Distinct from the unit
# tests: those prove the masking functions work, this proves the template
# actually calls them.
bash tests/test_masking.sh || FAILED=1

echo
echo "== baseline evaluation logic (fixture-driven) =================="
# Explicit inventory. Running against the project inventory risks picking up
# group_vars that set ansible_connection, which outranks the play-level
# connection keyword and would dispatch these tasks at a device.
ansible-playbook -i localhost, tests/test_baseline_logic.yml || FAILED=1

echo
if [ ${FAILED} -ne 0 ]; then
    echo "TEST SUITE FAILED"
    exit 1
fi
echo "TEST SUITE PASSED"
