# 06. `| int` on a formatted string returns 0 and causes false PASSes

> **Category:** Evaluation logic · Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)

**Symptom:** A threshold check passes on every device, including ones that
should fail.

**Cause:** SNMP TimeTicks and similar values often arrive pre-formatted:

```
9:0:07:42.73
```

`{{ value | int }}` on that returns `0` — no error, no warning. A check of the
form `value | int > threshold` then evaluates against zero and behaves
consistently, wrongly.

**Fix:** Request raw integers where the tool allows it (`snmpget -Ovqt`), and
guard the comparison so a non-numeric value forces a SKIP rather than falling
through to a PASS:

```yaml
_le_numeric: "{{ raw_value is match('^[0-9]+$') }}"
```

Treat `not _le_numeric` as SKIP, never as PASS. A check that cannot evaluate
its input has not passed.

---

← [05. ansible_become: false in group_vars silently drops privilege](Gotcha-05-ansible-become-false-in-group-vars-silently-drops-privilege) · [All gotchas](Gotchas) · [07. A naive dotted-quad regex fires on IOS image filenames](Gotcha-07-a-naive-dotted-quad-regex-fires-on-ios-image-filenames) →
