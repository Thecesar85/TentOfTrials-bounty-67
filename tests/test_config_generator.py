import copy
import unittest

from tools.config_generator import (
    DEFAULT_CONFIG,
    SENSITIVE_KEYS,
    generate_config,
    mask_sensitive,
    merge_config,
)


class ConfigGeneratorTests(unittest.TestCase):
    def test_generate_config_applies_development_overrides(self):
        config = generate_config("development")

        self.assertEqual(config["app"]["environment"], "development")
        self.assertTrue(config["app"]["debug"])
        self.assertEqual(config["app"]["log_level"], "debug")
        self.assertEqual(config["database"]["name"], "tent_dev")
        self.assertEqual(config["market"]["rate_limit_per_second"], 1000)
        self.assertEqual(config["auth"]["jwt_expiry_minutes"], 1440)

    def test_generate_config_applies_production_overrides(self):
        config = generate_config("production")

        self.assertEqual(config["app"]["environment"], "production")
        self.assertFalse(config["app"]["debug"])
        self.assertEqual(config["database"]["name"], "tent_production")
        self.assertEqual(config["database"]["pool_min"], 10)
        self.assertEqual(config["database"]["pool_max"], 50)
        self.assertEqual(config["market"]["rate_limit_per_second"], 10)
        self.assertTrue(config["auth"]["mfa_required"])
        self.assertTrue(config["features"]["margin_trading"])

    def test_merge_config_preserves_unrelated_nested_keys(self):
        base = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "pool": {"min": 2, "max": 10},
            },
            "features": {"dark_mode": True},
        }
        original = copy.deepcopy(base)
        override = {"database": {"pool": {"max": 25}}}

        merged = merge_config(base, override)

        self.assertEqual(merged["database"]["host"], "localhost")
        self.assertEqual(merged["database"]["port"], 5432)
        self.assertEqual(merged["database"]["pool"]["min"], 2)
        self.assertEqual(merged["database"]["pool"]["max"], 25)
        self.assertEqual(merged["features"]["dark_mode"], True)
        self.assertEqual(base, original)

    def test_mask_sensitive_redacts_secrets_and_preserves_public_values(self):
        config = generate_config(
            "production",
            {
                "database": {"password": "db-secret"},
                "redis": {"password": "redis-secret"},
                "auth": {"jwt_secret": "jwt-secret"},
            },
        )

        masked = mask_sensitive(config)

        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")
        self.assertEqual(masked["database"]["host"], DEFAULT_CONFIG["database"]["host"])
        self.assertEqual(masked["auth"]["jwt_expiry_minutes"], 60)
        self.assertEqual(masked["app"]["name"], "tent-of-trials")

    def test_sensitive_keys_are_deduplicated(self):
        self.assertEqual(SENSITIVE_KEYS, list(dict.fromkeys(SENSITIVE_KEYS)))


if __name__ == "__main__":
    unittest.main()
