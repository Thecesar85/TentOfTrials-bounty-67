import os

SENSITIVE_KEYS = [
    'auth.jwt_secret',
    'database.password',
    'redis.password',
    'auth.jwt_secret'  # duplicate
]

def deduplicate_sensitive_keys():
    seen = set()
    deduped = []
    for key in SENSITIVE_KEYS:
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped

SENSITIVE_KEYS = deduplicate_sensitive_keys()

def merge_config(base, override):
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged

def mask_sensitive(config, parent_key=''):
    masked = {}
    for key, value in config.items():
        full_key = f"{parent_key}.{key}" if parent_key else key
        if full_key in SENSITIVE_KEYS:
            masked[key] = '***REDACTED***'
        elif isinstance(value, dict):
            masked[key] = mask_sensitive(value, full_key)
        else:
            masked[key] = value
    return masked

def generate_config(env='development'):
    base_config = {
        'app': {
            'name': 'myapp',
            'debug': True,
            'port': 5000
        },
        'database': {
            'host': 'localhost',
            'port': 5432,
            'password': 'secret'
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'password': 'supersecret'
        },
        'auth': {
            'jwt_secret': 'myjwtsecret',
            'expiry': 3600
        }
    }
    env_overrides = {
        'development': {
            'app': {'debug': True}
        },
        'production': {
            'app': {'debug': False, 'port': 8080},
            'database': {'host': 'prod-db.example.com'},
            'redis': {'host': 'prod-redis.example.com'},
            'auth': {'jwt_secret': 'productionjwtsecret'}
        }
    }
    if env in env_overrides:
        return merge_config(base_config, env_overrides[env])
    return base_config
