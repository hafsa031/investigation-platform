"""AI-assisted score reranking with strict validation and grounding.

Default is fail-open to heuristic: unless ``AI_RERANK_ENABLED`` is True,
:func:`rerank` returns zero deltas so heuristic scores stand.
"""

from __future__ import annotations

import os
import re

from pydantic import BaseModel, Field, field_validator

AI_RERANK_ENABLED: bool = os.getenv("AI_RERANK_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

ALLOWED_TECHNIQUE_IDS = frozenset({"T1566.002", "T1110", "T1204", "T1071.001"})

_STOPWORDS = frozenset(
    {
        "this",
        "that",
        "with",
        "from",
        "have",
        "has",
        "were",
        "was",
        "are",
        "the",
        "and",
        "for",
        "because",
        "since",
        "while",
        "during",
        "observed",
        "shows",
        "show",
        "indicates",
        "suggests",
        "very",
        "more",
        "most",
        "high",
        "low",
        "medium",
    }
)

_WORD_RE = re.compile(r"[a-zA-Z]{4,}")


class AIRerankInput(BaseModel):
    """Single AI-proposed score adjustment."""

    ioc: str = Field(..., min_length=1)
    delta: int = Field(..., ge=-15, le=15)
    justification: str = Field(..., min_length=20)
    technique_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("technique_ids")
    @classmethod
    def _check_techniques(cls, v: list[str]) -> list[str]:
        bad = [t for t in v if t not in ALLOWED_TECHNIQUE_IDS]
        if bad:
            raise ValueError(f"technique_ids must be subset of {sorted(ALLOWED_TECHNIQUE_IDS)}, got {bad}")
        return v


class AIRerankOutput(BaseModel):
    """Validated rerank result for one IOC."""

    ioc: str
    delta: int = Field(..., ge=-15, le=15)
    justification: str = ""
    technique_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    accepted: bool = False
    reject_reason: str | None = None


def _candidate_nouns(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "") if w.lower() not in _STOPWORDS]


def _grounding_ok(justification: str, context: str, reasons: list[str], ioc: str) -> tuple[bool, str | None]:
    """Nouns in justification must appear in context, reasons, or the IOC itself."""
    nouns = _candidate_nouns(justification)
    if not nouns:
        return False, "ungrounded: no checkable nouns in justification"
    haystack = f"{context or ''} {' '.join(reasons or [])} {ioc or ''}".lower()
    missing = [n for n in nouns if n not in haystack]
    if missing:
        return False, f"ungrounded nouns not in context/reasons: {missing}"
    return True, None


def _heuristic_fallback(proposals: list[AIRerankInput]) -> list[AIRerankOutput]:
    return [
        AIRerankOutput(
            ioc=p.ioc,
            delta=0,
            justification=p.justification,
            technique_ids=list(p.technique_ids),
            confidence=0.0,
            accepted=False,
            reject_reason="ai_rerank_disabled: fail-open to heuristic",
        )
        for p in proposals
    ]


def rerank(
    iocs: list[AIRerankInput | dict],
    context: str = "",
    reasons_by_ioc: dict[str, list[str]] | None = None,
) -> list[AIRerankOutput]:
    """Validate AI-proposed deltas with grounding check.

    Args:
        iocs: List of :class:`AIRerankInput` (or equivalent dicts) with
            ``ioc/delta/justification/technique_ids/confidence``.
        context: Shared free-text context used for grounding.
        reasons_by_ioc: Optional per-IOC reason strings (e.g. from
            :func:`mitre_map.map_ioc`) added to the grounding haystack.

    Returns:
        List of :class:`AIRerankOutput`. Invalid or ungrounded proposals
        are returned with ``accepted=False`` and ``delta=0`` (fail-open).
        When ``AI_RERANK_ENABLED`` is False, all deltas are forced to 0.
    """
    reasons_by_ioc = reasons_by_ioc or {}
    validated: list[AIRerankInput] = []
    rejected: dict[str, str] = {}  # ioc -> pydantic error (first occurrence)

    for raw in iocs:
        try:
            prop = raw if isinstance(raw, AIRerankInput) else AIRerankInput.model_validate(raw)
            validated.append(prop)
        except Exception as exc:  # pydantic ValidationError -> reject, don't raise
            ioc_name = raw.get("ioc", "?") if isinstance(raw, dict) else getattr(raw, "ioc", "?")
            rejected.setdefault(
                str(ioc_name),
                f"validation failed: {exc}",
            )

    if not AI_RERANK_ENABLED:
        out = _heuristic_fallback(validated)
        for ioc_name, err in rejected.items():
            out.append(
                AIRerankOutput(
                    ioc=ioc_name,
                    delta=0,
                    confidence=0.0,
                    accepted=False,
                    reject_reason=err,
                )
            )
        return out

    out: list[AIRerankOutput] = []
    for prop in validated:
        reasons = list(reasons_by_ioc.get(prop.ioc, []) or [])
        ok, err = _grounding_ok(prop.justification, context, reasons, prop.ioc)
        if not ok:
            out.append(
                AIRerankOutput(
                    ioc=prop.ioc,
                    delta=0,
                    justification=prop.justification,
                    technique_ids=list(prop.technique_ids),
                    confidence=0.0,
                    accepted=False,
                    reject_reason=err,
                )
            )
        else:
            out.append(
                AIRerankOutput(
                    ioc=prop.ioc,
                    delta=prop.delta,
                    justification=prop.justification,
                    technique_ids=list(prop.technique_ids),
                    confidence=prop.confidence,
                    accepted=True,
                    reject_reason=None,
                )
            )
    for ioc_name, err in rejected.items():
        out.append(
            AIRerankOutput(
                ioc=ioc_name,
                delta=0,
                confidence=0.0,
                accepted=False,
                reject_reason=err,
            )
        )
    return out
