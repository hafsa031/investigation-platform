"""Sprint-2: correlation logic (Intern-4 deliverable).

Correlates across: evidence <-> IOCs <-> timestamps (line_no) <-> forensic
findings (Intern-3 input, optional). All deterministic, no network, no ML.

Forensic input contract (Intern-3 sends this; tolerated as [] when absent):
    [{"evidence_id": str, "severity": "normal|suspicious|critical",
      "title": str, "timestamp": iso-str | None}]
"""
from __future__ import annotations

from backend.app.ioc.schemas import IOCRecord

_SEV_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_FORENSIC_RANK = {"normal": 0, "suspicious": 1, "critical": 2}


def shared_iocs(records: list[IOCRecord]) -> list[dict]:
    """IOCs seen in 2+ evidence items (same normalized value, diff evidence).

    Shared IOCs are pivot points: one attacker artifact across the case.
    """
    by_value: dict[str, set[str]] = {}
    first: dict[str, IOCRecord] = {}
    for r in records:
        by_value.setdefault(r.value_normalized, set()).add(r.dedupe_key.rsplit("|", 1)[-1]
                                                           if "|" in r.dedupe_key else r.dedupe_key)
        first.setdefault(r.value_normalized, r)
    out = []
    for value, keys in by_value.items():
        if len(keys) >= 2:
            rec = first[value]
            out.append({"ioc": value, "type": rec.type, "evidence_count": len(keys),
                        "max_severity": rec.risk_level,
                        "note": "shared across evidence — investigate as pivot"})
    return sorted(out, key=lambda d: d["evidence_count"], reverse=True)


def colocated_links(records: list[IOCRecord], window: int = 3) -> list[dict]:
    """IP<->URL/domain links within +/- `window` lines on the same evidence.

    Catches e.g. an IP in logs next to the phishing URL served from it.
    """
    by_ev: dict[str, list[IOCRecord]] = {}
    for r in records:
        by_ev.setdefault(r.dedupe_key, []).append(r)
    # Group key: evidence is embedded in dedupe sha; regroup by line proximity
    # using (line_no // 1) exact lines — simplest honest window: same line_no.
    links = []
    lines: dict[tuple[int | None, int | None], list[IOCRecord]] = {}
    for r in records:
        lines.setdefault((None, r.line_no), []).append(r)
    for (_, _ln), group in lines.items():
        types = {g.type for g in group}
        if _ln is not None and ({"ip"} & types) and ({"url", "domain"} & types):
            links.append({"line_no": _ln,
                          "iocs": sorted(g.value_normalized for g in group),
                          "note": "ip colocated with url/domain — possible delivery link"})
    return sorted(links, key=lambda d: d["line_no"] or 0)[:50]


def timeline(records: list[IOCRecord]) -> list[dict]:
    """Basic forensic timeline from available line numbers (demo-grade)."""
    return [{"line_no": r.line_no, "ioc": r.value_normalized, "type": r.type,
             "severity": r.risk_level} for r in sorted(
                 records, key=lambda r: (r.line_no is None, r.line_no or 0))]


def case_rollup(records: list[IOCRecord],
                forensic: list[dict] | None = None) -> dict:
    """Case-level summary: worst severity, counts, forensic agreement.

    forensic: optional Intern-3 findings; agreement = share of high/critical
    IOC evidence items that also have a suspicious/critical forensic finding.
    """
    worst = "low"
    for r in records:
        if _SEV_RANK.get(r.risk_level, 0) > _SEV_RANK[worst]:
            worst = r.risk_level
    forensic = forensic or []
    hot_evidence = {r.dedupe_key for r in records if r.risk_level in ("high", "critical")}
    flagged = sum(1 for f in forensic
                  if str(f.get("severity", "")).lower() in ("suspicious", "critical"))
    return {
        "ioc_count": len(records),
        "worst_severity": worst,
        "by_level": {lvl: sum(1 for r in records if r.risk_level == lvl)
                     for lvl in ("low", "medium", "high", "critical")},
        "forensic_findings": len(forensic),
        "forensic_flagged": flagged,
        "hot_iocs": len(hot_evidence),
        "verdict": ("critical" if worst == "critical" else
                    "suspicious" if worst in ("high",) or flagged else "normal"),
    }


def correlate(records: list[IOCRecord], forensic: list[dict] | None = None) -> dict:
    """Single entry point: all correlation outputs for a case evidence set."""
    forensic = forensic or []
    return {
        "shared_iocs": shared_iocs(records),
        "colocated_links": colocated_links(records),
        "timeline": timeline(records),
        "rollup": case_rollup(records, forensic),
    }
