import pytest
from tools.config_generator import generate_config, merge_config, mask_sensitive, SENSITIVE_KEYS

def test_sensitive_keys_deduplicated():
    # Check that duplicate 'auth.jwt_secret' is removed
    assert SENSITIVE_KEYS == ['auth.jwt_secret', 'database.password', 'redis.password']

def test_generate_config_development():
    config = generate_config('development')
    assert config['app']['debug'] is True
    # Additional checks that development defaults are present
    assert config['database']['password'] == 'secret'
    assert config['redis']['password'] == 'supersecret'
    assert config['auth']['jwt_secret'] == 'myjwtsecret'

def test_generate_config_production():
    config = generate_config('production')
    assert config['app']['debug'] is False
    assert config['app']['port'] == 8080
    assert config['database']['host'] == 'prod-db.example.com'
    assert config['redis']['host'] == 'prod-redis.example.com'
    assert config['auth']['jwt_secret'] == 'productionjwtsecret'
    # Non-overridden keys should remain from base
    assert config['database']['port'] == 5432
    assert config['auth']['expiry'] == 3600

def test_merge_config_no_mutation():
    base = {'a': 1, 'b': {'c': 2, 'd': 3}}
    override = {'b': {'c': 99}}
    merged = merge_config(base, override)
    # Override should not mutate base
    assert base['b']['c'] == 2
    # Merged should have new value
    assert merged['b']['c'] == 99
    # Unrelated nested keys preserved
    assert merged['b']['d'] == 3
    # Confirm base unchanged
    assert base == {'a': 1, 'b': {'c': 2, 'd': 3}}

def test_merge_config_nested_override():
    base = {'x': {'y': {'z': 1}}}
    override = {'x': {'y': {'w': 2}}}
    merged = merge_config(base, override)
    assert merged['x']['y']['z'] == 1
    assert merged['x']['y']['w'] == 2

def test_mask_sensitive_redacts_secrets():
    config = {
        'database': {'password': 'secret123'},
        'redis': {'password': 'supersecret'},
        'auth': {'jwt_secret': 'myjwt'},
        'app': {'name': 'myapp', 'debug': True}
    }
    masked = mask_sensitive(config)
    assert masked['database']['password'] == '***REDACTED***'
    assert masked['redis']['password'] == '***REDACTED***'
    assert masked['auth']['jwt_secret'] == '***REDACTED***'
    # non-sensitive remains visible
    assert masked['app']['name'] == 'myapp'
    assert masked['app']['debug'] is True

def test_mask_sensitive_non_sensitive_dict_key():
    config = {
        'auth': {'jwt_secret': 'secret', 'expiry': 3600}
    }
    masked = mask_sensitive(config)
    assert masked['auth']['jwt_secret'] == '***REDACTED***'
    assert masked['auth']['expiry'] == 3600
