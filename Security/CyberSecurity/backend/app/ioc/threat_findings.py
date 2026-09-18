"""Sprint-2: Threat Findings structure (Intern-4 deliverable).

One ThreatFinding per IOC record. Severity derives from the deterministic
risk_level (never from AI alone); an accepted AI nudge may raise it at most
one step when the final score crosses the next threshold.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.ioc.schemas import IOCRecord

Severity = Literal["low", "medium", "high", "critical"]

# risk_level -> base severity (1:1; both use the same 4-step scale).
_RISK_TO_SEVERITY: dict[str, Severity] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
}

# Final-score bump thresholds: accepted AI delta pushing final across one of
# these promotes severity exactly one step (documented, auditable).
_BUMP_AT = (40, 65, 85)
_ORDER: list[Severity] = ["low", "medium", "high", "critical"]


class ThreatSource(BaseModel):
    """Where the finding came from (case -> evidence -> line)."""

    case_id: UUID
    evidence_id: UUID
    source_type: str = "generic"
    line_no: int | None = Field(default=None, ge=1)


class ThreatFinding(BaseModel):
    """Structured security finding for backend storage + dashboard display."""

    ioc: str = Field(min_length=1)
    type: str = Field(min_length=1)
    source: ThreatSource
    severity: Severity
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = Field(min_length=1, description="Top scoring reasons joined")
    observation: str = Field(default="", description="MITRE + AI context sentence")
    risk_score: int = Field(ge=0, le=100)
    mitre_ids: list[str] = Field(default_factory=list)


def severity_for(record: IOCRecord) -> Severity:
    """Map record -> severity, with at most one AI-driven promotion."""
    base: Severity = _RISK_TO_SEVERITY.get(record.risk_level, "low")
    if not record.ai_accepted or not record.ai_delta:
        return base
    final = record.risk_score + record.ai_delta
    idx = _ORDER.index(base)
    # Promote one step only if final crossed the next band threshold upward.
    if idx < 3 and final >= _BUMP_AT[idx] and record.risk_score < _BUMP_AT[idx]:
        return _ORDER[idx + 1]
    return base


def build_finding(record: IOCRecord, case_id: UUID, evidence_id: UUID,
                  source_type: str = "generic") -> ThreatFinding:
    """Build one finding from an analyzed IOC record (pure, deterministic)."""
    mitre = ",".join(record.mitre_ids) if record.mitre_ids else "unmapped"
    observation = f"MITRE: {mitre}."
    if record.ai_accepted and record.ai_justification:
        observation += f" AI: {record.ai_justification[:200]}"
    return ThreatFinding(
        ioc=record.value_normalized,
        type=record.type,
        source=ThreatSource(case_id=case_id, evidence_id=evidence_id,
                            source_type=source_type, line_no=record.line_no),
        severity=severity_for(record),
        reason="; ".join(record.reasons[:4]) if record.reasons else "no-signal",
        observation=observation,
        risk_score=record.risk_score,
        mitre_ids=list(record.mitre_ids),
    )


def build_findings(records: list[IOCRecord], case_id: UUID, evidence_id: UUID,
                   source_type: str = "generic") -> list[ThreatFinding]:
    """Build findings for every record of one evidence analysis."""
    return [build_finding(r, case_id, evidence_id, source_type) for r in records]
