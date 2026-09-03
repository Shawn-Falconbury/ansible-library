#!/usr/bin/env python3
"""
leak_check.py - fail loudly if anything that looks like real environment data
has made it into the repository.

This repo contains reference implementations only. No real address, hostname,
credential, or domain should ever appear in it. This script is the gate that
enforces that, and it runs in CI on every push and pull request.

Design notes
------------
The IPv4 pattern is octet-validated and word-boundary anchored. A naive
dotted-quad regex (\\d+\\.\\d+\\.\\d+\\.\\d+) produces false positives on things
that are legitimately present in network automation repos, most notably IOS
image filenames such as:

    cat9k_iosxe.17.06.06.SPA.bin
    c2960x-universalk9-mz.152-7.E7.bin

Those are not addresses. The pattern below requires four octets each in the
range 0-255 with nothing word-adjacent, which rejects the image filename cases
while still catching a genuine address.

Allowlisted address space is the documentation ranges from RFC 5737 plus
loopback, link-local, the RFC 3849 IPv6 documentation prefix, and the
unspecified/broadcast addresses. Anything outside that is treated as a leak,
including RFC 1918 space -- private addresses are still real addresses and
still describe someone's network.

Exit codes
----------
0  clean
1  one or more findings
2  usage or internal error

Adding an exception
-------------------
Prefer changing the file. If a finding is genuinely a false positive, add an
inline waiver comment on the same line:

    something_that_trips_the_regex   # leak-check: allow

Waivers are counted and printed in the summary so they cannot accumulate
silently.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

WAIVER = "leak-check: allow"

# Directories never scanned.
SKIP_DIRS = {
    ".git",
    ".github/workflows",  # contains no env data; excluded to avoid self-match
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    "collections",
    "tests/negative",  # deliberately poisoned fixtures
    "tests/fixtures",
}

# Extensions treated as binary and skipped.
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
    ".gz", ".tgz", ".zip", ".bin", ".pyc", ".so",
}

# Address space that is safe to publish.
ALLOWED_NETWORKS = [
    ipaddress.ip_network("192.0.2.0/24"),     # RFC 5737 TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # RFC 5737 TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # RFC 5737 TEST-NET-3
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("0.0.0.0/32"),       # unspecified
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("224.0.0.0/4"),      # multicast, used in protocol docs
]

ALLOWED_V6_NETWORKS = [
    ipaddress.ip_network("2001:db8::/32"),    # RFC 3849 documentation
    ipaddress.ip_network("::/128"),       # unspecified
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
]

# Domains that are safe to publish.
ALLOWED_DOMAIN_SUFFIXES = (
    "example.com",
    "example.org",
    "example.net",
    "example",       # lab.example, site-a.example
    "invalid",
    "localhost",
    "localdomain",
    "test",
)

# Public infrastructure that legitimately appears in tooling configuration and
# documentation links. These are not environment data -- they are the same for
# everyone. Keep this list short and exact; it is an allowlist, not a
# convenience hatch for "domains that felt fine".
# RFC 7042 section 2.1.2 reserves 00-00-5E-00-53-00 through
# 00-00-5E-00-53-FF for documentation. It is the MAC equivalent of the
# RFC 5737 address ranges, and the same rule applies: a documentation
# value is publishable, anything else is a finding. Matched
# case-insensitively and across all three notations.
ALLOWED_MAC_PREFIXES = (
    "00:00:5e:00:53:",
    "00-00-5e-00-53-",
    "0000.5e00.53",
)

ALLOWED_EXACT_DOMAINS = {
    "github.com",
    "api.github.com",
    "raw.githubusercontent.com",
    "galaxy.ansible.com",
    "docs.ansible.com",
    "pypi.org",
    "pre-commit.com",
    "letsencrypt.org",
}

# Hostnames/domains that are structurally fine but we never want committed.
# Extend this list with anything specific you want permanently barred.
DENY_SUBSTRINGS: list[str] = [
    # Populate with organisation-specific strings you never want published.
    # Kept empty in the public repo so the list itself leaks nothing.
]

# --------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------

# Octet-validated IPv4. Word-boundary anchored on both sides, and explicitly
# rejects a leading or trailing dot-digit so that version strings and image
# filenames (17.06.06, 152-7.E7) do not match.
_OCTET = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
RE_IPV4 = re.compile(
    rf"(?<![\w.]){_OCTET}\.{_OCTET}\.{_OCTET}\.{_OCTET}(?![\w.])"
)

# IPv6 candidates. Deliberately loose -- it grabs any run of hex groups and
# colons containing at least two colons, then hands the token to
# ipaddress.ip_address() for the real decision. An earlier version anchored on
# (?:hex:){2,7}hex and silently missed every compressed address, because the
# empty group in "2001:db8::1" breaks that pattern. Validate, do not pre-judge.
RE_IPV6 = re.compile(
    r"(?<![\w:.])(?=[0-9A-Fa-f:]*:[0-9A-Fa-f:]*:)"
    r"[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){1,7}(?![\w:.])"
)

# MAC addresses in colon, hyphen, or Cisco dotted-triplet form.
RE_MAC = re.compile(
    r"(?<![\w:.-])(?:"
    r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}"
    r"|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5}"
    r"|[0-9A-Fa-f]{4}(?:\.[0-9A-Fa-f]{4}){2}"
    r")(?![\w:.-])"
)

# Bare domain names. Deliberately loose; filtered against the allowlist below.
RE_DOMAIN = re.compile(
    r"(?<![\w.@-])(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|io|local|lan|internal|corp|gov|edu|mil|us|co|dev|app)"
    # A dot in the trailing lookahead is load-bearing. Without it,
    # "sw-a-01.internal.corp.example" matched only as far as ".corp" and
    # was reported as a leak, even though the full name ends in the
    # allowlisted .example and is therefore fine.
    r"(?![\w.-])"
)

RE_EMAIL = re.compile(
    r"(?<![\w.@-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w-])"
)

# Assignments that look like a real secret rather than a placeholder.
#
# The key portion allows arbitrary affixes because the interesting variable
# names in this domain are almost never the bare word. A \b-anchored
# alternation misses snmp_community, ansible_password, and vault_authkey
# outright, since an underscore is a word character and therefore supplies no
# boundary. Match the whole token instead, then decide on the value.
RE_SECRETISH = re.compile(  # leak-check: allow
    r"""(?ix)
    (?<![\w.-])
    (?P<key>
        # No hyphen in the key character class, deliberately. Variable
        # names in YAML and INI use underscores; hyphens appear in prose.
        # With '-' included, the comment "the one legitimate pass-through:
        # there is no domain" parsed as key='pass-through', value='there'
        # and was reported as a literal secret.
        [A-Za-z0-9_.]*
        (?: password | passwd | passphrase | secret | api[_-]?key |
            token | community | authkey | privkey |
            pass(?![A-Za-z]) )
        [A-Za-z0-9_.]*
    )
    \s* [:=] \s*
    (?P<val>["']?[^\s"'#]{4,}["']?)
    """
)

# Values that are acceptable on the right-hand side of a secret-ish key.
PLACEHOLDER_MARKERS = (
    "changeme",
    "{{",            # a Jinja reference, not a literal
    "!vault",        # vault-encrypted
    "vault_",        # points at a vaulted variable
    "lookup(",
    "omit",
    "null",
    "none",
    "~",
    "\"\"",
    "''",
    "example",
    "redacted",
    "placeholder",
    "your_",
    "<",             # <set-me>, <your-password>
)

# Certificate and key material.
RE_KEY_BLOCK = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----"
)
RE_VAULT_BLOB = re.compile(r"\$ANSIBLE_VAULT;")  # leak-check: allow


@dataclass
class Finding:
    path: Path
    lineno: int
    kind: str
    value: str
    line: str

    def render(self, root: Path) -> str:
        rel = self.path.relative_to(root)
        return (
            f"{rel}:{self.lineno}: {self.kind}: {self.value}\n"
            f"    {self.line.strip()[:160]}"
        )


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def ipv4_is_allowed(text: str) -> bool:
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return True  # not actually an address
    return any(addr in net for net in ALLOWED_NETWORKS)


def ipv6_is_allowed(text: str) -> bool:
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return True
    return any(addr in net for net in ALLOWED_V6_NETWORKS)


def mac_is_allowed(text: str) -> bool:
    lowered = text.lower()
    return lowered.startswith(ALLOWED_MAC_PREFIXES)


def domain_is_allowed(text: str) -> bool:
    lowered = text.lower().rstrip(".")
    if lowered in ALLOWED_EXACT_DOMAINS:
        return True
    return any(
        lowered == suffix or lowered.endswith("." + suffix)
        for suffix in ALLOWED_DOMAIN_SUFFIXES
    )


NON_SECRET_LITERALS = {
    "true", "false", "yes", "no", "on", "off", "enabled", "disabled",
}


def secret_value_is_placeholder(value: str) -> bool:
    """True if the right-hand side is clearly not a real credential.

    The keyword alternation is deliberately greedy -- 'pass' anchored at the
    end of a token catches vault_pass and ssh_pass, but it also catches
    'bypass'. Rather than narrowing the key pattern and reopening the gap that
    let vault_pass through, filter here: a boolean or a bare number is never a
    credential, so 'bypass: true' resolves cleanly without a waiver.
    """
    lowered = value.strip().strip("\"'").lower()
    if not lowered:
        return True
    if lowered in NON_SECRET_LITERALS:
        return True
    try:
        float(lowered)
        return True
    except ValueError:
        pass
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def scan_line(path: Path, lineno: int, line: str) -> list[Finding]:
    found: list[Finding] = []

    def add(kind: str, value: str) -> None:
        found.append(Finding(path, lineno, kind, value, line))

    for match in RE_IPV4.finditer(line):
        if not ipv4_is_allowed(match.group(0)):
            add("ipv4-address", match.group(0))

    for match in RE_IPV6.finditer(line):
        if not ipv6_is_allowed(match.group(0)):
            add("ipv6-address", match.group(0))

    for match in RE_MAC.finditer(line):
        if not mac_is_allowed(match.group(0)):
            add("mac-address", match.group(0))

    for match in RE_EMAIL.finditer(line):
        domain = match.group(0).split("@", 1)[1]
        if not domain_is_allowed(domain):
            add("email-address", match.group(0))

    for match in RE_DOMAIN.finditer(line):
        if not domain_is_allowed(match.group(0)):
            add("domain-name", match.group(0))

    for match in RE_SECRETISH.finditer(line):
        value = match.group("val")
        if not secret_value_is_placeholder(value):
            add("literal-secret", f"{match.group('key')} = {value[:24]}")

    if RE_KEY_BLOCK.search(line):
        add("private-key-block", "PEM private key header")

    if RE_VAULT_BLOB.search(line):
        add("vault-blob", "encrypted vault payload committed")

    for needle in DENY_SUBSTRINGS:
        if needle and needle.lower() in line.lower():
            add("denylisted-string", needle)

    return found


def should_skip(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    for skip in SKIP_DIRS:
        skip_parts = tuple(skip.split("/"))
        if rel_parts[: len(skip_parts)] == skip_parts:
            return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return False


def scan_repo(root: Path) -> tuple[list[Finding], int, int]:
    findings: list[Finding] = []
    waived = 0
    scanned = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        scanned += 1
        for lineno, line in enumerate(text.splitlines(), start=1):
            if WAIVER in line:
                waived += 1
                continue
            findings.extend(scan_line(path, lineno, line))

    return findings, waived, scanned


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail if real environment data appears in the repository."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=os.environ.get("LEAK_CHECK_ROOT", "."),
        help="Repository root to scan (default: current directory).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the summary line on a clean run.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"leak_check: not a directory: {root}", file=sys.stderr)
        return 2

    findings, waived, scanned = scan_repo(root)

    if findings:
        print(f"leak_check: {len(findings)} finding(s)\n", file=sys.stderr)
        for finding in findings:
            print(finding.render(root), file=sys.stderr)
        print(
            f"\nScanned {scanned} file(s); {waived} line(s) waived.",
            file=sys.stderr,
        )
        print(
            "\nThis repository publishes reference implementations only.\n"
            "Replace the value above with a documented variable, or use a\n"
            "documentation-range placeholder (see docs/conventions.md).",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(f"leak_check: clean ({scanned} files, {waived} waived)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
