## Summary

Add focused test coverage for `tools/config_generator.py` helpers and deduplicate duplicate entries in `SENSITIVE_KEYS`. Covers `generate_config()` (dev/prod overrides), `merge_config()` (deep merge without mutation), and `mask_sensitive()` (redaction correctness).

## Changes

- **`tools/config_generator.py`**: Remove two duplicate `auth.jwt_secret` entries from `SENSITIVE_KEYS` (5→3 items, same redaction behaviour)
- **`tests/test_config_generator.py`**: New test file with 18 tests across 4 test classes

## Testing

```
python3 -m pytest tests/test_config_generator.py -v   # 18 passed in 0.55s
python3 build.py --module all                          # 3/10 modules pass (Python/Rust/Go ok, missing deps for C/Java/Ruby/Lua/Haskell)
```

## Checklist

- [x] Relevant modules affected by these changes build locally
- [x] Tests pass locally
- [x] Diagnostic build log is committed in this PR
- [x] Changes are scoped to the PR purpose

---

- [ ] I would like to request that my diagnostic build log is removed before merging
