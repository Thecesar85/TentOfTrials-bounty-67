#!/usr/bin/env python3
"""Tests for tools/config_generator.py — bounty #1 ($45)."""

import json
import pytest
import sys
from pathlib import Path

# Ensure tools/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from config_generator import (  # noqa: E402
    generate_config,
    merge_config,
    mask_sensitive,
    SENSITIVE_KEYS,
)


# ---------------------------------------------------------------------------
# SENSITIVE_KEYS deduplication
# ---------------------------------------------------------------------------

class TestSensitiveKeysDedup:
    """SENSITIVE_KEYS must contain no duplicates while preserving redaction behaviour."""

    def test_no_duplicates(self):
        assert len(SENSITIVE_KEYS) == len(set(SENSITIVE_KEYS)), (
            f"SENSITIVE_KEYS contains duplicates: {SENSITIVE_KEYS}"
        )

    def test_expected_keys_present(self):
        """All three expected sensitive paths are still covered after dedup."""
        assert "database.password" in SENSITIVE_KEYS
        assert "redis.password" in SENSITIVE_KEYS
        assert "auth.jwt_secret" in SENSITIVE_KEYS


# ---------------------------------------------------------------------------
# generate_config
# ---------------------------------------------------------------------------

class TestGenerateConfig:
    """generate_config() must return correct values for known environments."""

    def test_development_defaults(self):
        cfg = generate_config("development")
        assert cfg["app"]["environment"] == "development"
        assert cfg["app"]["debug"] is True
        assert cfg["database"]["name"] == "tent_dev"
        assert cfg["auth"]["jwt_expiry_minutes"] == 1440

    def test_production_defaults(self):
        cfg = generate_config("production")
        assert cfg["app"]["environment"] == "production"
        assert cfg["app"]["debug"] is False
        assert cfg["database"]["name"] == "tent_production"
        assert cfg["database"]["pool_max"] == 50
        assert cfg["auth"]["mfa_required"] is True
        assert cfg["features"]["margin_trading"] is True

    def test_custom_overrides_applied(self):
        overrides = {"app": {"debug": False}, "database": {"name": "custom_db"}}
        cfg = generate_config("development", overrides=overrides)
        assert cfg["app"]["debug"] is False
        assert cfg["database"]["name"] == "custom_db"
        # Unrelated keys must not be affected
        assert cfg["app"]["environment"] == "development"
        assert cfg["database"]["pool_max"] == 10

    def test_unknown_env_falls_back_to_default(self):
        cfg = generate_config("unknown_env")
        assert cfg["app"]["debug"] is True  # DEFAULT_CONFIG debug=True
        assert cfg["app"]["environment"] == "development"

    def test_overrides_do_not_mutate_default(self):
        import config_generator
        before = config_generator.DEFAULT_CONFIG.copy()
        generate_config("development", overrides={"app": {"debug": False}})
        after = config_generator.DEFAULT_CONFIG
        assert after["app"]["debug"] is True  # unchanged


# ---------------------------------------------------------------------------
# merge_config
# ---------------------------------------------------------------------------

class TestMergeConfig:
    """merge_config() must deep-merge without mutating the base dict."""

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 4}}
        result = merge_config(base, override)
        assert result["a"]["x"] == 1   # preserved
        assert result["a"]["y"] == 99  # overridden
        assert result["a"]["z"] == 4   # added
        assert result["b"] == 3        # preserved

    def test_base_not_mutated(self):
        base = {"a": {"x": 1}}
        original = json.loads(json.dumps(base))  # deep copy
        override = {"a": {"x": 2, "y": 3}}
        merge_config(base, override)
        assert base == original  # base unchanged

    def test_non_dict_override_wins(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": "scalar"}
        result = merge_config(base, override)
        assert result["a"] == "scalar"

    def test_empty_override_is_noop(self):
        base = {"a": 1, "b": {"c": 2}}
        result = merge_config(base, {})
        assert result == base


# ---------------------------------------------------------------------------
# mask_sensitive
# ---------------------------------------------------------------------------

class TestMaskSensitive:
    """mask_sensitive() must redact SENSITIVE_KEYS and leave others visible."""

    def test_database_password_masked(self):
        cfg = generate_config("development")
        masked = mask_sensitive(cfg)
        assert masked["database"]["password"] == "***REDACTED***"

    def test_redis_password_masked(self):
        cfg = generate_config("development")
        masked = mask_sensitive(cfg)
        assert masked["redis"]["password"] == "***REDACTED***"

    def test_jwt_secret_masked(self):
        cfg = generate_config("development")
        masked = mask_sensitive(cfg)
        assert masked["auth"]["jwt_secret"] == "***REDACTED***"

    def test_non_sensitive_values_visible(self):
        cfg = generate_config("development")
        masked = mask_sensitive(cfg)
        assert masked["app"]["name"] == "tent-of-trials"
        assert masked["app"]["version"] == "3.2.0"
        assert masked["database"]["host"] == "localhost"
        assert masked["database"]["port"] == 5432

    def test_non_sensitive_nested_value_visible(self):
        cfg = generate_config("production")
        masked = mask_sensitive(cfg)
        # pool_max is NOT in SENSITIVE_KEYS
        assert masked["database"]["pool_max"] == 50
        assert masked["auth"]["jwt_expiry_minutes"] == 60

    def test_empty_config(self):
        assert mask_sensitive({}) == {}

    def test_masked_does_not_mutate_original(self):
        cfg = generate_config("development")
        original_pwd = cfg["database"]["password"]
        masked = mask_sensitive(cfg)
        assert cfg["database"]["password"] == original_pwd  # original intact
        assert masked["database"]["password"] == "***REDACTED***"


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
