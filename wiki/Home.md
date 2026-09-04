# Ansible Network &amp; Systems Reference

Reference implementations of network and systems automation patterns, written
to be read as much as run.

Every playbook is a clean-room implementation. Nothing here is a sanitised copy
of a working environment — no real address, hostname, credential, or
organisation name has ever been committed, and CI enforces that on every push.
What is preserved is the *technique*, and the reasoning behind it.

---

## The thesis

**Most of these playbooks exist because the obvious implementation was wrong in
a way that produced a passing result.**

That is the whole premise. A playbook that errors out is a nuisance. A playbook
that reports 100% healthy while three switches are powered off is a liability,
because it replaces a known unknown with a false certainty — and nothing in the
output distinguishes the two.

So the catalogue of failure modes is not an appendix to this repository. It is
the point of it.

### → **[The gotchas catalogue](Gotchas)** — 18 documented silent failures

---

## Where to go

| If you want to | Go to |
|---|---|
| Understand why this repo exists | **[Gotchas](Gotchas)** |
| Run something | [Getting started](Getting-Started) |
| See what exists and what is planned | [Playbook catalogue](Playbook-Catalogue) |
| Contribute, or match the house style | [Conventions](Conventions) |
| Understand the testing stance | [Testing philosophy](Testing-Philosophy) |
| Understand the no-real-data rule | [Security model](Security-Model) |

---

## Three examples of the pattern

**A reachability check that always passes.**
`ansible.builtin.ping` is resolved by an action plugin on the control node. For
a host using the `network_cli` connection plugin it never opens a session to
the device, and returns `pong` for a switch that has been off for months. The
same module against an SSH-connected Linux host *is* a real test. Same task,
opposite meaning, no warning.
→ [Gotcha 01](Gotcha-01-ansible-builtin-ping-is-not-a-connectivity-test-for-network-devices)

**A threshold check that passes on every device.**
SNMP TimeTicks arrive pre-formatted as `9:0:07:42.73`. `{{ value | int }}`
returns `0` — no error, no warning. Every `value | int > threshold` comparison
then evaluates against zero and behaves consistently, wrongly.
→ [Gotcha 06](Gotcha-06-int-on-a-formatted-string-returns-0-and-causes-false-passes)

**A compliance report where nothing was evaluated.**
If the summary only counts FAILs, a device whose checks all skipped is
indistinguishable from a clean one. SKIP has to be a first-class status that
the run fails on, because unknown is not acceptable.
→ [Gotcha 16](Gotcha-16-skip-rolled-up-into-pass)

---

## What is enforced rather than requested

- **No real environment data.** `scripts/leak_check.py` scans the tree for
  addresses outside the RFC 5737 documentation ranges, MAC addresses outside
  RFC 7042, non-`.example` domains, and credential-shaped assignments. It runs
  on every push and weekly. See [Security model](Security-Model).
- **The scanner is tested before it is trusted.** `tests/test_leak_check.sh`
  asserts the negative path first, category by category, and only then accepts
  a clean verdict. A scanner that has silently stopped matching is worse than
  no scanner.
- **Collections are pinned.** Unpinned collections re-resolve on every run and
  change module behaviour with nothing in git to point at.
  → [Gotcha 12](Gotcha-12-unpinned-collections-re-resolve-on-every-run)
- **Only `.example` files are tracked.** Filled-in copies are gitignored, so
  the failure mode is a missing file (loud) rather than a committed credential
  (silent).

---

## About this wiki

These pages are **generated** from the repository by `scripts/build_wiki.py`.
The canonical text lives in `docs/`, ships with every clone, and is what a
reader who arrives directly at a playbook will find. The wiki exists so that
each gotcha has a stable, linkable URL you can drop into a code review.

Edit the repository, not the wiki. CI fails if the two diverge.

Verified against ansible-core 2.16 and 2.17. MIT licensed.
