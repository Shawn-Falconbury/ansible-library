#!/usr/bin/env bash
#
# test_leak_check.sh - verify the leak checker before trusting it.
#
# A scrubbing tool that silently stops matching is worse than no tool at all,
# because it converts an active check into a false assurance. This harness
# therefore asserts the negative path first: the checker MUST fail on a file
# full of deliberately planted leaks. Only then does it assert the positive
# path, that a file of known-good placeholder values comes back clean.
#
# The fixtures carry a .txt suffix so that the repository-wide leak scan does
# not read the deliberately-poisoned file as a real finding. tests/negative/
# is excluded from the main scan for the same reason.
#
# Usage:  tests/test_leak_check.sh
# Exit:   0 all assertions passed, 1 otherwise

set -o nounset
set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
CHECKER="${REPO_ROOT}/scripts/leak_check.py"

FAILURES=0
WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

# --------------------------------------------------------------------------
# Assertion 1: the checker must FAIL on planted leaks.
# --------------------------------------------------------------------------
echo "negative path -- checker must reject planted leaks"

mkdir -p "${WORKDIR}/negative"
cp "${HERE}/negative/leak_fixtures_must_fail.yml.txt" \
   "${WORKDIR}/negative/bad.yml"

output="$(python3 "${CHECKER}" "${WORKDIR}/negative" 2>&1)"
rc=$?

if [[ ${rc} -eq 0 ]]; then
    fail "checker returned clean on a file full of leaks (rc=0)"
    echo "${output}"
else
    pass "checker exited non-zero (rc=${rc})"
fi

# Each planted category must be named in the output. If a category silently
# stops matching, this is where it surfaces.
for kind in ipv4-address ipv6-address mac-address domain-name \
            email-address literal-secret; do
    if grep -q "${kind}" <<<"${output}"; then
        pass "detected ${kind}"
    else
        fail "did NOT detect ${kind} -- pattern regression"
    fi
done

# --------------------------------------------------------------------------
# Assertion 2: the checker must PASS on approved placeholders.
# --------------------------------------------------------------------------
echo
echo "positive path -- checker must accept documentation placeholders"

mkdir -p "${WORKDIR}/positive"
cp "${HERE}/fixtures/leak_fixtures_must_pass.yml.txt" \
   "${WORKDIR}/positive/good.yml"

if python3 "${CHECKER}" "${WORKDIR}/positive" >/dev/null 2>&1; then
    pass "documentation-range placeholders accepted"
else
    fail "false positive on approved placeholders:"
    python3 "${CHECKER}" "${WORKDIR}/positive" 2>&1 | sed 's/^/    /'
fi

# --------------------------------------------------------------------------
# Assertion 3: the live repository must be clean.
# --------------------------------------------------------------------------
echo
echo "repository scan -- working tree must be clean"

if python3 "${CHECKER}" "${REPO_ROOT}" >/dev/null 2>&1; then
    pass "repository contains no detectable environment data"
else
    fail "repository scan found leaks:"
    python3 "${CHECKER}" "${REPO_ROOT}" 2>&1 | sed 's/^/    /'
fi

echo
if [[ ${FAILURES} -ne 0 ]]; then
    echo "${FAILURES} assertion(s) failed"
    exit 1
fi
echo "all assertions passed"
exit 0
