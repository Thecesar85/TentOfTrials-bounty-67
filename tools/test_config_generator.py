import pytest
from tools.config_generator import (
    DEFAULT_CONFIG,
    ENV_OVERRIDES,
    SENSITIVE_KEYS,
    generate_config,
    mask_sensitive,
    merge_config,
)


class TestMergeConfig:
    def test_flat_override(self):
        base = {"a": 1, "b": 2}
        result = merge_config(base, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_nested_override(self):
        base = {"db": {"host": "localhost", "port": 5432}}
        result = merge_config(base, {"db": {"port": 3306}})
        assert result["db"]["host"] == "localhost"
        assert result["db"]["port"] == 3306

    def test_deep_nested_override(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        result = merge_config(base, {"a": {"b": {"c": 10}}})
        assert result["a"]["b"]["c"] == 10
        assert result["a"]["b"]["d"] == 2

    def test_add_new_key(self):
        base = {"a": 1}
        result = merge_config(base, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_does_not_mutate_base(self):
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}
        merge_config(base, override)
        assert base["a"]["b"] == 1

    def test_unrelated_nested_keys_unchanged(self):
        base = {"x": {"a": 1, "b": 2}, "y": {"c": 3}}
        result = merge_config(base, {"x": {"a": 10}})
        assert result["x"]["b"] == 2
        assert result["y"]["c"] == 3


class TestGenerateConfig:
    def test_development_environment(self):
        config = generate_config("development")
        assert config["app"]["environment"] == "development"
        assert config["app"]["debug"] is True
        assert config["database"]["name"] == "tent_dev"

    def test_staging_environment(self):
        config = generate_config("staging")
        assert config["app"]["environment"] == "staging"
        assert config["database"]["name"] == "tent_staging"
        assert config["database"]["pool_max"] == 20

    def test_production_environment(self):
        config = generate_config("production")
        assert config["app"]["environment"] == "production"
        assert config["app"]["debug"] is False
        assert config["database"]["name"] == "tent_production"
        assert config["database"]["pool_max"] == 50
        assert config["database"]["pool_min"] == 10
        assert config["auth"]["mfa_required"] is True

    def test_production_features(self):
        config = generate_config("production")
        assert config["features"]["margin_trading"] is True
        assert config["features"]["ai_assistant"] is False

    def test_unknown_env_returns_defaults(self):
        config = generate_config("nonexistent")
        assert config["app"]["name"] == "tent-of-trials"
        assert config["database"]["name"] == "tent_dev"

    def test_custom_overrides(self):
        config = generate_config("development", overrides={"server": {"port": 9999}})
        assert config["server"]["port"] == 9999
        assert config["app"]["environment"] == "development"

    def test_all_envs_produce_valid_config(self):
        for env in ENV_OVERRIDES:
            config = generate_config(env)
            assert "app" in config
            assert "database" in config
            assert "auth" in config


class TestMaskSensitive:
    def test_masks_database_password(self):
        config = {"database": {"password": "secret123", "host": "localhost"}}
        masked = mask_sensitive(config)
        assert masked["database"]["password"] == "***REDACTED***"
        assert masked["database"]["host"] == "localhost"

    def test_masks_redis_password(self):
        config = {"redis": {"password": "r3d1s", "host": "localhost"}}
        masked = mask_sensitive(config)
        assert masked["redis"]["password"] == "***REDACTED***"

    def test_masks_auth_jwt_secret(self):
        config = {"auth": {"jwt_secret": "supersecret", "jwt_expiry_minutes": 60}}
        masked = mask_sensitive(config)
        assert masked["auth"]["jwt_secret"] == "***REDACTED***"
        assert masked["auth"]["jwt_expiry_minutes"] == 60

    def test_non_sensitive_values_preserved(self):
        config = {"database": {"host": "localhost", "port": 5432, "name": "mydb"}}
        masked = mask_sensitive(config)
        assert masked["database"]["host"] == "localhost"
        assert masked["database"]["port"] == 5432
        assert masked["database"]["name"] == "mydb"

    def test_empty_config(self):
        assert mask_sensitive({}) == {}

    def test_deep_nested_non_sensitive_preserved(self):
        config = {"level1": {"level2": {"password": "x", "other": "y"}}}
        masked = mask_sensitive(config)
        assert masked["level1"]["level2"]["other"] == "y"

    def test_full_config_masking(self):
        config = generate_config("development")
        masked = mask_sensitive(config)
        assert masked["database"]["password"] == "***REDACTED***"
        assert masked["redis"]["password"] == "***REDACTED***"
        assert masked["auth"]["jwt_secret"] == "***REDACTED***"
        assert masked["app"]["name"] == "tent-of-trials"
