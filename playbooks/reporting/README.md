# playbooks/reporting

Health reporting and notification.

| Playbook | Status | Purpose |
|---|---|---|
| `service_health.yml` | complete | Service state and certificate-expiry monitoring with unreachable-host detection. Dual-rendered, leak-scanned before send, optional mail. Evaluation is a separate task file: 11 fixture cases, 33 assertions, no hosts. |

## Pattern

Reporting playbooks are where silent failures concentrate, because their
output is a document that looks the same whether or not it is correct.

Three rules apply to everything in this directory:

- `ignore_errors` / `ignore_unreachable` so failed hosts stay visible.
- Unreachable hosts detected via the `ansible_play_hosts_all` diff, never by
  absence from a loop.
- Metric fields **omitted** for unreachable hosts, never defaulted to zero — a
  zero renders as a measurement and reads as healthy.

See `docs/gotchas.md` entries 2 and 3.
