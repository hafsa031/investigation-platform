"""Mocked tests for groq_rerank: no network, no real key, offline."""
from __future__ import annotations

import io
import json
import os

from backend.app.ioc import ai_enhance as AI
from backend.app.ioc import groq_rerank as G


def _fake_response(payload: dict):
    class Fake:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(payload).encode()
    return Fake()


def test_groq_disabled_fail_open(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(AI, "AI_RERANK_ENABLED", False)
    out = G.groq_rerank_one("http://evil.tk/login", "ctx", ["phishing-keyword:login+20"])
    d = out if isinstance(out, dict) else out.model_dump()
    assert d["delta"] == 0 and d["accepted"] is False


def test_groq_no_key_fail_open(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(AI, "AI_RERANK_ENABLED", True)
    out = G.groq_rerank_one("http://evil.tk/login", "ctx", [])
    d = out if isinstance(out, dict) else out.model_dump()
    assert d["delta"] == 0 and "groq disabled or no key" in d["justification"]


def test_groq_valid_json_accepted_path(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_FAKE_TEST_ONLY")
    monkeypatch.setattr(AI, "AI_RERANK_ENABLED", True)
    body = {"choices": [{"message": {"content":
        '{"delta": 5, "justification": "phishing login page shows credential theft attempt here", '
        '"technique_ids": ["T1566.002"], "confidence": 0.8}'}}]}
    monkeypatch.setattr(G.urllib.request, "urlopen", lambda req, timeout=8.0: _fake_response(body))
    out = G.groq_rerank_one("http://evil.tk/login",
                            "phishing login page shows credential theft attempt here",
                            ["phishing-keyword:login+20"])
    d = out if isinstance(out, dict) else out.model_dump()
    assert -15 <= d["delta"] <= 15 and "ioc" in d
    # key must never leak into output
    assert "FAKE_TEST_ONLY" not in json.dumps(d)


def test_groq_bad_json_fail_open(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_FAKE_TEST_ONLY")
    monkeypatch.setattr(AI, "AI_RERANK_ENABLED", True)
    monkeypatch.setattr(G.urllib.request, "urlopen", lambda req, timeout=8.0: (_ for _ in ()).throw(TimeoutError()))
    out = G.groq_rerank_one("8.8.8.8", "", [])
    d = out if isinstance(out, dict) else out.model_dump()
    assert d["delta"] == 0 and d["accepted"] is False


def test_env_example_has_no_real_key():
    text = open(".env.example").read()
    assert "REPLACE_WITH_YOUR_OWN_KEY" in text
