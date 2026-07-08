#!/usr/bin/env python3
"""Test config_generator.py — environment config generation, merge, and sensitive masking."""

import json
import os
import sys
from pathlib import Path

# Import from parent tools/
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "config_generator",
    str(Path(__file__).resolve().parent.parent / "tools" / "config_generator.py")
)
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)


def test_generate_config_development():
    """generate_config() for development environment."""
    cfg = cg.generate_config("development")
    assert cfg["app"]["environment"] == "development"
    assert cfg["app"]["debug"] is True
    assert cfg["app"]["log_level"] == "debug"
    assert cfg["database"]["name"] == "tent_dev"
    assert cfg["auth"]["jwt_expiry_minutes"] == 1440  # dev override
    assert cfg["features"]["dark_mode"] is True  # from default
    print("    ✓ development config correct")


def test_generate_config_production():
    """generate_config() for production environment."""
    cfg = cg.generate_config("production")
    assert cfg["app"]["environment"] == "production"
    assert cfg["app"]["debug"] is False
    assert cfg["app"]["log_level"] == "info"
    assert cfg["database"]["name"] == "tent_production"
    assert cfg["database"]["pool_max"] == 50  # prod override
    assert cfg["auth"]["mfa_required"] is True  # prod override
    assert cfg["features"]["dark_mode"] is True  # from default
    print("    ✓ production config correct")


def test_generate_config_custom_overrides():
    """generate_config() with caller-provided overrides."""
    overrides = {
        "app": {"log_level": "error"},
        "server": {"port": 9090},
        "features": {"dark_mode": False},
    }
    cfg = cg.generate_config("production", overrides)
    assert cfg["app"]["log_level"] == "error"  # override wins
    assert cfg["server"]["port"] == 9090  # override wins
    assert cfg["features"]["dark_mode"] is False  # override wins
    assert cfg["database"]["name"] == "tent_production"  # env override still applies
    print("    ✓ custom overrides applied correctly")


def test_merge_config_deep_merge():
    """merge_config() does deep merge, not shallow replace."""
    base = {
        "a": 1,
        "b": {"x": 10, "y": 20},
        "c": ["original"],
    }
    override = {
        "b": {"y": 99, "z": 30},  # y replaced, x preserved, z added
        "d": "new",
    }
    merged = cg.merge_config(base, override)
    assert merged["a"] == 1  # preserved
    assert merged["b"]["x"] == 10  # deep preserved
    assert merged["b"]["y"] == 99  # deep overridden
    assert merged["b"]["z"] == 30  # deep added
    assert merged["c"] == ["original"]  # unchanged
    assert merged["d"] == "new"  # added
    assert "x" in merged["b"]  # structural integrity
    print("    ✓ deep merge, no mutation of unrelated keys")


def test_merge_config_no_mutation():
    """merge_config() does not mutate the base dict."""
    base = {"key": {"nested": "original"}}
    override = {"key": {"nested": "changed"}}
    _ = cg.merge_config(base, override)
    assert base["key"]["nested"] == "original"  # base unchanged
    print("    ✓ base dict not mutated")


def test_merge_config_empty_override():
    """merge_config() with empty override returns base."""
    base = {"a": 1, "b": {"c": 2}}
    merged = cg.merge_config(base, {})
    assert merged == base
    print("    ✓ empty override returns base")


def test_mask_sensitive_database_password():
    """mask_sensitive() redacts database.password."""
    cfg = {"database": {"host": "localhost", "password": "supersecret"}}
    masked = cg.mask_sensitive(cfg)
    assert masked["database"]["host"] == "localhost"  # non-sensitive visible
    assert masked["database"]["password"] == "***REDACTED***"
    print("    ✓ database.password redacted")


def test_mask_sensitive_redis_password():
    """mask_sensitive() redacts redis.password."""
    cfg = {"redis": {"host": "localhost", "password": "secret"}}
    masked = cg.mask_sensitive(cfg)
    assert masked["redis"]["password"] == "***REDACTED***"
    print("    ✓ redis.password redacted")


def test_mask_sensitive_jwt_secret():
    """mask_sensitive() redacts auth.jwt_secret."""
    cfg = {"auth": {"jwt_secret": "my-secret-key"}}
    masked = cg.mask_sensitive(cfg)
    assert masked["auth"]["jwt_secret"] == "***REDACTED***"
    print("    ✓ auth.jwt_secret redacted")


def test_mask_sensitive_non_sensitive_values_visible():
    """mask_sensitive() leaves non-sensitive values visible."""
    cfg = {
        "app": {"name": "tent-of-trials", "version": "3.2.0"},
        "server": {"host": "0.0.0.0", "port": 8080},
    }
    masked = cg.mask_sensitive(cfg)
    assert masked["app"]["name"] == "tent-of-trials"
    assert masked["server"]["port"] == 8080
    print("    ✓ non-sensitive values visible")


def test_mask_sensitive_nested_unchanged():
    """mask_sensitive() preserves non-sensitive nested structure."""
    cfg = {
        "app": {"name": "test"},
        "database": {"password": "secret", "host": "db.example.com"},
    }
    masked = cg.mask_sensitive(cfg)
    assert masked["app"] == {"name": "test"}
    assert masked["database"]["host"] == "db.example.com"
    print("    ✓ nested non-sensitive structure preserved")


def test_sensitive_keys_deduplicated():
    """SENSITIVE_KEYS should not have duplicates."""
    assert len(cg.SENSITIVE_KEYS) == len(set(cg.SENSITIVE_KEYS)), \
        f"Duplicates found: {cg.SENSITIVE_KEYS}"
    print(f"    ✓ SENSITIVE_KEYS deduplicated ({len(cg.SENSITIVE_KEYS)} unique)")


def test_sensitive_keys_content():
    """SENSITIVE_KEYS contains expected keys."""
    expected = {"database.password", "redis.password", "auth.jwt_secret"}
    actual = set(cg.SENSITIVE_KEYS)
    assert actual == expected, f"Expected {expected}, got {actual}"
    print("    ✓ SENSITIVE_KEYS content correct")


def main():
    print("=" * 60)
    print("Config Generator Validation Tests")
    print("=" * 60)

    tests = [
        ("Development environment config", test_generate_config_development),
        ("Production environment config", test_generate_config_production),
        ("Custom CLI overrides", test_generate_config_custom_overrides),
        ("Deep recursive merge", test_merge_config_deep_merge),
        ("No mutation of base dict", test_merge_config_no_mutation),
        ("Empty override", test_merge_config_empty_override),
        ("Database password redaction", test_mask_sensitive_database_password),
        ("Redis password redaction", test_mask_sensitive_redis_password),
        ("JWT secret redaction", test_mask_sensitive_jwt_secret),
        ("Non-sensitive values visible", test_mask_sensitive_non_sensitive_values_visible),
        ("Nested structure preserved", test_mask_sensitive_nested_unchanged),
        ("SENSITIVE_KEYS deduplicated", test_sensitive_keys_deduplicated),
        ("SENSITIVE_KEYS content", test_sensitive_keys_content),
    ]

    failures = 0
    for label, test in tests:
        print(f"\n  {label}:")
        try:
            test()
        except Exception as e:
            import traceback
            print(f"    FAILED: {e}")
            traceback.print_exc()
            failures += 1

    print(f"\n  {'=' * 50}")
    total = len(tests)
    passed = total - failures
    print(f"  Results: {total} tests, {passed} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())