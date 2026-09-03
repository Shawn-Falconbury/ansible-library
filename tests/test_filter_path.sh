#!/usr/bin/env bash
#
# test_filter_path.sh - prove the filter_plugins registration is load-bearing.
#
# tests/test_mask.py proves the masking FUNCTIONS work. It imports the module
# directly and never involves Ansible, so it says nothing about whether a
# playbook can actually reach those filters.
#
# That gap matters here. Ansible autodiscovers filter_plugins/ next to the
# PLAYBOOK, and every playbook in this repo lives in a subdirectory, so the
# repository-root filter_plugins/ is outside the search path. It works only
# because ansible.cfg declares it explicitly.
#
# This test asserts BOTH directions:
#   - without the declaration the filters must be unreachable
#   - with it they must resolve and produce correct output
#
# The negative half is the important one. A configuration line that turns out
# to be unnecessary is a line nobody dares delete, and a suite that would stay
# green after deleting it teaches nothing.
#
# Usage:
#   bash tests/test_filter_path.sh
#   ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/test_filter_path.sh

set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tests/_ansible_env.sh
. "${HERE}/_ansible_env.sh"

resolve_ansible || exit 2
ROOT="$(cd "${HERE}/.." && pwd)"
cd "$ROOT" || exit 2

FAILED=0
PROBE="playbooks/network/_test_filter_path.yml"

# ansible.cfg is gitignored and may or may not already exist. Preserve any
# existing copy rather than clobbering the caller's working state.
RESTORE=0
if [ -f ansible.cfg ]; then
    cp ansible.cfg "${ROOT}/.ansible.cfg.testbak"
    RESTORE=1
fi

cleanup() {
    rm -f "$PROBE" ansible.cfg
    if [ "$RESTORE" -eq 1 ]; then
        mv "${ROOT}/.ansible.cfg.testbak" ansible.cfg
    fi
}
trap cleanup EXIT

# The probe lives alongside the real playbooks, in a subdirectory. Putting it
# at the repository root would sit it next to filter_plugins/ where
# autodiscovery finds it, and the test would pass for the wrong reason.
cat > "$PROBE" <<'YAML'
---
- name: Exercise the masking filters from a playbook in a subdirectory
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Masking filters resolve and produce expected output
      ansible.builtin.assert:
        that:
          - "'192.0.2.10' | mask_ip == '192.0.xxx.xxx'"
          - "'00:00:5e:00:53:af' | mask_mac == '00:00:5e:xx:xx:xx'"
          - "'sw-a-01.site.example' | mask_hostname == 'sw-a-01.xxx'"
        quiet: true
YAML

echo "== environment =="
report_ansible

echo
echo "== negative: WITHOUT filter_plugins registered, filters must be unreachable =="
grep -v '^filter_plugins' ansible.cfg.example > ansible.cfg
if ansible-playbook -i localhost, "$PROBE" >/tmp/fp_neg.txt 2>&1; then
    echo "  FAIL - the playbook succeeded without the declaration."
    echo "         filter_plugins in ansible.cfg is doing nothing: either the"
    echo "         filters moved somewhere autodiscoverable, or this test is"
    echo "         no longer probing what it claims to."
    FAILED=1
else
    echo "  ok - failed as expected"
    grep -oE "Could not load[^\"]*|No filter named '[a-z_]+'" /tmp/fp_neg.txt \
        | head -1 | sed 's/^/       /'
fi

echo
echo "== positive: WITH filter_plugins registered, filters must resolve =="
cp ansible.cfg.example ansible.cfg
if ansible-playbook -i localhost, "$PROBE" >/tmp/fp_pos.txt 2>&1; then
    echo "  ok - filters resolved, all three assertions held"
else
    echo "  FAIL - filters unreachable even with the declaration:"
    tail -12 /tmp/fp_pos.txt | sed 's/^/       /'
    FAILED=1
fi

echo
if [ $FAILED -eq 0 ]; then
    echo "FILTER PATH VERIFIED"
    exit 0
fi
echo "FILTER PATH CHECK FAILED"
exit 1
