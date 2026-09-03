# tests

## Principle

Make it fail first. A check observed only in its passing state has not been
observed.

Each test asserts, in order:

1. The check **fails** under wrong conditions.
2. The check **passes** under right conditions.
3. The failure message names the cause.

## `test_leak_check.sh`

Verifies `scripts/leak_check.py` before trusting its verdict on the repository.

Asserts category by category — IPv4, IPv6, MAC, domain, email, literal secret —
that each planted leak in `negative/leak_fixtures_must_fail.yml.txt` is
detected. If one pattern silently stops matching, that specific category fails
rather than the whole suite going quietly green.

Then asserts no false positives against
`fixtures/leak_fixtures_must_pass.yml.txt`, which includes the cases a naive
implementation gets wrong: IOS image filenames (`cat9k_iosxe.17.06.06.SPA.bin`),
bare version strings, `bypass:` and `passive_mode:` keys that trip a greedy
credential pattern, and Jinja references to vaulted variables.

Finally scans the live working tree.

```bash
bash tests/test_leak_check.sh
```

Fixtures carry a `.txt` suffix and their directories are excluded from the
repository scan, so the deliberately poisoned file is not itself reported as a
finding.

## Fixture-based playbook tests

Network playbooks cannot be tested against real hardware in CI. The approach
here is to separate the *logic* from the *collection* — assertion and
threshold logic runs against recorded fixture data on `localhost`, so the
comparison being tested is exercised without a device present.

This is what catches gotcha 6: a fixture containing a formatted TimeTicks value
(`9:0:07:42.73`) proves that `| int` yields `0` and that the guard forces SKIP
rather than PASS.
