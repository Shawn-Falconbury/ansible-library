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
echo "== inventory row assembly (fixture-driven) ====================="
# Asserts that a host which produced no facts still produces a row. The
# masking test cannot catch this: it is handed a fixture list that already
# contains an unreachable device, so it never sees a dropped one.
ansible-playbook -i localhost, tests/test_inventory_assembly.yml || FAILED=1

echo
echo "== host row assembly (fixture-driven) =========================="
# roles/host_rows, shared by playbooks/reporting/ and playbooks/linux/.
# ANSIBLE_ROLES_PATH rather than a staged ansible.cfg: this is the only test
# that needs role resolution, and one env var is cheaper than a wrapper.
#
# Note that --syntax-check does NOT catch an unresolvable role -- include_role
# is dynamic, so the name is never looked up until the play runs. This test is
# the only automated check that the role can be found at all.
ANSIBLE_ROLES_PATH=./roles ansible-playbook -i localhost, tests/test_host_rows.yml || FAILED=1

echo
echo "== service health evaluation logic (fixture-driven) ============"
# Runs bare -- no ansible.cfg, no collections. The report masking half of
# this playbook needs a staged config and runs under test_masking.sh above.
ansible-playbook -i localhost, tests/test_service_health_logic.yml || FAILED=1

echo
echo "== network playbook logic (fixture-driven) ====================="
# snmp_capability_probe and host_key_trust. Same harness as the linux
# suite: every evaluation file consumes check_facts and emits
# check_results, so one runner drives all five.
ansible-playbook -i localhost, tests/test_network_logic.yml || FAILED=1

echo
echo "== linux playbook logic (fixture-driven) ======================="
# One suite for all three Linux evaluations. They share the lx_results /
# lx_verdict contract, so one harness drives all of them. Runs bare -- the
# listener report masking half runs under test_masking.sh above.
ansible-playbook -i localhost, tests/test_linux_logic.yml || FAILED=1

echo
if [ ${FAILED} -ne 0 ]; then
    echo "TEST SUITE FAILED"
    exit 1
fi
echo "TEST SUITE PASSED"
