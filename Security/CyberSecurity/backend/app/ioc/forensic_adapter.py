"""Sprint-2 (Intern-4): adapter from the REAL forensic engine output to IOC inputs.

Consumes the exact dict returned by ``process_evidence()`` in the team repo
(``Forensic/forensic_engine.py``) — keys verified: ``hash``,
``file_identification{is_mismatch,category}``, ``filesystem_metadata``,
``exif{has_exif,datetime_original}``, ``document_metadata{author,...}``,
``log_entries[{line_number,timestamp,level,source_ip,raw_line}]``,
``timeline_events``, ``processing_errors``.

Two outputs:
  1. ``evidence_text()`` — plain text the IOC extractor scans (log raw lines
     + document/exif strings). Never binary.
  2. ``forensic_inputs()`` — list of ``{evidence_id, severity, title,
     timestamp}`` for ``correlation.correlate(records, forensic=...)``.

Severity mapping (honest, documented — this adapter triages, Intern-3 owns
the full forensic classifier):
  - log level CRITICAL/FATAL or ERROR repeated from one IP -> "critical"
  - log level ERROR/WARN, or file extension mismatch -> "suspicious"
  - otherwise -> "normal"
"""
from __future__ import annotations

from typing import Any


def evidence_text(result: dict) -> str:
    """Flatten a process_evidence() result to scannable text (≤5MB, truncated)."""
    parts: list[str] = []
    for entry in result.get("log_entries") or []:
        raw = entry.get("raw_line")
        if raw:
            parts.append(str(raw)[:1000])
    doc = result.get("document_metadata") or {}
    for key in ("author", "title", "last_modified_by", "application"):
        if doc.get(key):
            parts.append(str(doc[key])[:500])
    exif = result.get("exif") or {}
    if exif.get("has_exif"):
        for key in ("camera_make", "camera_model", "software", "datetime_original"):
            if exif.get(key):
                parts.append(str(exif[key])[:500])
    text = "\n".join(parts)
    return text.encode("utf-8", errors="ignore")[:5_242_880].decode("utf-8", errors="ignore")


def _classify(log_entries: list[dict], is_mismatch: bool) -> tuple[str, str]:
    """Return (severity, title) from real engine signals. Critical lines flagged."""
    crit = sum(1 for e in log_entries if str(e.get("level") or "").upper() in ("CRITICAL", "FATAL"))
    errs = [e for e in log_entries if str(e.get("level") or "").upper() == "ERROR"]
    err_ips = {e.get("source_ip") for e in errs if e.get("source_ip")}
    if crit > 0:
        return "critical", f"{crit} critical log event(s)"  # CRITICAL level is never noise
    if errs and len(errs) >= 3 and len(err_ips) == 1:
        return "critical", f"{len(errs)} errors from single host {next(iter(err_ips))}"  # brute-force shape
    if errs or is_mismatch:
        reason = "extension mismatch (possible disguise)" if is_mismatch else f"{len(errs)} error event(s)"
        return "suspicious", reason
    # Failed-auth shape without an ERROR level (e.g. sshd "Failed password"):
    # ≥3 fail-lines from one IP = brute-force triage signal, still heuristic.
    fail_ips: dict[str, int] = {}
    for e in log_entries:
        raw = str(e.get("raw_line") or "").lower()
        if "fail" in raw or "denied" in raw or "blocked" in raw:
            ip = e.get("source_ip") or "unknown"
            fail_ips[ip] = fail_ips.get(ip, 0) + 1
    if fail_ips:
        top_ip, top_n = max(fail_ips.items(), key=lambda kv: kv[1])
        if top_n >= 3 and len(fail_ips) == 1:
            return "suspicious", f"{top_n} failed-auth events from single host {top_ip}"
    warns = sum(1 for e in log_entries if str(e.get("level") or "").upper().startswith("WARN"))
    if warns:
        return "suspicious", f"{warns} warning event(s)"
    return "normal", "no error/critical signals, no type mismatch"


def forensic_inputs(result: dict, evidence_id: str) -> list[dict]:
    """Map one engine result to the correlation forensic-input contract."""
    entries = result.get("log_entries") or []
    ident = result.get("file_identification") or {}
    severity, title = _classify(entries, bool(ident.get("is_mismatch")))
    ts = None
    for e in entries:  # first timestamped entry anchors the finding in time
        if e.get("timestamp"):
            ts = e["timestamp"]
            break
    return [{"evidence_id": evidence_id, "severity": severity,
             "title": title, "timestamp": ts}]


def load_engine():
    """Import the team engine if available (local path override via env)."""
    import os  # local import: keeps module import side-effect free
    import sys
    extra = os.getenv("FORENSIC_ENGINE_PATH", "/tmp/opencode/team-repo/Forensic")
    if extra not in sys.path:
        sys.path.insert(0, extra)
    try:
        from forensic_engine import process_evidence  # type: ignore[import]
        return process_evidence
    except Exception:
        return None
