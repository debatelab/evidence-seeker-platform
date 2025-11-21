"""Lazy exports for app.models to avoid importing heavy dependencies eagerly."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "User",
    "EvidenceSeeker",
    "EvidenceSeekerSettings",
    "FactCheckRun",
    "FactCheckResult",
    "FactCheckEvidence",
    "FactCheckRunStatus",
    "InterpretationType",
    "ConfirmationLevel",
    "EvidenceStance",
    "IndexJob",
    "IndexJobStatus",
    "Document",
    "APIKey",
    "Permission",
]

_EXPORT_MAP = {
    "User": "user",
    "EvidenceSeeker": "evidence_seeker",
    "EvidenceSeekerSettings": "evidence_seeker_settings",
    "FactCheckRun": "fact_check",
    "FactCheckResult": "fact_check",
    "FactCheckEvidence": "fact_check",
    "FactCheckRunStatus": "fact_check",
    "InterpretationType": "fact_check",
    "ConfirmationLevel": "fact_check",
    "EvidenceStance": "fact_check",
    "IndexJob": "index_job",
    "IndexJobStatus": "index_job",
    "Document": "document",
    "APIKey": "api_key",
    "Permission": "permission",
}

_MODULES_LOADED = False


def _ensure_modules_loaded() -> None:
    """Eagerly import model modules so SQLAlchemy relationships resolve."""
    global _MODULES_LOADED
    if _MODULES_LOADED:
        return
    for module_name in sorted(set(_EXPORT_MAP.values())):
        import_module(f"{__name__}.{module_name}")
    _MODULES_LOADED = True


_ensure_modules_loaded()


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MAP.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
