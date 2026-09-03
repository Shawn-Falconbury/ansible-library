#!/usr/bin/env python3
"""Verify what GitHub actually published, independently of the local clone.

`git status` reports what your clone believes it pushed. This asks GitHub what
it received. The two have diverged before -- a push can succeed while the
commit carries file modes, an author identity, or paths you did not intend,
and none of that is visible from `git log`.

Checks:
  * repository is public, on the expected default branch
  * head commit author identity, and whether it links to a GitHub account
  * no disallowed paths published (collections/, generated config, reports/)
  * script files carry the executable bit
  * latest CI run and the per-job conclusions

The repository slug is derived from the `origin` remote rather than hardcoded,
so this works unchanged in a fork.

Usage:
    python3 scripts/verify_published.py
    python3 scripts/verify_published.py --repo owner/name

Unauthenticated API calls are rate limited to 60/hour per IP, which is ample
for interactive use and will not survive a loop.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

# Paths that must never appear in a published tree. Each is either generated,
# installed, or a filled-in copy of an .example file.
DISALLOWED_PREFIXES = ("collections/", "reports/")
DISALLOWED_EXACT = {
    "ansible.cfg",
    "inventory/hosts.yml",
    "inventory/group_vars/all.yml",
    "inventory/group_vars/ios_devices.yml",
    "inventory/group_vars/linux_hosts.yml",
    "vars/baseline.yml",
    "vars/mail.yml",
}


def detect_repo() -> str:
    """Derive owner/name from the origin remote."""
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("could not read the origin remote; pass --repo owner/name")

    # git@github.com:owner/name.git  or  https://github.com/owner/name.git
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        sys.exit("origin does not look like a GitHub remote: {0}".format(url))
    return m.group(1)


def api(repo: str, path: str = ""):
    url = "https://api.github.com/repos/{0}{1}".format(repo, path)
    try:
        with urllib.request.urlopen(url) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            sys.exit("GitHub API rate limit reached for this IP. Try later.")
        if exc.code == 404:
            sys.exit("not found: {0} (private repo, or wrong slug?)".format(url))
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", help="owner/name; default: derived from origin")
    args = ap.parse_args()

    repo = args.repo or detect_repo()
    print("repository: {0}\n".format(repo))

    failures = []

    meta = api(repo)
    lic = (meta.get("license") or {}).get("spdx_id")
    print("== metadata ==")
    print("  visibility      {0}".format(meta.get("visibility")))
    print("  default branch  {0}".format(meta.get("default_branch")))
    print("  license         {0}".format(lic))
    print("  description     {0}".format(meta.get("description") or "(none set)"))

    branch = meta.get("default_branch", "main")
    commit = api(repo, "/commits/{0}".format(branch))
    author = commit["commit"]["author"]
    login = (commit.get("author") or {}).get("login")
    print("\n== head commit ==")
    print("  sha       {0}".format(commit["sha"][:12]))
    print("  author    {0} <{1}>".format(author["name"], author["email"]))
    print("  subject   {0}".format(commit["commit"]["message"].splitlines()[0]))
    if login:
        print("  login     {0}".format(login))
    else:
        # Not fatal, but worth surfacing: it usually means the commit email
        # is not registered on the account, so the commit shows as authored
        # by nobody and does not count toward the contribution graph.
        print("  login     UNLINKED - commit email not registered on any account")

    tree = api(repo, "/git/trees/{0}?recursive=1".format(branch))
    blobs = [t for t in tree.get("tree", []) if t["type"] == "blob"]
    paths = {t["path"] for t in blobs}
    print("\n== published tree ==")
    print("  files      {0}".format(len(blobs)))

    bad = sorted(
        p for p in paths
        if p.startswith(DISALLOWED_PREFIXES) or p in DISALLOWED_EXACT
    )
    if bad:
        print("  DISALLOWED published:")
        for p in bad:
            print("    {0}".format(p))
        failures.append("{0} disallowed path(s) published".format(len(bad)))
    else:
        print("  disallowed no generated config, collections or reports")

    execs = sorted(t["path"] for t in blobs if t["mode"] == "100755")
    print("  executable {0}".format(", ".join(execs) if execs else "NONE"))

    # Any shipped .sh or .py meant to be invoked directly should be 100755.
    # git records the mode, so a file committed 0644 is not executable for
    # anyone who clones, regardless of its mode on the machine that pushed it.
    should_exec = sorted(
        p for p in paths
        if (p.startswith(("scripts/", "tests/")) and p.endswith((".sh", ".py")))
        and not p.rsplit("/", 1)[-1].startswith("_")
        and not p.rsplit("/", 1)[-1].startswith("test_mask")
    )
    missing = [p for p in should_exec if p not in execs]
    if missing:
        print("  MISSING exec bit:")
        for p in missing:
            print("    {0}".format(p))
        failures.append("{0} file(s) missing the exec bit".format(len(missing)))

    runs = api(repo, "/actions/runs?per_page=5").get("workflow_runs", [])
    print("\n== workflow runs ==")
    if not runs:
        print("  none yet")
    else:
        for r in runs:
            print("  {0:6} {1:11} {2:10} {3}".format(
                r.get("name", "?"), r.get("status", "?"),
                str(r.get("conclusion")), (r.get("head_sha") or "")[:8]))

        latest = runs[0]
        if latest.get("head_sha") != commit["sha"]:
            print("\n  note: latest run is not for the head commit")
        jobs = api(repo, "/actions/runs/{0}/jobs".format(latest["id"]))
        print("\n  jobs for {0}:".format((latest.get("head_sha") or "")[:8]))
        for j in jobs.get("jobs", []):
            print("    {0:20} {1}".format(
                j.get("name", "?"), str(j.get("conclusion"))))
            for s in j.get("steps", []):
                if s.get("conclusion") not in ("success", "skipped", None):
                    print("        FAILED STEP: {0}".format(s.get("name")))
        if latest.get("conclusion") not in ("success", None):
            failures.append("latest workflow run did not succeed")

    print()
    if failures:
        for f in failures:
            print("FAIL: {0}".format(f))
        return 1
    print("PUBLISHED STATE VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
