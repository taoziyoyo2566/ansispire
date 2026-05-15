import unittest
import sys
import os

# Add filter_plugins to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "filter_plugins"))
import custom_filters

class TestFilters(unittest.TestCase):
    def test_to_nginx_size(self):
        self.assertEqual(custom_filters.to_nginx_size(1073741824), "1g")
        self.assertEqual(custom_filters.to_nginx_size(2147483648), "2g")
        self.assertEqual(custom_filters.to_nginx_size(1048576), "1m")
        self.assertEqual(custom_filters.to_nginx_size(10485760), "10m")
        self.assertEqual(custom_filters.to_nginx_size(1024), "1k")
        self.assertEqual(custom_filters.to_nginx_size(10240), "10k")
        self.assertEqual(custom_filters.to_nginx_size(500), "500")

    def test_cidr_to_nginx_allow(self):
        self.assertEqual(custom_filters.cidr_to_nginx_allow(["10.0.0.0/8"]), ["allow 10.0.0.0/8;"])
        self.assertEqual(custom_filters.cidr_to_nginx_allow(["1.1.1.1", "2.2.2.2"]), ["allow 1.1.1.1;", "allow 2.2.2.2;"])

    def test_mask_secret(self):
        self.assertEqual(custom_filters.mask_secret("password"), "pass****")
        self.assertEqual(custom_filters.mask_secret("secret", 2), "se****")
        self.assertEqual(custom_filters.mask_secret("abc"), "***")

    def test_env_badge(self):
        self.assertEqual(custom_filters.env_badge("production"), "[PROD]")
        self.assertEqual(custom_filters.env_badge("staging"), "[STAGING]")
        self.assertEqual(custom_filters.env_badge("development"), "[DEV]")
        self.assertEqual(custom_filters.env_badge("testing"), "[TEST]")
        self.assertEqual(custom_filters.env_badge("prod"), "[PROD]")
        self.assertEqual(custom_filters.env_badge("unknown"), "[UNKNOWN]")
        
        self.assertEqual(custom_filters.env_badge("production", style="emoji"), "🔴")
        self.assertEqual(custom_filters.env_badge("staging", style="emoji"), "🟡")
        self.assertEqual(custom_filters.env_badge("development", style="emoji"), "🟢")
        self.assertEqual(custom_filters.env_badge("testing", style="emoji"), "🔵")
        self.assertEqual(custom_filters.env_badge("unknown", style="emoji"), "⚪")
        
        self.assertEqual(custom_filters.env_badge("production", style="raw"), "PROD")

    def test_parse_version(self):
        self.assertEqual(custom_filters.parse_version("v1.2.3"), [1, 2, 3])
        self.assertEqual(custom_filters.parse_version("1.2.3-alpha"), [1, 2, 3, "alpha"])
        self.assertEqual(custom_filters.parse_version("2.0"), [2, 0])

    def test_to_systemd_bool(self):
        self.assertEqual(custom_filters.to_systemd_bool(True), "yes")
        self.assertEqual(custom_filters.to_systemd_bool(False), "no")
        self.assertEqual(custom_filters.to_systemd_bool("true"), "yes")
        self.assertEqual(custom_filters.to_systemd_bool("1"), "yes")
        self.assertEqual(custom_filters.to_systemd_bool("on"), "yes")
        self.assertEqual(custom_filters.to_systemd_bool("0"), "no")

    def test_ljust_rjust(self):
        self.assertEqual(custom_filters.ljust("hi", 5), "hi   ")
        self.assertEqual(custom_filters.rjust("hi", 5), "   hi")

    def test_filter_module(self):
        fm = custom_filters.FilterModule()
        self.assertIn("to_nginx_size", fm.filters())

if __name__ == "__main__":
    unittest.main()
