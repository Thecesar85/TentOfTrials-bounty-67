import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import config_generator


class ConfigGeneratorTests(unittest.TestCase):
    def test_generate_config_applies_environment_overrides(self):
        config = config_generator.generate_config("production")

        self.assertEqual(config["app"]["environment"], "production")
        self.assertFalse(config["app"]["debug"])
        self.assertEqual(config["database"]["name"], "tent_production")
        self.assertEqual(config["database"]["pool_min"], 10)
        self.assertTrue(config["auth"]["mfa_required"])

    def test_generate_config_merges_custom_overrides(self):
        config = config_generator.generate_config(
            "staging",
            {
                "server": {"port": 9090},
                "features": {"ai_assistant": True},
            },
        )

        self.assertEqual(config["app"]["environment"], "staging")
        self.assertEqual(config["server"]["port"], 9090)
        self.assertTrue(config["features"]["ai_assistant"])
        self.assertTrue(config["features"]["web_socket"])

    def test_sensitive_keys_are_unique(self):
        self.assertEqual(
            len(config_generator.SENSITIVE_KEYS),
            len(set(config_generator.SENSITIVE_KEYS)),
        )

    def test_mask_sensitive_redacts_nested_secret_values(self):
        config = config_generator.generate_config(
            "development",
            {
                "database": {"password": "db-password"},
                "redis": {"password": "redis-password"},
                "auth": {"jwt_secret": "jwt-secret"},
            },
        )

        masked = config_generator.mask_sensitive(config)

        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")
        self.assertEqual(masked["database"]["name"], "tent_dev")

    def test_dotenv_output_formats_lists_and_booleans(self):
        config = {
            "app": {"debug": False},
            "kafka": {"brokers": ["broker-a:9092", "broker-b:9092"]},
        }

        output = config_generator.to_dotenv(config)

        self.assertIn("APP_DEBUG=false", output)
        self.assertIn("KAFKA_BROKERS=broker-a:9092,broker-b:9092", output)

    @unittest.skipUnless(config_generator.HAS_YAML, "PyYAML is not installed")
    def test_yaml_output_preserves_environment_override(self):
        output = config_generator.to_yaml(config_generator.generate_config("staging"))

        self.assertIn("environment: staging", output)
        self.assertIn("name: tent_staging", output)


if __name__ == "__main__":
    unittest.main()
