# Bug Report: LlamaIndex Workflow Context API Incompatibility

## Description

The `evidence-seeker` library (v0.1.2b1) uses deprecated LlamaIndex workflow Context API methods (`ctx.set()` and `ctx.get()`) that have been removed in `llama-index-core` v0.14.4 and replaced with a new `ctx.store` API. This causes runtime failures when executing the preprocessing workflow.

## Environment

- **evidence-seeker version:** 0.1.2b1
- **llama-index-core version:** 0.14.4
- **Python version:** 3.12

## Steps to Reproduce

1. Install evidence-seeker 0.1.2b1 with llama-index-core 0.14.4
2. Create a preprocessing config with Hugging Face Inference API models
3. Execute a fact-check with any claim

## Error

```
AttributeError: 'Context' object has no attribute 'set'
```

**Full traceback:**
```python
File "evidence_seeker/preprocessing/workflows.py", line 299, in list_normative_claims
    await ctx.set("num_normative_claims", len(claims.claims))
          ^^^^^^^
AttributeError: 'Context' object has no attribute 'set'
```

## Root Cause

The LlamaIndex workflow `Context` API was redesigned between versions. The old methods:
- `await ctx.set(key, value)`
- `await ctx.get(key, default)`

Have been **replaced** with a typed state store:
- `ctx.store` (an `InMemoryStateStore` instance with async `set()` and `get()` methods)

**Affected code locations in `evidence_seeker/preprocessing/workflows.py`:**

| Line | Old Code | Required Change |
|------|----------|----------------|
| ~160 | `await ctx.set("num_descriptive_claims", len(claims.claims))` | `await ctx.store.set("num_descriptive_claims", len(claims.claims))` |
| ~227 | `await ctx.set("num_ascriptive_claims", len(claims.claims))` | `await ctx.store.set("num_ascriptive_claims", len(claims.claims))` |
| ~299 | `await ctx.set("num_normative_claims", len(claims.claims))` | `await ctx.store.set("num_normative_claims", len(claims.claims))` |
| ~349 | `num_descriptive_claims = await ctx.get("num_descriptive_claims", 0)` | `num_descriptive_claims = await ctx.store.get("num_descriptive_claims", 0)` |
| ~350 | `num_ascriptive_claims = await ctx.get("num_ascriptive_claims", 0)` | `num_ascriptive_claims = await ctx.store.get("num_ascriptive_claims", 0)` |
| ~351 | `num_normative_claims = await ctx.get("num_normative_claims", 0)` | `num_normative_claims = await ctx.store.get("num_normative_claims", 0)` |

## Suggested Fix

### Option 1: Update to New API (Recommended)

Replace all instances of `ctx.set()` and `ctx.get()` with `ctx.store.set()` and `ctx.store.get()`:

```python
# Old (deprecated)
await ctx.set("num_descriptive_claims", len(claims.claims))
num_descriptive_claims = await ctx.get("num_descriptive_claims", 0)

# New (current API)
await ctx.store.set("num_descriptive_claims", len(claims.claims))
num_descriptive_claims = await ctx.store.get("num_descriptive_claims", 0)
```

The new `ctx.store` is an `InMemoryStateStore` that provides:
- `await ctx.store.set(key: str, value: Any) -> None`
- `await ctx.store.get(key: str, default: Any = None) -> Any`

**Complete diff for `evidence_seeker/preprocessing/workflows.py`:**

```diff
- await ctx.set("num_descriptive_claims", len(claims.claims))
+ await ctx.store.set("num_descriptive_claims", len(claims.claims))

- await ctx.set("num_ascriptive_claims", len(claims.claims))
+ await ctx.store.set("num_ascriptive_claims", len(claims.claims))

- await ctx.set("num_normative_claims", len(claims.claims))
+ await ctx.store.set("num_normative_claims", len(claims.claims))

- num_descriptive_claims = await ctx.get("num_descriptive_claims", 0)
- num_ascriptive_claims = await ctx.get("num_ascriptive_claims", 0)
- num_normative_claims = await ctx.get("num_normative_claims", 0)
+ num_descriptive_claims = await ctx.store.get("num_descriptive_claims", 0)
+ num_ascriptive_claims = await ctx.store.get("num_ascriptive_claims", 0)
+ num_normative_claims = await ctx.store.get("num_normative_claims", 0)
```

### Option 2: Pin llama-index Version (Not Feasible)

Theoretically, you could add a version constraint to pin an older version:

```toml
llama-index-core = "<0.12.0"  # version that still had ctx.set/get
```

**However, this is not feasible** because:
- `llama-index-vector-stores-postgres` (a required dependency of evidence-seeker) requires `llama-index-core>=0.12.0`
- The old Context API was removed in version 0.12.0
- This creates an impossible dependency constraint - downgrading llama-index-core would break the postgres vector store
- Users cannot resolve this conflict without breaking other required packages
- It prevents users from using newer LlamaIndex features and security updates

## Additional Context

1. **No version constraints**: The `evidence-seeker` package currently doesn't specify version constraints for `llama-index` in its dependencies, which allows incompatible versions to be installed.

2. **API migration is simple**: The fix is straightforward - just add `.store` between `ctx` and the method call. The method signatures and behavior are identical.

3. **Current LlamaIndex Context API**: The new API provides a typed state store (`InMemoryStateStore`) that supports:
   - Async get/set operations
   - Type-safe state management with Pydantic models (optional)
   - Serialization/deserialization for workflow persistence
   - See: [llama-index workflows Context documentation](https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/workflow/context.py)

## Recommendation

Please update `evidence_seeker/preprocessing/workflows.py` to use the new `ctx.store` API. This is a simple find-and-replace operation that will make the library compatible with current and future versions of LlamaIndex.

If you need to maintain backward compatibility with older LlamaIndex versions, you could add a compatibility shim:

```python
# At the top of workflows.py
def get_store(ctx):
    """Get the state store, handling both old and new Context API"""
    return getattr(ctx, 'store', ctx)  # falls back to ctx itself for old API
```

Then use: `await get_store(ctx).set(...)` and `await get_store(ctx).get(...)`
