#!/usr/bin/env python3
"""
Unit and validation test suite for tools/config_generator.py.
Covers generate_config, recursive merge_config, sensitive key masking, and format conversions.
"""

import unittest
import os
import sys
import json

# Ensure tools directory is on sys.path
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)

from config_generator import (
    DEFAULT_CONFIG,
    ENV_OVERRIDES,
    SENSITIVE_KEYS,
    merge_config,
    generate_config,
    mask_sensitive,
    to_json,
    to_dotenv,
    to_k8s_configmap,
)


class TestConfigGenerator(unittest.TestCase):

    def test_sensitive_keys_deduplication(self):
        """Verify SENSITIVE_KEYS contains unique entries and no duplicates."""
        self.assertEqual(len(SENSITIVE_KEYS), len(set(SENSITIVE_KEYS)), "SENSITIVE_KEYS must not contain duplicates")
        self.assertIn("database.password", SENSITIVE_KEYS)
        self.assertIn("redis.password", SENSITIVE_KEYS)
        self.assertIn("auth.jwt_secret", SENSITIVE_KEYS)

    def test_merge_config_recursive_and_isolated(self):
        """Test recursive merge preserves unmodified sibling keys without mutating base dict."""
        base = {
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "timeout": 30,
            },
            "database": {
                "host": "localhost",
                "name": "tent_dev",
            },
            "debug": True,
        }
        override = {
            "server": {
                "port": 9000,
            },
            "database": {
                "name": "tent_prod",
            },
            "new_key": "val",
        }

        merged = merge_config(base, override)

        # Overridden keys
        self.assertEqual(merged["server"]["port"], 9000)
        self.assertEqual(merged["database"]["name"], "tent_prod")
        self.assertEqual(merged["new_key"], "val")

        # Preserved sibling keys
        self.assertEqual(merged["server"]["host"], "0.0.0.0")
        self.assertEqual(merged["server"]["timeout"], 30)
        self.assertEqual(merged["database"]["host"], "localhost")
        self.assertEqual(merged["debug"], True)

        # Base dictionary isolation (immutability)
        self.assertEqual(base["server"]["port"], 8080)
        self.assertNotIn("new_key", base)

    def test_generate_config_development_environment(self):
        """Verify generate_config for development environment applying correct defaults and overrides."""
        dev_config = generate_config("development")

        self.assertEqual(dev_config["app"]["environment"], "development")
        self.assertTrue(dev_config["app"]["debug"])
        self.assertEqual(dev_config["app"]["log_level"], "debug")
        self.assertEqual(dev_config["database"]["name"], "tent_dev")
        self.assertEqual(dev_config["market"]["rate_limit_per_second"], 1000)
        self.assertEqual(dev_config["auth"]["jwt_expiry_minutes"], 1440)
        # Default keys preserved
        self.assertEqual(dev_config["server"]["port"], 8080)
        self.assertEqual(dev_config["features"]["web_socket"], True)

    def test_generate_config_production_environment(self):
        """Verify generate_config for production environment applying strict production overrides."""
        prod_config = generate_config("production")

        self.assertEqual(prod_config["app"]["environment"], "production")
        self.assertFalse(prod_config["app"]["debug"])
        self.assertEqual(prod_config["app"]["log_level"], "info")
        self.assertEqual(prod_config["database"]["name"], "tent_production")
        self.assertEqual(prod_config["database"]["pool_max"], 50)
        self.assertEqual(prod_config["database"]["pool_min"], 10)
        self.assertEqual(prod_config["auth"]["mfa_required"], True)
        self.assertEqual(prod_config["features"]["margin_trading"], True)
        self.assertEqual(prod_config["monitoring"]["tracing_sample_rate"], 0.01)

    def test_generate_config_with_custom_overrides(self):
        """Verify custom ad-hoc overrides passed to generate_config."""
        custom_overrides = {
            "server": {"port": 4444},
            "custom_section": {"enabled": True},
        }
        config = generate_config("production", overrides=custom_overrides)

        self.assertEqual(config["server"]["port"], 4444)
        self.assertEqual(config["custom_section"]["enabled"], True)
        self.assertEqual(config["app"]["environment"], "production")

    def test_mask_sensitive_redaction(self):
        """Verify sensitive keys are redacted while non-sensitive fields remain visible."""
        raw_config = {
            "database": {
                "host": "postgres.internal",
                "port": 5432,
                "user": "tent_admin",
                "password": "SuperSecretPassword123!",
            },
            "redis": {
                "host": "redis.internal",
                "password": "RedisSecretKey987!",
            },
            "auth": {
                "jwt_secret": "my-super-secret-jwt-token-key",
                "jwt_expiry_minutes": 60,
            },
            "app": {
                "name": "tent-of-trials",
                "debug": False,
            },
        }

        masked = mask_sensitive(raw_config)

        # Sensitive keys must be redacted
        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")

        # Non-sensitive keys must remain unmodified
        self.assertEqual(masked["database"]["host"], "postgres.internal")
        self.assertEqual(masked["database"]["port"], 5432)
        self.assertEqual(masked["database"]["user"], "tent_admin")
        self.assertEqual(masked["redis"]["host"], "redis.internal")
        self.assertEqual(masked["auth"]["jwt_expiry_minutes"], 60)
        self.assertEqual(masked["app"]["name"], "tent-of-trials")
        self.assertEqual(masked["app"]["debug"], False)

    def test_serializers_output(self):
        """Test to_json, to_dotenv, and to_k8s_configmap serialization formats."""
        cfg = generate_config("development")
        masked = mask_sensitive(cfg)

        json_out = to_json(masked)
        self.assertIn('"name": "tent-of-trials"', json_out)
        self.assertIn('"password": "***REDACTED***"', json_out)

        dotenv_out = to_dotenv(masked)
        self.assertIn("APP_NAME=tent-of-trials", dotenv_out)
        self.assertIn("DATABASE_PASSWORD=***REDACTED***", dotenv_out)

        k8s_out = to_k8s_configmap(masked, name="tent-config")
        self.assertIn("name: tent-config", k8s_out)
        self.assertIn("app.name: \"tent-of-trials\"", k8s_out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
