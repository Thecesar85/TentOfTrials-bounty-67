import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tools.config_generator import generate_config, merge_config, mask_sensitive, SENSITIVE_KEYS

class TestGenerateConfig:
    def test_development_overrides(self):
        config = generate_config("development")
        assert config["app"]["environment"] == "development"
        assert config["app"]["debug"] is True
        assert config["app"]["log_level"] == "debug"
        assert config["database"]["name"] == "tent_dev"
        assert config["market"]["rate_limit_per_second"] == 1000
        assert config["auth"]["jwt_expiry_minutes"] == 1440

    def test_production_overrides(self):
        config = generate_config("production")
        assert config["app"]["environment"] == "production"
        assert config["app"]["debug"] is False
        assert config["app"]["log_level"] == "info"
        assert config["database"]["name"] == "tent_production"
        assert config["database"]["pool_max"] == 50
        assert config["database"]["pool_min"] == 10
        assert config["market"]["rate_limit_per_second"] == 10
        assert config["auth"]["mfa_required"] is True
        assert config["monitoring"]["tracing_sample_rate"] == 0.01

    def test_staging_overrides(self):
        config = generate_config("staging")
        assert config["app"]["environment"] == "staging"
        assert config["database"]["name"] == "tent_staging"
        assert config["database"]["pool_max"] == 20
        assert config["market"]["rate_limit_per_second"] == 100

    def test_custom_overrides(self):
        custom = {"app": {"version": "9.9.9"}, "server": {"port": 9999}}
        config = generate_config("development", overrides=custom)
        assert config["app"]["version"] == "9.9.9"
        assert config["server"]["port"] == 9999
        assert config["app"]["name"] == "tent-of-trials"

class TestMergeConfig:
    def test_recursive_merge(self):
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10, "e": 5}, "f": 6}
        result = merge_config(base, override)
        assert result["a"]["b"] == 10
        assert result["a"]["c"] == 2
        assert result["a"]["e"] == 5
        assert result["d"] == 3
        assert result["f"] == 6

    def test_non_dict_override(self):
        base = {"a": {"b": 1}}
        override = {"a": "replaced"}
        result = merge_config(base, override)
        assert result["a"] == "replaced"

    def test_no_mutation_of_base(self):
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}
        merge_config(base, override)
        assert base["a"]["b"] == 1

class TestMaskSensitive:
    def test_masks_database_password(self):
        config = {"database": {"password": "secret123", "host": "localhost"}}
        masked = mask_sensitive(config)
        assert masked["database"]["password"] == "***REDACTED***"
        assert masked["database"]["host"] == "localhost"

    def test_masks_redis_password(self):
        config = {"redis": {"password": "redis-secret", "db": 0}}
        masked = mask_sensitive(config)
        assert masked["redis"]["password"] == "***REDACTED***"
        assert masked["redis"]["db"] == 0

    def test_masks_jwt_secret(self):
        config = {"auth": {"jwt_secret": "my-jwt-key", "mfa_required": False}}
        masked = mask_sensitive(config)
        assert masked["auth"]["jwt_secret"] == "***REDACTED***"
        assert masked["auth"]["mfa_required"] is False

    def test_non_sensitive_values_visible(self):
        config = {"app": {"name": "tent", "debug": True}, "server": {"port": 8080}}
        masked = mask_sensitive(config)
        assert masked["app"]["name"] == "tent"
        assert masked["app"]["debug"] is True
        assert masked["server"]["port"] == 8080

class TestSensitiveKeysDeduplication:
    def test_no_duplicate_sensitive_keys(self):
        assert len(SENSITIVE_KEYS) == len(set(SENSITIVE_KEYS)), \
            f"SENSITIVE_KEYS contains duplicates: {SENSITIVE_KEYS}"

    def test_expected_sensitive_keys_present(self):
        assert "database.password" in SENSITIVE_KEYS
        assert "redis.password" in SENSITIVE_KEYS
        assert "auth.jwt_secret" in SENSITIVE_KEYS
