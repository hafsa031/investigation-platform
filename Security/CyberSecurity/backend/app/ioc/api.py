"""FastAPI router for IOC analysis: prefix /api/v1/iocs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Query

from backend.app.ioc.pipeline import analyze
from backend.app.ioc.schemas import AnalyzeResponse, IOCAnalyzeRequest

router = APIRouter(prefix="/api/v1/iocs", tags=["iocs"])

# In-memory store of analyses (placeholder persistence for listing).
_ANALYSES: list[AnalyzeResponse] = []


def _current_subject(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """Placeholder auth dependency.

    Accepts missing/invalid credentials for now (fail-open) so tests and local
    dev work; wire real JWT/API-key verification here. ``GET /health`` does
    NOT depend on this (no auth).
    """
    if not authorization:
        return None
    return authorization


@router.post("/analyze", response_model=AnalyzeResponse, status_code=201)
def analyze_iocs(
    body: IOCAnalyzeRequest,
    _subject: Optional[str] = Depends(_current_subject),
) -> AnalyzeResponse:
    result = analyze(body)
    _ANALYSES.append(result)
    return result


@router.get("/", response_model=dict)
def list_iocs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _subject: Optional[str] = Depends(_current_subject),
) -> dict:
    """Paged listing of extracted IOCs across analyses (page/page_size, max 200)."""
    flat: list[dict] = []
    for a in _ANALYSES:
        for rec in a.iocs:
            d = rec.model_dump()
            d["evidence_id"] = str(a.evidence_id)
            d["analysis_id"] = str(a.analysis_id)
            flat.append(d)
    total = len(flat)
    start = (page - 1) * page_size
    items = flat[start: start + page_size]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/health")
def health() -> dict:
    """Liveness probe — no auth required."""
    return {"status": "ok"}


def _case_analyses(case_id: str) -> list[AnalyzeResponse]:
    """All stored analyses for one case (Intern-1 persists; this is the demo store)."""
    return [a for a in _ANALYSES if str(a.case_id) == str(case_id)]


@router.get("/by-case/{case_id}/iocs", response_model=dict)
def case_iocs(
    case_id: str,
    level: Optional[str] = Query(default=None),
    _subject: Optional[str] = Depends(_current_subject),
) -> dict:
    """Sprint-2: IOCs for a case — backs GET /cases/{case_id}/iocs on the gateway."""
    items: list[dict] = []
    for a in _case_analyses(case_id):
        for rec in a.iocs:
            if level and rec.risk_level != level:
                continue
            d = rec.model_dump()
            d["evidence_id"] = str(a.evidence_id)
            items.append(d)
    return {"case_id": case_id, "total": len(items), "items": items}


@router.get("/by-case/{case_id}/findings", response_model=dict)
def case_findings(
    case_id: str,
    severity: Optional[str] = Query(default=None),
    _subject: Optional[str] = Depends(_current_subject),
) -> dict:
    """Sprint-2: Threat Findings for a case — backs GET /cases/{case_id}/findings."""
    items: list[dict] = []
    for a in _case_analyses(case_id):
        for f in a.findings:
            if severity and f.get("severity") != severity:
                continue
            items.append(f)
    return {"case_id": case_id, "total": len(items), "items": items}


@router.get("/by-case/{case_id}/summary", response_model=dict)
def case_summary(
    case_id: str,
    _subject: Optional[str] = Depends(_current_subject),
) -> dict:
    """Sprint-2: case rollup for the Case Summary dashboard card."""
    from backend.app.ioc import correlation as _corr

    recs = [rec for a in _case_analyses(case_id) for rec in a.iocs]
    rollup = _corr.case_rollup(recs) if recs else {"ioc_count": 0, "verdict": "normal"}
    return {"case_id": case_id,
            "evidence_count": len(_case_analyses(case_id)), **rollup}
