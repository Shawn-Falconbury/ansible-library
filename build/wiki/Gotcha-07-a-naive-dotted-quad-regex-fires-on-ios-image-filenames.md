# 07. A naive dotted-quad regex fires on IOS image filenames

> **Category:** Pattern matching · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A leak scan or address parser flags `cat9k_iosxe.17.06.06.SPA.bin`.

**Cause:** `\d+\.\d+\.\d+\.\d+` matches `17.06.06` in context, and version
strings generally.

**Fix:** Validate each octet against 0–255 and anchor on word boundaries that
reject adjacent dots and word characters. See the `RE_IPV4` pattern in
`scripts/leak_check.py`.

The inverse mistake is worth noting too: a keyword regex anchored with `\b`
will never match inside `snmp_community`, because `_` is a word character and
supplies no boundary. Both directions of this failure are silent.

---

← [06. | int on a formatted string returns 0 and causes false PASSes](Gotcha-06-int-on-a-formatted-string-returns-0-and-causes-false-passes) · [All gotchas](Gotchas) · [08. An empty play is not a passing play](Gotcha-08-an-empty-play-is-not-a-passing-play) →
