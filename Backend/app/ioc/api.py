# Backend/app/ioc/api.py

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, HTTPException

from app.ioc.pipeline import analyze
from app.ioc.schemas import AnalyzeResponse, IOCAnalyzeRequest

router = APIRouter(
    prefix="/api/v1/iocs",
    tags=["iocs"],
)

_ANALYSES: list[AnalyzeResponse] = []


def _current_subject(
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header",
        )

    return authorization


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=201,
)
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

    flat: list[dict] = []

    for analysis in _ANALYSES:
        for record in analysis.iocs:
            item = record.model_dump()

            item["evidence_id"] = str(
                analysis.evidence_id
            )

            item["analysis_id"] = str(
                analysis.analysis_id
            )

            item["case_id"] = str(
                analysis.case_id
            )

            flat.append(item)

    total = len(flat)

    start = (page - 1) * page_size

    items = flat[start:start + page_size]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok"
    }