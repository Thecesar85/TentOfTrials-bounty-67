#!/usr/bin/env python3
"""Comprehensive regression test suite for tools/config_generator.py.

Validates:
1. SENSITIVE_KEYS deduplication and canonical entries.
2. generate_config() environment overrides (development, production, staging, custom).
3. merge_config() deep recursive merging without mutating unrelated nested keys.
4. mask_sensitive() redaction of sensitive credentials while preserving non-sensitive fields.
5. Export format serializers (JSON, dotenv, Kubernetes ConfigMap).
"""

import copy
import json
import unittest
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.config_generator import (
    DEFAULT_CONFIG,
    ENV_OVERRIDES,
    SENSITIVE_KEYS,
    generate_config,
    merge_config,
    mask_sensitive,
    to_json,
    to_dotenv,
    to_k8s_configmap,
    flatten_for_k8s,
)


class TestConfigGeneratorValidation(unittest.TestCase):
    """Test suite addressing all acceptance criteria for TentOfTrials Issue #1."""

    def test_sensitive_keys_deduplicated_and_exact(self):
        """Verify SENSITIVE_KEYS has no duplicate entries and preserves required keys."""
        self.assertEqual(
            len(SENSITIVE_KEYS),
            len(set(SENSITIVE_KEYS)),
            "SENSITIVE_KEYS must not contain duplicated entries.",
        )
        expected_keys = ["database.password", "redis.password", "auth.jwt_secret"]
        self.assertEqual(SENSITIVE_KEYS, expected_keys)

    def test_merge_config_recursive_preserves_unrelated_nested_keys(self):
        """Verify recursive merge_config() preserves untouched sibling keys and does not mutate base."""
        base = {
            "app": {
                "name": "TentOfTrials",
                "version": "1.0.0",
                "debug": False,
                "nested": {"level1": "orig1", "level2": "orig2"},
            },
            "server": {"host": "127.0.0.1", "port": 8080},
        }
        base_copy = copy.deepcopy(base)

        override = {
            "app": {
                "debug": True,
                "nested": {"level2": "updated2", "level3": "added3"},
            },
            "server": {"port": 9090},
        }

        merged = merge_config(base, override)

        # Base immutability check
        self.assertEqual(base, base_copy, "merge_config must not mutate the original base dictionary.")

        # Preservation of untouched nested keys
        self.assertEqual(merged["app"]["name"], "TentOfTrials")
        self.assertEqual(merged["app"]["version"], "1.0.0")
        self.assertEqual(merged["app"]["nested"]["level1"], "orig1")
        self.assertEqual(merged["server"]["host"], "127.0.0.1")

        # Application of overrides
        self.assertTrue(merged["app"]["debug"])
        self.assertEqual(merged["app"]["nested"]["level2"], "updated2")
        self.assertEqual(merged["app"]["nested"]["level3"], "added3")
        self.assertEqual(merged["server"]["port"], 9090)

    def test_generate_config_development_overrides(self):
        """Verify generate_config('development') applies expected dev defaults and overrides."""
        config = generate_config("development")

        self.assertEqual(config["app"]["environment"], "development")
        self.assertTrue(config["app"]["debug"])
        self.assertEqual(config["app"]["log_level"], "debug")
        self.assertEqual(config["database"]["name"], "tent_dev")
        self.assertEqual(config["market"]["rate_limit_per_second"], 1000)
        self.assertEqual(config["auth"]["jwt_expiry_minutes"], 1440)

    def test_generate_config_production_overrides(self):
        """Verify generate_config('production') applies expected hardened production defaults."""
        config = generate_config("production")

        self.assertEqual(config["app"]["environment"], "production")
        self.assertFalse(config["app"]["debug"])
        self.assertEqual(config["app"]["log_level"], "info")
        self.assertEqual(config["database"]["name"], "tent_production")
        self.assertEqual(config["database"]["pool_max"], 50)
        self.assertTrue(config["auth"]["mfa_required"])
        self.assertFalse(config["features"]["ai_assistant"])
        self.assertTrue(config["features"]["margin_trading"])

    def test_generate_config_with_custom_overrides(self):
        """Verify generate_config handles additional custom overrides layered on top."""
        custom = {
            "app": {"cluster_id": "eu-central-1"},
            "market": {"custom_symbol": "BTC/USD"},
        }
        config = generate_config("staging", overrides=custom)

        self.assertEqual(config["app"]["environment"], "staging")
        self.assertEqual(config["app"]["cluster_id"], "eu-central-1")
        self.assertEqual(config["market"]["custom_symbol"], "BTC/USD")

    def test_mask_sensitive_redacts_credentials_keeps_non_sensitive(self):
        """Verify mask_sensitive() redacts database, Redis, and JWT secrets while keeping other fields visible."""
        raw_config = {
            "app": {"name": "tent", "environment": "production"},
            "database": {
                "host": "db.internal",
                "port": 5432,
                "password": "super-secret-db-pass",
            },
            "redis": {
                "host": "cache.internal",
                "password": "super-secret-redis-token",
            },
            "auth": {
                "jwt_secret": "my-ultra-secure-jwt-signing-key",
                "jwt_expiry_minutes": 60,
            },
        }

        masked = mask_sensitive(raw_config)

        # Redacted values
        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")

        # Non-sensitive values preserved
        self.assertEqual(masked["app"]["name"], "tent")
        self.assertEqual(masked["app"]["environment"], "production")
        self.assertEqual(masked["database"]["host"], "db.internal")
        self.assertEqual(masked["database"]["port"], 5432)
        self.assertEqual(masked["redis"]["host"], "cache.internal")
        self.assertEqual(masked["auth"]["jwt_expiry_minutes"], 60)

    def test_to_json_serialization(self):
        """Verify JSON export creates parseable JSON matching original keys."""
        config = generate_config("development")
        json_str = to_json(config, pretty=True)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["app"]["environment"], "development")
        self.assertTrue(parsed["app"]["debug"])

    def test_to_dotenv_serialization(self):
        """Verify .env export correctly flattens and formats uppercase keys."""
        sample = {
            "app": {"name": "tent", "debug": True},
            "server": {"port": 8080},
        }
        dotenv_str = to_dotenv(sample)
        self.assertIn("APP_NAME=tent", dotenv_str)
        self.assertIn("APP_DEBUG=true", dotenv_str)
        self.assertIn("SERVER_PORT=8080", dotenv_str)

    def test_flatten_and_k8s_configmap(self):
        """Verify flattening and Kubernetes ConfigMap manifest formatting."""
        sample = {
            "app": {"name": "tent-service"},
            "server": {"port": 8080},
        }
        flat = flatten_for_k8s(sample)
        self.assertIn(("app.name", "tent-service"), flat)
        self.assertIn(("server.port", 8080), flat)

        k8s_yaml = to_k8s_configmap(sample, name="tent-config")
        self.assertIn("kind: ConfigMap", k8s_yaml)
        self.assertIn("name: tent-config", k8s_yaml)
        self.assertIn('app.name: "tent-service"', k8s_yaml)


if __name__ == "__main__":
    unittest.main()
