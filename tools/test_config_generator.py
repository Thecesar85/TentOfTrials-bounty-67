#!/usr/bin/env python3
"""
Tests for config_generator.py
Run with: python3 tools/test_config_generator.py
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config_generator as cg


class TestMergeConfig(unittest.TestCase):
    """Test recursive merge_config() behavior."""

    def test_merge_overwrites_top_level(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = cg.merge_config(base, override)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 4})

    def test_merge_nested_dict_recursive(self):
        base = {"app": {"name": "test", "version": "1.0"}, "other": "val"}
        override = {"app": {"version": "2.0"}}
        result = cg.merge_config(base, override)
        self.assertEqual(result["app"]["name"], "test")  # unrelated nested key preserved
        self.assertEqual(result["app"]["version"], "2.0")
        self.assertEqual(result["other"], "val")

    def test_merge_does_not_mutate_base(self):
        base = {"app": {"name": "test"}}
        override = {"app": {"version": "2.0"}}
        original_base = dict(base)
        cg.merge_config(base, override)
        self.assertEqual(base, original_base)

    def test_merge_replaces_non_dict_with_dict(self):
        base = {"key": "string"}
        override = {"key": {"nested": "value"}}
        result = cg.merge_config(base, override)
        self.assertEqual(result["key"], {"nested": "value"})


class TestGenerateConfig(unittest.TestCase):
    """Test generate_config() for env overrides."""

    def test_development_override(self):
        config = cg.generate_config("development")
        self.assertEqual(config["app"]["environment"], "development")
        self.assertTrue(config["app"]["debug"])
        self.assertEqual(config["database"]["name"], "tent_dev")

    def test_production_override(self):
        config = cg.generate_config("production")
        self.assertEqual(config["app"]["environment"], "production")
        self.assertFalse(config["app"]["debug"])
        self.assertEqual(config["database"]["name"], "tent_production")
        self.assertEqual(config["database"]["pool_max"], 50)

    def test_staging_override(self):
        config = cg.generate_config("staging")
        self.assertEqual(config["app"]["environment"], "staging")
        self.assertEqual(config["database"]["name"], "tent_staging")
        self.assertEqual(config["auth"]["jwt_expiry_minutes"], 60)

    def test_custom_overrides_applied(self):
        config = cg.generate_config("development", overrides={"app": {"debug": False}})
        self.assertFalse(config["app"]["debug"])

    def test_production_mfa_required(self):
        config = cg.generate_config("production")
        self.assertTrue(config["auth"]["mfa_required"])

    def test_production_features(self):
        config = cg.generate_config("production")
        self.assertFalse(config["features"]["ai_assistant"])
        self.assertTrue(config["features"]["margin_trading"])


class TestMaskSensitive(unittest.TestCase):
    """Test mask_sensitive() redaction behavior."""

    def test_database_password_masked(self):
        config = {"database": {"password": "secret123"}}
        masked = cg.mask_sensitive(config)
        self.assertEqual(masked["database"]["password"], "***REDACTED***")

    def test_redis_password_masked(self):
        config = {"redis": {"password": "redis_secret"}}
        masked = cg.mask_sensitive(config)
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")

    def test_jwt_secret_masked(self):
        config = {"auth": {"jwt_secret": "jwt_super_secret"}}
        masked = cg.mask_sensitive(config)
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")

    def test_non_sensitive_values_remain_visible(self):
        config = {
            "app": {"name": "test-app", "version": "1.0"},
            "database": {"host": "localhost", "password": "secret"}
        }
        masked = cg.mask_sensitive(config)
        self.assertEqual(masked["app"]["name"], "test-app")
        self.assertEqual(masked["app"]["version"], "1.0")
        self.assertEqual(masked["database"]["host"], "localhost")
        self.assertEqual(masked["database"]["password"], "***REDACTED***")

    def test_nested_non_sensitive_preserved(self):
        config = {"database": {"host": "db.example.com", "port": 5432, "password": "dbpass"}}
        masked = cg.mask_sensitive(config)
        self.assertEqual(masked["database"]["host"], "db.example.com")
        self.assertEqual(masked["database"]["port"], 5432)
        self.assertEqual(masked["database"]["password"], "***REDACTED***")

    def test_top_level_sensitive_masked(self):
        config = {"database.password": "top_level_secret"}
        masked = cg.mask_sensitive(config)
        self.assertEqual(masked["database.password"], "***REDACTED***")


if __name__ == "__main__":
    unittest.main()
