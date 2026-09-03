#!/usr/bin/env bash
#
# simulate_ci.sh - run the CI jobs locally, from a clean slate.
#
# THE RULE FOR THIS FILE: every command here must be copied verbatim from
# .github/workflows/ci.yml. Do not paraphrase, do not "improve", do not add
# exclusions that seem sensible.
#
# The first version of this script did exactly that. CI ran
#     find playbooks -name '*.yml' -type f
# and this script ran the same find with -not -path '*/tasks/*' bolted on,
# because feeding task files to --syntax-check is obviously wrong. The
# simulation passed, CI failed on the first push, and the exclusion that made
# the simulation pass was the very bug it existed to catch.
#
# It happened a second time: a `unit` job was added to ci.yml and not to this
# file, one commit after the warning above was written.
#
# A simulation that diverges from the thing it simulates is worse than no
# simulation, because it converts an unknown into a false assurance.
#
# When ci.yml changes, change this file in the SAME COMMIT.
#
# ---------------------------------------------------------------------------
# KNOWN, DELIBERATE DIVERGENCE
#
# CI's `unit` job runs on a runner with no Ansible installed, which proves the
# filter plugin's no-Ansible import path works. That cannot be reproduced on a
# development box where Ansible is installed. A pass here is necessary but not
# sufficient for that specific property; only CI can confirm it.
# ---------------------------------------------------------------------------
#
# Usage:
#   bash tests/simulate_ci.sh
#   ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/simulate_ci.sh

set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tests/_ansible_env.sh
. "${HERE}/_ansible_env.sh"

resolve_ansible || exit 2
cd "$(cd "${HERE}/.." && pwd)" || exit 2

FAILED=0
note() { printf '\n== %s ==\n' "$1"; }
verdict() { if [ "$1" -eq 0 ]; then echo "PASS"; else echo "FAIL"; FAILED=1; fi; }

note "environment"
report_ansible

note "clean slate"
rm -rf collections ansible.cfg reports
rm -f inventory/hosts.yml vars/baseline.yml vars/mail.yml
rm -f inventory/group_vars/all.yml inventory/group_vars/ios_devices.yml \
      inventory/group_vars/linux_hosts.yml
echo "removed generated config and collections"

# ---- job: leak-check ---------------------------------------------------
note "job: leak-check"
bash tests/test_leak_check.sh >/dev/null 2>&1
verdict $?

# ---- job: unit ---------------------------------------------------------
note "job: unit -> filter plugin unit tests"
python3 -m unittest discover -s tests -p 'test_*.py' >/tmp/ut.txt 2>&1
verdict $?
tail -3 /tmp/ut.txt

# ---- job: lint ---------------------------------------------------------
note "job: lint -> yamllint ."
yamllint . 2>&1 | tail -5
yamllint . >/dev/null 2>&1
verdict $?

# ---- job: syntax -------------------------------------------------------
# Order matches ci.yml: stage config, fixture tests, install, syntax.
note "job: syntax -> stage example configuration"
cp ansible.cfg.example ansible.cfg
cp inventory/hosts.yml.example inventory/hosts.yml
for f in inventory/group_vars/*.yml.example; do cp "$f" "${f%.example}"; done
for f in vars/*.yml.example; do cp "$f" "${f%.example}"; done
echo staged

note "job: syntax -> fixture-driven logic tests"
ansible-playbook -i localhost, tests/test_baseline_logic.yml >/tmp/fx.txt 2>&1
verdict $?
grep -E 'All [0-9]+ assertions|Divergent' /tmp/fx.txt | head -3

note "job: syntax -> install pinned collections"
ansible-galaxy collection install -r requirements.yml >/tmp/gx.txt 2>&1
verdict $?
grep -c 'installed successfully' /tmp/gx.txt | xargs -I{} echo "{} collections installed"
if [ -d collections/ansible_collections ]; then
  echo "landed in ./collections - correct"
else
  echo "NOT in ./collections - collections_path ordering bug is back"; FAILED=1
fi

# ansible-lint belongs to the lint job, which in CI runs on a BARE checkout
# with no config and no collections. Running it here after staging is a
# different test. tests/test_bare_lint.sh reproduces the CI conditions.
note "job: lint -> ansible-lint (staged tree; see test_bare_lint.sh for CI conditions)"
ansible-lint >/tmp/al.txt 2>&1
AL=$?
sed -n '/Rule Violation Summary/,/^$/p' /tmp/al.txt
verdict $AL

note "job: syntax -> syntax-check every playbook (VERBATIM find from ci.yml)"
rc=0
while IFS= read -r pb; do
  if ansible-playbook --syntax-check "$pb" >/dev/null 2>&1; then
    echo "  ok   $pb"
  else
    echo "  FAIL $pb"; rc=1
  fi
done < <(find playbooks -name '*.yml' -type f \
           -not -path 'playbooks/*/tasks/*' | sort)
verdict $rc

note "cleanup generated files"
rm -f ansible.cfg inventory/hosts.yml vars/baseline.yml vars/mail.yml
rm -f inventory/group_vars/all.yml inventory/group_vars/ios_devices.yml \
      inventory/group_vars/linux_hosts.yml
echo "done"

note "RESULT"
if [ $FAILED -eq 0 ]; then echo "CI SIMULATION PASSED"; else echo "CI SIMULATION FAILED"; fi
exit $FAILED
