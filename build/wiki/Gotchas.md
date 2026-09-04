# Gotchas

**18 failure modes that produce a passing result.**

Ordinary errors are not interesting; they announce themselves. Everything
catalogued here ran, exited zero, and reported success while being wrong.

Each entry is its own page so it can be linked from a code review, a ticket,
or a playbook comment. The canonical source is
[`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)
in the repository — these pages are generated from it.

## Reachability and reporting

Failures where a host disappears from the run and its absence reads as health.

- **01.** [ansible.builtin.ping is not a connectivity test for network devices](Gotcha-01-ansible-builtin-ping-is-not-a-connectivity-test-for-network-devices)
- **02.** [Unreachable hosts are removed from the play before tasks are evaluated](Gotcha-02-unreachable-hosts-are-removed-from-the-play-before-tasks-are-evaluated)
- **03.** [Unreachable hosts have no facts — do not default them to zero](Gotcha-03-unreachable-hosts-have-no-facts-do-not-default-them-to-zero)

## Variable precedence

Inventory quietly outranking the play. No warning is emitted in any of these.

- **04.** [ansible_connection in group_vars outranks a play-level connection:](Gotcha-04-ansible-connection-in-group-vars-outranks-a-play-level-connection)
- **05.** [ansible_become: false in group_vars silently drops privilege](Gotcha-05-ansible-become-false-in-group-vars-silently-drops-privilege)
- **14.** [Plaintext vars can silently shadow a vaulted variable](Gotcha-14-plaintext-vars-can-silently-shadow-a-vaulted-variable)

## Evaluation logic

Checks that return PASS without having evaluated anything.

- **06.** [| int on a formatted string returns 0 and causes false PASSes](Gotcha-06-int-on-a-formatted-string-returns-0-and-causes-false-passes)
- **08.** [An empty play is not a passing play](Gotcha-08-an-empty-play-is-not-a-passing-play)
- **16.** [SKIP rolled up into PASS](Gotcha-16-skip-rolled-up-into-pass)

## Pattern matching

Regexes that match what they should not, and fail to match what they should.

- **07.** [A naive dotted-quad regex fires on IOS image filenames](Gotcha-07-a-naive-dotted-quad-regex-fires-on-ios-image-filenames)

## Structure and plugin discovery

Valid YAML in the wrong place, and plugins Ansible never looks for.

- **15.** [delegate_to and run_once at play level parse but do not work](Gotcha-15-delegate-to-and-run-once-at-play-level-parse-but-do-not-work)
- **18.** [filter_plugins/ is discovered next to the playbook, not the project root](Gotcha-18-filter-plugins-is-discovered-next-to-the-playbook-not-the-project-root)

## Setup and CI ordering

Steps that each report success while the sequence as a whole is wrong.

- **17.** [ansible-galaxy reads collections_path, but only if ansible.cfg exists yet](Gotcha-17-ansible-galaxy-reads-collections-path-but-only-if-ansible-cfg-exists-yet)
- **11.** [Scheduler re-runs may pin to the original commit](Gotcha-11-scheduler-re-runs-may-pin-to-the-original-commit)
- **12.** [Unpinned collections re-resolve on every run](Gotcha-12-unpinned-collections-re-resolve-on-every-run)

## Secrets and environment

Places where a secret, or the explanation of a failure, ends up somewhere unintended.

- **09.** [Hardcoded no_log: true makes credential failures undebuggable](Gotcha-09-hardcoded-no-log-true-makes-credential-failures-undebuggable)
- **10.** [Verify $HOME before writing to ~/](Gotcha-10-verify-home-before-writing-to)
- **13.** [git-receive-pack does not inherit command-scope -c config](Gotcha-13-git-receive-pack-does-not-inherit-command-scope-c-config)

---

## Adding one

Append a `## N. Title` section to `docs/gotchas.md`, assign the number to a
group in `scripts/build_wiki.py`, and rebuild. The build refuses to complete
if a gotcha is ungrouped, so a new entry cannot quietly fail to appear here.
