#!/usr/bin/env bash
#
# test_masking.sh - wrapper for tests/test_report_masking.yml.
#
# WHY A WRAPPER AND NOT A DIRECT ansible-playbook CALL
#
# The masking test renders a template that calls mask_ip, mask_mac and
# mask_hostname. Those resolve through the filter_plugins path declared in
# ansible.cfg, and ansible.cfg is gitignored -- it exists only as
# ansible.cfg.example until someone stages it. run_tests.sh cannot assume it
# is present, and must not leave one behind if it was not.
#
# So this stages a config, runs the test, and restores whatever was there
# before. Same shape as test_filter_path.sh, which manipulates ansible.cfg for
# a different reason.
#
# CI's syntax job stages config for its own purposes and can call the playbook
# directly; it does not need this wrapper.
#
# Usage:
#   bash tests/test_masking.sh
#   ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/test_masking.sh

set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tests/_ansible_env.sh
. "${HERE}/_ansible_env.sh"

resolve_ansible || exit 2
ROOT="$(cd "${HERE}/.." && pwd)"
cd "$ROOT" || exit 2

RESTORE=0
if [ -f ansible.cfg ]; then
    cp ansible.cfg "${ROOT}/.ansible.cfg.maskbak"
    RESTORE=1
fi

cleanup() {
    if [ "$RESTORE" -eq 1 ]; then
        mv "${ROOT}/.ansible.cfg.maskbak" ansible.cfg
    else
        rm -f ansible.cfg
    fi
}
trap cleanup EXIT

cp ansible.cfg.example ansible.cfg

# Both masking tests run under the same staged config. Kept in one wrapper
# rather than two: duplicating the stage/restore logic would mean two copies
# that can disagree about what "staged" means, and the second copy is the one
# nobody updates.
RC=0
ansible-playbook -i localhost, tests/test_report_masking.yml || RC=1
ansible-playbook -i localhost, tests/test_health_report_masking.yml || RC=1
ansible-playbook -i localhost, tests/test_listener_report_masking.yml || RC=1
exit $RC
