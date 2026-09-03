"""Masking filters for reports that leave the network they describe.

The dual-render pattern in this repository produces two copies of every
report: a masked one for distribution, and a full one archived at mode 0600.
These filters produce the masked copy.

DESIGN RULE: THESE FILTERS FAIL LOUDLY.

A masking filter that cannot parse its input must raise, never return the
input unchanged. Returning it unchanged is the worst available behaviour --
the value flows straight into a report labelled "masked" and gets emailed,
while the render still succeeds and every test still passes. The failure is
invisible precisely because the output looks like output.

So unparseable input is an error. A report that fails to render is a bad
afternoon; a report that renders with live addresses in it is an incident.
"""

from __future__ import annotations

import ipaddress
import re

try:
    from ansible.errors import AnsibleFilterError
except ImportError:  # pragma: no cover - permits standalone unit testing
    class AnsibleFilterError(Exception):
        """Stand-in so this module imports without Ansible present.

        tests/test_mask.py runs under plain `python3 -m unittest`, with no
        Ansible on the path. That matters: the masking logic is the part most
        worth testing and it should not need a working Ansible install to
        exercise.
        """


MASK_TOKEN = "xxx"
MAC_MASK_TOKEN = "xx"

# Cisco dotted-triplet, colon-separated, and hyphen-separated MAC forms.
_MAC_RE = re.compile(
    r"^(?:"
    r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}"
    r"|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5}"
    r"|[0-9A-Fa-f]{4}(?:\.[0-9A-Fa-f]{4}){2}"
    r")$"
)


def mask_ip(value, keep=2):
    """Mask an IP address, preserving the leading `keep` components.

        mask_ip('192.0.2.10')           -> '192.0.xxx.xxx'
        mask_ip('192.0.2.10', keep=1)   -> '192.xxx.xxx.xxx'
        mask_ip('2001:db8::1', keep=2)  -> '2001:0db8:xxx:xxx:xxx:xxx:xxx:xxx'

    Enough is preserved to correlate hosts within a subnet without publishing
    the address itself. Raises on anything that is not an IP address.
    """
    if value is None:
        raise AnsibleFilterError("mask_ip: refusing to mask None")

    text = str(value).strip()
    if not text:
        raise AnsibleFilterError("mask_ip: refusing to mask an empty value")

    try:
        keep = int(keep)
    except (TypeError, ValueError):
        raise AnsibleFilterError(
            "mask_ip: keep must be an integer, got {0!r}".format(keep)
        )
    if keep < 0:
        raise AnsibleFilterError("mask_ip: keep must not be negative")

    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        raise AnsibleFilterError(
            "mask_ip: {0!r} is not an IP address. Refusing to return it "
            "unchanged -- a value that passes through a masking filter "
            "unparsed ends up unmasked in a report labelled masked.".format(text)
        )

    if addr.version == 4:
        parts = text.split(".")
        sep = "."
        total = 4
    else:
        # exploded, not compressed: '2001:db8::1' has to become eight
        # components before any of them can be replaced, or the mask count
        # depends on how many zero groups the input happened to collapse.
        parts = addr.exploded.split(":")
        sep = ":"
        total = 8

    if keep >= total:
        raise AnsibleFilterError(
            "mask_ip: keep={0} masks nothing for an IPv{1} address "
            "({2} components). That is not masking.".format(
                keep, addr.version, total)
        )

    return sep.join(parts[:keep] + [MASK_TOKEN] * (total - keep))


def mask_mac(value):
    """Mask a MAC address, preserving the OUI.

        mask_mac('00:00:5e:00:53:af') -> '00:00:5e:xx:xx:xx'
        mask_mac('0000.5e00.53af')    -> '0000.5e00.xxxx'

    The vendor prefix is kept: it is not sensitive, and it is frequently the
    reason the report is being read. Raises on non-MAC input.
    """
    if value is None:
        raise AnsibleFilterError("mask_mac: refusing to mask None")

    text = str(value).strip()
    if not _MAC_RE.match(text):
        raise AnsibleFilterError(
            "mask_mac: {0!r} is not a MAC address. Refusing to return it "
            "unchanged.".format(text)
        )

    if "." in text:
        groups = text.split(".")
        return ".".join(groups[:2] + ["xxxx"])

    sep = ":" if ":" in text else "-"
    octets = text.split(sep)
    return sep.join(octets[:3] + [MAC_MASK_TOKEN] * 3)


def mask_hostname(value, keep_labels=1):
    """Mask the domain portion of an FQDN, keeping the leftmost labels.

        mask_hostname('sw-a-01.site.example') -> 'sw-a-01.xxx'

    A bare hostname with no dot is returned unchanged. There is no domain to
    remove, and the short name is what makes the report readable. This is the
    one pass-through in this module, and it is correct because nothing was
    withheld -- not because parsing failed.
    """
    if value is None:
        raise AnsibleFilterError("mask_hostname: refusing to mask None")

    text = str(value).strip()
    if not text:
        raise AnsibleFilterError(
            "mask_hostname: refusing to mask an empty value")

    try:
        keep_labels = int(keep_labels)
    except (TypeError, ValueError):
        raise AnsibleFilterError(
            "mask_hostname: keep_labels must be an integer")
    if keep_labels < 1:
        raise AnsibleFilterError(
            "mask_hostname: keep_labels must be at least 1")

    labels = text.split(".")
    if len(labels) <= keep_labels:
        return text
    return ".".join(labels[:keep_labels] + [MASK_TOKEN])


class FilterModule(object):
    """Expose the masking filters to Ansible."""

    def filters(self):
        return {
            "mask_ip": mask_ip,
            "mask_mac": mask_mac,
            "mask_hostname": mask_hostname,
        }
