# shellcheck shell=bash
#
# _ansible_env.sh - shared environment resolution for the test scripts.
# Sourced, not executed.
#
# WHY THIS EXISTS
#
# These scripts were developed against one machine with ansible-core in
# ~/venvs/ansible-2.16, and all three hardcoded that path. That works exactly
# once, on one box, for one person. Worse, a hardcoded PATH prepend silently
# selects a version: run the suite expecting 2.16 on a host where that venv
# does not exist and you get whatever `ansible-playbook` resolves to, with no
# indication the version changed.
#
# So: resolution is explicit and the version is always reported.
#
# Order of preference:
#   1. $ANSIBLE_VENV, if set -- an explicit choice by the caller
#   2. whatever is already on PATH -- an activated venv, or a system install
#   3. fail, with instructions
#
# Note there is no automatic search of ~/venvs. Guessing which of several
# installed versions the caller meant is precisely the behaviour that makes
# "it passed locally" untrustworthy.

resolve_ansible() {
    if [ -n "${ANSIBLE_VENV:-}" ]; then
        if [ ! -x "${ANSIBLE_VENV}/bin/ansible-playbook" ]; then
            echo "ANSIBLE_VENV is set to '${ANSIBLE_VENV}' but" >&2
            echo "${ANSIBLE_VENV}/bin/ansible-playbook is not executable." >&2
            return 1
        fi
        PATH="${ANSIBLE_VENV}/bin:${PATH}"
        export PATH
    fi

    if ! command -v ansible-playbook >/dev/null 2>&1; then
        cat >&2 <<'MSG'
ansible-playbook not found.

Activate a virtualenv that has ansible-core installed, or point at one:

    ANSIBLE_VENV=~/venvs/ansible-2.16 bash tests/run_tests.sh

The repository's CI tests ansible-core 2.16 and 2.17. Running the suite
against a much newer core may pass here and fail there.
MSG
        return 1
    fi

    ANSIBLE_CORE_VERSION="$(ansible --version 2>/dev/null | head -1)"
    export ANSIBLE_CORE_VERSION
    return 0
}

# Print the resolved interpreter and version. Always call this before running
# anything, so a passing run says which version it passed against.
report_ansible() {
    printf 'ansible:  %s\n' "$(command -v ansible-playbook)"
    printf 'version:  %s\n' "${ANSIBLE_CORE_VERSION:-unknown}"
}

# Repository root, derived from this file's location rather than from $PWD or
# a hardcoded path, so the scripts work from any working directory.
repo_root() {
    ( cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd )
}
