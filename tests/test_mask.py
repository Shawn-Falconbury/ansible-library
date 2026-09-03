"""Unit tests for filter_plugins/network_mask.py.

Runnable without Ansible installed:

    python3 -m unittest discover -s tests -p 'test_*.py'

That independence is deliberate. The masking logic is the highest-risk code
in this repository -- a silent failure here emails live addresses to a list --
and testing it should not depend on a working Ansible install, a control node,
or a device.

The bulk of these tests assert on FAILURE. A masking filter that returns its
input unchanged when it cannot parse it is the specific bug being defended
against, so most of what follows checks that the filter raises rather than
that it returns something pretty.
"""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "filter_plugins"),
)

from network_mask import (  # noqa: E402
    AnsibleFilterError,
    mask_hostname,
    mask_ip,
    mask_mac,
)


class TestMaskIp(unittest.TestCase):
    def test_ipv4_default_keeps_two_octets(self):
        self.assertEqual(mask_ip("192.0.2.10"), "192.0.xxx.xxx")

    def test_ipv4_keep_one(self):
        self.assertEqual(mask_ip("192.0.2.10", keep=1), "192.xxx.xxx.xxx")

    def test_ipv4_keep_zero_masks_everything(self):
        self.assertEqual(mask_ip("192.0.2.10", keep=0), "xxx.xxx.xxx.xxx")

    def test_ipv4_keep_as_string_is_coerced(self):
        # Jinja hands filter arguments through as strings often enough that
        # this needs to work rather than raise.
        self.assertEqual(mask_ip("192.0.2.10", keep="1"), "192.xxx.xxx.xxx")

    def test_ipv6_is_exploded_before_masking(self):
        # The compressed form has three components; the exploded form has
        # eight. Masking the compressed form would mask a different amount of
        # the address depending on how many zero groups the input collapsed.
        self.assertEqual(
            mask_ip("2001:db8::1", keep=2),
            "2001:0db8:xxx:xxx:xxx:xxx:xxx:xxx",
        )

    def test_ipv6_full_form_matches_compressed_form(self):
        self.assertEqual(
            mask_ip("2001:db8::1", keep=2),
            mask_ip("2001:0db8:0000:0000:0000:0000:0000:0001", keep=2),
        )

    # ---- failure paths: the reason this module exists ------------------

    def test_ios_image_filename_raises(self):
        # The classic false positive. A naive dotted-quad matcher treats
        # '17.06.06' as an address; a masking filter that accepted this and
        # returned it unchanged would look like it had done its job.
        with self.assertRaises(AnsibleFilterError):
            mask_ip("cat9k_iosxe.17.06.06.SPA.bin")

    def test_bare_version_string_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip("15.2.7.E7")

    def test_hostname_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip("sw-a-01.lab.example")

    def test_none_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip(None)

    def test_empty_string_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip("   ")

    def test_keep_equal_to_component_count_raises(self):
        # keep=4 on IPv4 would return the address verbatim. Silently doing
        # nothing while being called a masking filter is the failure mode.
        with self.assertRaises(AnsibleFilterError):
            mask_ip("192.0.2.10", keep=4)

    def test_keep_greater_than_component_count_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip("192.0.2.10", keep=9)

    def test_negative_keep_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip("192.0.2.10", keep=-1)

    def test_non_integer_keep_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_ip("192.0.2.10", keep="two")

    def test_output_never_contains_the_masked_octets(self):
        # Belt and braces: assert on absence, not just on the expected string.
        # If the mask token or join logic changes, this still catches a leak.
        result = mask_ip("198.51.100.237", keep=2)
        self.assertNotIn("100", result)
        self.assertNotIn("237", result)


class TestMaskMac(unittest.TestCase):
    def test_colon_form_keeps_oui(self):
        self.assertEqual(mask_mac("00:00:5e:00:53:af"), "00:00:5e:xx:xx:xx")

    def test_hyphen_form_preserved(self):
        self.assertEqual(mask_mac("00-00-5e-00-53-af"), "00-00-5e-xx-xx-xx")

    def test_cisco_dotted_triplet(self):
        self.assertEqual(mask_mac("0000.5e00.53af"), "0000.5e00.xxxx")

    def test_uppercase_accepted(self):
        self.assertEqual(mask_mac("00:00:5E:00:53:AF"), "00:00:5E:xx:xx:xx")

    def test_output_never_contains_the_host_octets(self):
        result = mask_mac("00:00:5e:00:53:af")
        # Only '53' and 'af' are asserted absent. The third host octet is
        # '00', which also appears in the OUI that masking deliberately
        # keeps -- asserting its absence would fail against correct
        # output. A consequence of using the RFC 7042 documentation
        # range, and worth stating rather than leaving as a silent gap.
        for octet in ("53", "af"):
            self.assertNotIn(octet, result)

    def test_ip_address_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_mac("192.0.2.10")

    def test_truncated_mac_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_mac("00:00:5e:00:53")

    def test_none_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_mac(None)

    def test_arbitrary_text_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_mac("not a mac")


class TestMaskHostname(unittest.TestCase):
    def test_fqdn_domain_is_masked(self):
        self.assertEqual(
            mask_hostname("sw-a-01.site.example"), "sw-a-01.xxx")

    def test_keep_two_labels(self):
        self.assertEqual(
            mask_hostname("sw-a-01.site.example", keep_labels=2),
            "sw-a-01.site.xxx",
        )

    def test_bare_hostname_returned_unchanged(self):
        # The one legitimate pass-through: there is no domain to remove.
        self.assertEqual(mask_hostname("sw-a-01"), "sw-a-01")

    def test_labels_equal_to_keep_returned_unchanged(self):
        self.assertEqual(
            mask_hostname("sw-a-01.site", keep_labels=2), "sw-a-01.site")

    def test_output_never_contains_the_domain(self):
        result = mask_hostname("sw-a-01.internal.corp.example")
        self.assertNotIn("internal", result)
        self.assertNotIn("corp", result)

    def test_none_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_hostname(None)

    def test_empty_raises(self):
        with self.assertRaises(AnsibleFilterError):
            mask_hostname("")

    def test_zero_keep_labels_raises(self):
        # keep_labels=0 would leave only the mask token, discarding the one
        # piece of information the report needs. Almost certainly a mistake.
        with self.assertRaises(AnsibleFilterError):
            mask_hostname("sw-a-01.site.example", keep_labels=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
