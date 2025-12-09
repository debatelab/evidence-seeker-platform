# Bug Report: Hugging Face Inference backend posts to wrong endpoint

**Issue:** When using `embed_backend_type="huggingface_inference_api"`, EvidenceSeeker appends `/embed` to the provided base URL. For Hugging Face Inference (router or model URLs), the correct endpoint is the model URL itself; `/embed` causes the call to return an error payload (dict), leading to `KeyError: 0` when determining embedding dimension.

## Context
- EvidenceSeeker retrieval, backend type: `huggingface_inference_api`
- Base URL set to a model endpoint, e.g. `https://router.huggingface.co/hf-inference/models/BAAI/bge-m3`
- EvidenceSeeker uses `HFTextEmbeddingsInference` under the hood (llama-index)

## Observed failure
During `_get_embedding_dimension`, `HFTextEmbeddingsInference._call_api` posts to `base_url + "/embed"` (default endpoint from llama-index TEI client). The HF router expects POST directly to the model URL; appending `/embed` returns an error object, not a list, so indexing `[0]` raises `KeyError: 0` and `_get_embedding_dimension` raises `ValueError`.

### Stack highlights
```
evidence_seeker/retrieval/base.py:_get_embedding_dimension -> embed_model.get_text_embedding("sample text")
llama_index.embeddings.text_embeddings_inference.base.TextEmbeddingsInference._call_api -> POST to f"{base_url}{endpoint}" (endpoint defaults to /embed)
KeyError: 0
ValueError: Could not determine embedding dimension: 0
```

## Root cause
`_get_text_embeddings_inference_kwargs` passes `base_url` but not `endpoint`, so `HFTextEmbeddingsInference` defaults to `endpoint="/embed"`. That path is correct for TEI-like servers, but **not** for Hugging Face Inference/Router, which requires posting directly to the model URL.

## Fix suggestion
In `evidence_seeker/retrieval/base.py`, when `embed_backend_type == EmbedBackendType.HUGGINGFACE_INFERENCE_API`, set `endpoint = ""` (or `None`) so llama-index posts directly to `base_url` without appending `/embed`.

```python
elif embed_backend_type == EmbedBackendType.HUGGINGFACE_INFERENCE_API:
    kwargs = {
        "model_name": embed_model_name,
        "base_url": embed_base_url,
        "embed_batch_size": embed_batch_size,
        "auth_token": token,
        "bill_to": bill_to,
    }
    # Do not append /embed for HF inference model URLs
    kwargs["endpoint"] = ""
    if trust_remote_code is not None:
        kwargs["trust_remote_code"] = trust_remote_code
    return kwargs
```

## Notes
- Applies to any HF inference/model URL (router or direct hosted model). 
- With the above change, `_get_embedding_dimension` succeeds and embeddings flow normally.
