import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from config_generator import (
    generate_config,
    merge_config,
    mask_sensitive,
    SENSITIVE_KEYS,
)

def test_merge_config_does_not_mutate_base():
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    override = {"a": {"b": 10, "e": 5}, "f": 6}
    base_copy = {"a": {"b": 1, "c": 2}, "d": 3}
    override_copy = {"a": {"b": 10, "e": 5}, "f": 6}
    result = merge_config(base, override)
    assert result == {"a": {"b": 10, "c": 2, "e": 5}, "d": 3, "f": 6}
    assert base == base_copy
    assert override == override_copy

def test_merge_config_nested_overrides():
    base = {"server": {"host": "localhost", "port": 8080}}
    override = {"server": {"port": 9090}}
    result = merge_config(base, override)
    assert result == {"server": {"host": "localhost", "port": 9090}}

def test_generate_config_development():
    config = generate_config("development")
    assert config["app"]["environment"] == "development"
    assert config["app"]["debug"] is True

def test_generate_config_production():
    config = generate_config("production")
    assert config["app"]["environment"] == "production"
    assert config["app"]["debug"] is False

def test_generate_config_with_overrides():
    overrides = {"server": {"port": 3000}}
    config = generate_config("development", overrides=overrides)
    assert config["server"]["port"] == 3000

def test_mask_sensitive_redacts_secrets():
    config = {
        "database": {"host": "localhost", "password": "secret"},
        "redis": {"host": "localhost", "password": "secret"},
        "auth": {"jwt_secret": "secret", "jwt_expiry_minutes": 60},
    }
    masked = mask_sensitive(config)
    assert masked["database"]["password"] == "***REDACTED***"
    assert masked["redis"]["password"] == "***REDACTED***"
    assert masked["auth"]["jwt_secret"] == "***REDACTED***"
    assert masked["auth"]["jwt_expiry_minutes"] == 60

def test_sensitive_keys_deduplicated():
    assert len(SENSITIVE_KEYS) == len(set(SENSITIVE_KEYS))
