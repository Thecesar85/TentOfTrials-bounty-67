#!/usr/bin/env python3
"""Tests for tools/config_generator.py."""

import unittest
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "config_generator",
    os.path.join(_HERE, "config_generator.py"),
)
_config_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_gen)

DEFAULT_CONFIG = _config_gen.DEFAULT_CONFIG
ENV_OVERRIDES = _config_gen.ENV_OVERRIDES
SENSITIVE_KEYS = _config_gen.SENSITIVE_KEYS
merge_config = _config_gen.merge_config
generate_config = _config_gen.generate_config
mask_sensitive = _config_gen.mask_sensitive


class TestSensitiveKeys(unittest.TestCase):
    def test_no_duplicates(self):
        self.assertEqual(len(SENSITIVE_KEYS), len(set(SENSITIVE_KEYS)))


class TestMergeConfig(unittest.TestCase):
    def test_merge_top_level(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_config(base, override)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 4})

    def test_merge_nested(self):
        base = {"db": {"host": "localhost", "port": 5432}, "app": {"debug": True}}
        override = {"db": {"port": 9999, "user": "admin"}}
        result = merge_config(base, override)
        self.assertEqual(result, {"db": {"host": "localhost", "port": 9999, "user": "admin"}, "app": {"debug": True}})

    def test_merge_does_not_mutate_unrelated_keys(self):
        base = {"x": {"y": 1, "z": 2}, "other": "keep"}
        override = {"x": {"y": 99}}
        result = merge_config(base, override)
        self.assertEqual(result, {"x": {"y": 99, "z": 2}, "other": "keep"})

    def test_merge_non_dict_overwrite(self):
        base = {"key": {"nested": "dict"}}
        override = {"key": "string"}
        result = merge_config(base, override)
        self.assertEqual(result, {"key": "string"})

    def test_merge_empty_overrides(self):
        base = {"a": 1, "b": {"c": 2}}
        result = merge_config(base, {})
        self.assertEqual(result, {"a": 1, "b": {"c": 2}})

    def test_merge_original_unchanged(self):
        base = {"nested": {"val": 1}}
        override = {"nested": {"val": 2, "extra": 3}}
        merge_config(base, override)
        self.assertEqual(base, {"nested": {"val": 1}})


class TestGenerateConfig(unittest.TestCase):
    def test_development_defaults(self):
        config = generate_config("development")
        self.assertEqual(config["app"]["environment"], "development")
        self.assertEqual(config["app"]["debug"], True)
        self.assertEqual(config["app"]["log_level"], "debug")
        self.assertEqual(config["database"]["name"], "tent_dev")

    def test_production_overrides(self):
        config = generate_config("production")
        self.assertEqual(config["app"]["environment"], "production")
        self.assertEqual(config["app"]["debug"], False)
        self.assertEqual(config["app"]["log_level"], "info")
        self.assertEqual(config["database"]["name"], "tent_production")
        self.assertEqual(config["database"]["pool_max"], 50)
        self.assertEqual(config["database"]["pool_min"], 10)
        self.assertTrue(config["auth"]["mfa_required"])

    def test_staging_overrides(self):
        config = generate_config("staging")
        self.assertEqual(config["app"]["environment"], "staging")
        self.assertEqual(config["app"]["debug"], True)
        self.assertEqual(config["app"]["log_level"], "info")
        self.assertEqual(config["database"]["name"], "tent_staging")

    def test_custom_overrides_merge(self):
        custom = {"server": {"port": 3000}, "app": {"debug": False}}
        config = generate_config("development", overrides=custom)
        self.assertEqual(config["server"]["port"], 3000)
        self.assertEqual(config["app"]["debug"], False)

    def test_custom_overrides_do_not_break_defaults(self):
        custom = {"features": {"dark_mode": False}}
        config = generate_config("production", overrides=custom)
        self.assertEqual(config["features"]["dark_mode"], False)
        self.assertEqual(config["app"]["environment"], "production")

    def test_unknown_env_uses_defaults(self):
        config = generate_config("unknown")
        self.assertEqual(config["app"]["environment"], "development")

    def test_all_envs_have_required_sections(self):
        for env in ENV_OVERRIDES:
            config = generate_config(env)
            for section in ("app", "server", "database", "redis", "auth"):
                self.assertIn(section, config, msg=f"Missing section {section!r} for env {env!r}")


class TestMaskSensitive(unittest.TestCase):
    def test_mask_database_password(self):
        config = {"database": {"password": "supersecret", "host": "localhost"}}
        masked = mask_sensitive(config)
        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["database"]["host"], "localhost")

    def test_mask_redis_password(self):
        config = {"redis": {"password": "redispass", "port": 6379}}
        masked = mask_sensitive(config)
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")

    def test_mask_jwt_secret(self):
        config = {"auth": {"jwt_secret": "my-jwt-token", "jwt_expiry_minutes": 60}}
        masked = mask_sensitive(config)
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_expiry_minutes"], 60)

    def test_non_sensitive_values_remain(self):
        config = {"app": {"name": "tent-of-trials", "debug": True}, "server": {"port": 8080, "host": "0.0.0.0"}}
        masked = mask_sensitive(config)
        self.assertEqual(masked, config)

    def test_mask_deep_nested(self):
        config = {"outer": {"inner": {"database": {"password": "deepsecret"}}}}
        masked = mask_sensitive(config)
        self.assertEqual(masked["outer"]["inner"]["database"]["password"], "deepsecret")

    def test_empty_config(self):
        self.assertEqual(mask_sensitive({}), {})

    def test_all_sensitive_keys_are_masked(self):
        config = generate_config("development")
        config["database"]["password"] = "db_pass"
        config["redis"]["password"] = "redis_pass"
        config["auth"]["jwt_secret"] = "jwt_secret"
        masked = mask_sensitive(config)
        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")


if __name__ == "__main__":
    unittest.main()
