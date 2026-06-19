import copy
import unittest

from tools import config_generator


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

    def test_merge_config_preserves_unrelated_nested_keys(self):
        base = {
            "database": {"host": "localhost", "port": 5432, "pool": {"min": 2, "max": 10}},
            "auth": {"jwt_expiry_minutes": 60},
        }
        original = copy.deepcopy(base)

        merged = config_generator.merge_config(base, {"database": {"pool": {"max": 20}}})

        self.assertEqual(merged["database"]["host"], "localhost")
        self.assertEqual(merged["database"]["port"], 5432)
        self.assertEqual(merged["database"]["pool"]["min"], 2)
        self.assertEqual(merged["database"]["pool"]["max"], 20)
        self.assertEqual(merged["auth"]["jwt_expiry_minutes"], 60)
        self.assertEqual(base, original)

    def test_mask_sensitive_redacts_database_redis_and_jwt_secret(self):
        config = config_generator.generate_config(
            "production",
            {
                "database": {"password": "database-secret"},
                "redis": {"password": "redis-secret"},
                "auth": {"jwt_secret": "jwt-secret"},
            },
        )

        masked = config_generator.mask_sensitive(config)

        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")
        self.assertEqual(masked["database"]["name"], "tent_production")
        self.assertEqual(masked["redis"]["host"], "localhost")
        self.assertEqual(masked["auth"]["jwt_expiry_minutes"], 60)

    def test_sensitive_keys_are_deduplicated(self):
        self.assertEqual(
            len(config_generator.SENSITIVE_KEYS),
            len(set(config_generator.SENSITIVE_KEYS)),
        )


if __name__ == "__main__":
    unittest.main()
