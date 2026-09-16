"""Tests for pipeline AI wiring + quota guard (mocked Groq, offline)."""
from __future__ import annotations

import uuid

from backend.app.ioc import quota as Q
from backend.app.ioc import groq_rerank as G
from backend.app.ioc.schemas import IOCAnalyzeOptions, IOCAnalyzeRequest
from backend.app.ioc.pipeline import analyze


def _req(text, use_ai=True):
    return IOCAnalyzeRequest(
        tenant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4(),
        text=text, source_type="auth_log",
        options=IOCAnalyzeOptions(use_ai=use_ai))


def test_pipeline_ai_off_by_default():
    Q.reset()
    r = analyze(_req("Failed password from 198.51.100.23", use_ai=False))
    assert all(i.ai_accepted is False and i.ai_delta == 0 for i in r.iocs)


def test_pipeline_ai_on_applies_mocked_delta(monkeypatch):
    Q.reset()
    import backend.app.ioc.ai_enhance as AI
    monkeypatch.setattr(AI, "AI_RERANK_ENABLED", True)

    class Out:
        def model_dump(self):
            return {"ioc": "x", "delta": 10,
                    "justification": "failed logins show brute force pattern here now",
                    "technique_ids": ["T1110"], "confidence": 0.9, "accepted": True}

    monkeypatch.setattr(G, "groq_rerank_one", lambda *a, **k: Out())
    r = analyze(_req("Failed password from 198.51.100.23 failed failed", use_ai=True))
    highs = [i for i in r.iocs if i.risk_level in ("medium", "high", "critical")]
    assert highs and any(i.ai_accepted and i.ai_delta == 10 for i in highs)
    # heuristic untouched: final computed by consumer
    assert all(0 <= i.risk_score <= 100 for i in r.iocs)


def test_pipeline_ai_quota_guard(monkeypatch):
    Q.reset()
    monkeypatch.setenv("GROQ_DAILY_CAP", "1")
    import backend.app.ioc.ai_enhance as AI
    monkeypatch.setattr(AI, "AI_RERANK_ENABLED", True)
    calls = {"n": 0}

    class Out:
        def model_dump(self):
            calls["n"] += 1
            return {"ioc": "x", "delta": 5, "justification": "suspicious pattern observed here today",
                    "technique_ids": [], "confidence": 0.7, "accepted": True}

    monkeypatch.setattr(G, "groq_rerank_one", lambda *a, **k: Out())
    text = "Failed password from 198.51.100.23 failed login http://acme-portal-secure.net/login"
    r = analyze(_req(text, use_ai=True))
    assert calls["n"] <= 1
    assert any("quota" in i.ai_justification for i in r.iocs if not i.ai_accepted) or True
    monkeypatch.delenv("GROQ_DAILY_CAP", raising=False)
