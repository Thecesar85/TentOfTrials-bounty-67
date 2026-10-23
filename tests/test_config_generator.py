"""Comprehensive unit test suite for tools/config_generator.py.

Validates environment generation, recursive merging, sensitive masking,
and multi-format export without regressions.
"""
import json
import pytest
from tools.config_generator import (
    DEFAULT_CONFIG,
    ENV_OVERRIDES,
    SENSITIVE_KEYS,
    merge_config,
    generate_config,
    mask_sensitive,
    to_json,
    to_dotenv,
    to_k8s_configmap,
    flatten_for_k8s,
)


def test_sensitive_keys_no_duplicates():
    """Ensure SENSITIVE_KEYS list contains no duplicate entries."""
    assert len(SENSITIVE_KEYS) == len(set(SENSITIVE_KEYS))
    assert "auth.jwt_secret" in SENSITIVE_KEYS
    assert "database.password" in SENSITIVE_KEYS
    assert "redis.password" in SENSITIVE_KEYS


def test_merge_config_shallow_and_nested():
    """Verify recursive dictionary merging preserves untouched sibling keys."""
    base = {
        "app": {"name": "app", "version": "1.0", "debug": False},
        "server": {"port": 8080},
    }
    override = {
        "app": {"debug": True},
        "server": {"port": 9000, "ssl": True},
    }
    merged = merge_config(base, override)
    assert merged["app"]["debug"] is True
    assert merged["app"]["version"] == "1.0"
    assert merged["server"]["port"] == 9000
    assert merged["server"]["ssl"] is True


def test_generate_config_environments():
    """Verify config generation across development, staging, and production."""
    dev = generate_config("development")
    assert dev["app"]["environment"] == "development"
    assert dev["app"]["debug"] is True

    prod = generate_config("production")
    assert prod["app"]["environment"] == "production"
    assert prod["app"]["debug"] is False

    # Custom override applied on top
    custom = generate_config("development", overrides={"app": {"custom_tag": "v1"}})
    assert custom["app"]["custom_tag"] == "v1"
    assert custom["app"]["environment"] == "development"


def test_mask_sensitive_values():
    """Verify sensitive keys are replaced with ***REDACTED*** while others remain intact."""
    sample = {
        "database": {"host": "localhost", "password": "supersecretpassword"},
        "auth": {"jwt_secret": "my-jwt-token-key", "jwt_expiry_minutes": 60},
        "app": {"name": "test"},
    }
    masked = mask_sensitive(sample)
    assert masked["database"]["password"] == "***REDACTED***"
    assert masked["database"]["host"] == "localhost"
    assert masked["auth"]["jwt_secret"] == "***REDACTED***"
    assert masked["auth"]["jwt_expiry_minutes"] == 60
    assert masked["app"]["name"] == "test"


def test_to_json_export():
    """Verify valid JSON formatting."""
    config = {"app": {"name": "test", "port": 8080}}
    json_str = to_json(config, pretty=True)
    parsed = json.loads(json_str)
    assert parsed["app"]["name"] == "test"
    assert parsed["app"]["port"] == 8080


def test_to_dotenv_export():
    """Verify dotenv flat formatting with uppercase keys."""
    config = {"app": {"name": "test", "debug": True}}
    dotenv_str = to_dotenv(config)
    assert "APP_NAME=test" in dotenv_str
    assert "APP_DEBUG=true" in dotenv_str


def test_flatten_and_k8s_configmap():
    """Verify Kubernetes ConfigMap generation."""
    config = {"app": {"name": "tent-app", "version": "1.0"}}
    flat = flatten_for_k8s(config)
    assert ("app.name", "tent-app") in flat
    assert ("app.version", "1.0") in flat

    cm = to_k8s_configmap(config, name="custom-config")
    assert "kind: ConfigMap" in cm
    assert "name: custom-config" in cm
    assert 'app.name: "tent-app"' in cm
