"""Tenant-scoped deterministic dedupe keys."""

from __future__ import annotations

import hashlib


def normalize_value(ioc_type: str, value: str) -> str:
    v = (value or "").strip()
    if (ioc_type or "").lower() in ("domain", "email", "url", "md5", "sha1", "sha256", "sha512", "hash"):
        v = v.lower()
    if (ioc_type or "").lower() == "domain":
        v = v.rstrip(".")
    return v


def dedupe_key(tenant_id: str, ioc_type: str, value: str) -> str:
    """Deterministic ``sha256(tenant|type|normalized-value)`` hex digest."""
    norm = normalize_value(ioc_type, value)
    blob = f"{str(tenant_id).strip().lower()}|{(ioc_type or '').strip().lower()}|{norm}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
