import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import config_generator


class ConfigGeneratorTests(unittest.TestCase):
    def test_generate_config_applies_development_overrides(self):
        config = config_generator.generate_config("development")

        self.assertEqual(config["app"]["environment"], "development")
        self.assertTrue(config["app"]["debug"])
        self.assertEqual(config["app"]["log_level"], "debug")
        self.assertEqual(config["database"]["name"], "tent_dev")
        self.assertEqual(config["market"]["rate_limit_per_second"], 1000)
        self.assertEqual(config["auth"]["jwt_expiry_minutes"], 1440)

    def test_generate_config_applies_production_overrides(self):
        config = config_generator.generate_config("production")

        self.assertEqual(config["app"]["environment"], "production")
        self.assertFalse(config["app"]["debug"])
        self.assertEqual(config["database"]["name"], "tent_production")
        self.assertEqual(config["database"]["pool_min"], 10)
        self.assertEqual(config["database"]["pool_max"], 50)
        self.assertTrue(config["auth"]["mfa_required"])
        self.assertTrue(config["features"]["margin_trading"])

    def test_merge_config_recurses_without_mutating_unrelated_nested_keys(self):
        base = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "pool": {"min": 2, "max": 10},
            },
            "server": {"host": "0.0.0.0", "port": 8080},
        }
        original = copy.deepcopy(base)
        override = {"database": {"pool": {"max": 30}}}

        merged = config_generator.merge_config(base, override)

        self.assertEqual(base, original)
        self.assertEqual(merged["database"]["host"], "localhost")
        self.assertEqual(merged["database"]["port"], 5432)
        self.assertEqual(merged["database"]["pool"]["min"], 2)
        self.assertEqual(merged["database"]["pool"]["max"], 30)
        self.assertEqual(merged["server"], original["server"])

    def test_mask_sensitive_redacts_database_redis_and_jwt_only(self):
        config = {
            "database": {
                "host": "db.internal",
                "password": "db-secret",
            },
            "redis": {
                "host": "redis.internal",
                "password": "redis-secret",
            },
            "auth": {
                "jwt_secret": "jwt-secret",
                "jwt_expiry_minutes": 60,
            },
            "app": {
                "name": "tent-of-trials",
                "debug": False,
            },
        }

        masked = config_generator.mask_sensitive(config)

        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")
        self.assertEqual(masked["database"]["host"], "db.internal")
        self.assertEqual(masked["redis"]["host"], "redis.internal")
        self.assertEqual(masked["auth"]["jwt_expiry_minutes"], 60)
        self.assertEqual(masked["app"]["name"], "tent-of-trials")

    def test_sensitive_keys_are_unique(self):
        self.assertEqual(
            sorted(config_generator.SENSITIVE_KEYS),
            sorted(set(config_generator.SENSITIVE_KEYS)),
        )


if __name__ == "__main__":
    unittest.main()
