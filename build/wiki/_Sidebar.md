### [Home](Home)

**Using it**
- [Getting started](Getting-Started)
- [Playbook catalogue](Playbook-Catalogue)
- [Conventions](Conventions)

**Why it is built this way**
- [Testing philosophy](Testing-Philosophy)
- [Security model](Security-Model)

**[Gotchas](Gotchas)** (18)
<details><summary>Reachability and reporting</summary>

- [01. ansible.builtin.ping is not a connectivity test for network devices](Gotcha-01-ansible-builtin-ping-is-not-a-connectivity-test-for-network-devices)
- [02. Unreachable hosts are removed from the play before tasks are evaluated](Gotcha-02-unreachable-hosts-are-removed-from-the-play-before-tasks-are-evaluated)
- [03. Unreachable hosts have no facts — do not default them to zero](Gotcha-03-unreachable-hosts-have-no-facts-do-not-default-them-to-zero)

</details>
<details><summary>Variable precedence</summary>

- [04. ansible_connection in group_vars outranks a play-level connection:](Gotcha-04-ansible-connection-in-group-vars-outranks-a-play-level-connection)
- [05. ansible_become: false in group_vars silently drops privilege](Gotcha-05-ansible-become-false-in-group-vars-silently-drops-privilege)
- [14. Plaintext vars can silently shadow a vaulted variable](Gotcha-14-plaintext-vars-can-silently-shadow-a-vaulted-variable)

</details>
<details><summary>Evaluation logic</summary>

- [06. | int on a formatted string returns 0 and causes false PASSes](Gotcha-06-int-on-a-formatted-string-returns-0-and-causes-false-passes)
- [08. An empty play is not a passing play](Gotcha-08-an-empty-play-is-not-a-passing-play)
- [16. SKIP rolled up into PASS](Gotcha-16-skip-rolled-up-into-pass)

</details>
<details><summary>Pattern matching</summary>

- [07. A naive dotted-quad regex fires on IOS image filenames](Gotcha-07-a-naive-dotted-quad-regex-fires-on-ios-image-filenames)

</details>
<details><summary>Structure and plugin discovery</summary>

- [15. delegate_to and run_once at play level parse but do not work](Gotcha-15-delegate-to-and-run-once-at-play-level-parse-but-do-not-work)
- [18. filter_plugins/ is discovered next to the playbook, not the project root](Gotcha-18-filter-plugins-is-discovered-next-to-the-playbook-not-the-project-root)

</details>
<details><summary>Setup and CI ordering</summary>

- [17. ansible-galaxy reads collections_path, but only if ansible.cfg exists yet](Gotcha-17-ansible-galaxy-reads-collections-path-but-only-if-ansible-cfg-exists-yet)
- [11. Scheduler re-runs may pin to the original commit](Gotcha-11-scheduler-re-runs-may-pin-to-the-original-commit)
- [12. Unpinned collections re-resolve on every run](Gotcha-12-unpinned-collections-re-resolve-on-every-run)

</details>
<details><summary>Secrets and environment</summary>

- [09. Hardcoded no_log: true makes credential failures undebuggable](Gotcha-09-hardcoded-no-log-true-makes-credential-failures-undebuggable)
- [10. Verify $HOME before writing to ~/](Gotcha-10-verify-home-before-writing-to)
- [13. git-receive-pack does not inherit command-scope -c config](Gotcha-13-git-receive-pack-does-not-inherit-command-scope-c-config)

</details>
