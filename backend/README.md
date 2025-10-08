# Evidence Seeker Backend

This is the FastAPI backend package for the Evidence Seeker Platform.

It is built as a Python package (PEP 621 metadata in `pyproject.toml`).

## Development

Install (editable) with dev extras:

```
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
```

## Running

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Packaging Notes

- The top-level project README lives one directory up; this lightweight README satisfies the `readme = "README.md"` field in `pyproject.toml` for building wheels inside the backend build context.
- Adjust as needed if you want a richer backend-specific description.
