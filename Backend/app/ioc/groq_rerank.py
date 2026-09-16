"""Groq-backed AI rerank for the IOC module (optional, fail-open).

Safety rules (do NOT break these):
- API key is read ONLY from the ``GROQ_API_KEY`` environment variable.
- Never hardcode, log, or return the key. Never commit ``.env``.
- No network call happens unless BOTH ``AI_RERANK_ENABLED=true`` AND
  ``GROQ_API_KEY`` is set. Otherwise returns zero-delta (heuristic stands).
- Groq output is validated through :mod:`backend.app.ioc.ai_enhance`
  (delta ±15, allowed techniques, grounded justification). Invalid output
  is discarded, heuristic score is kept.

Setup (on your own machine, never paste the key in chat/tickets)::

    export GROQ_API_KEY="gsk_..."        # secret, stays in your shell
    export AI_RERANK_ENABLED=true
    export GROQ_MODEL="llama-3.3-70b-versatile"   # free-tier model
"""

from __future__ import annotations

import json
import os
import urllib.request

from app.ioc import ai_enhance as AI

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
_TIMEOUT_S = 8.0


def _prompt(ioc: str, context: str, reasons: list[str]) -> str:
    return (
        "You are a SOC assistant. Given ONE indicator of compromise, propose a score "
        "adjustment delta in [-15, 15] plus a one-sentence justification.\n"
        "Rules: never invent new IOC values; cite at least one heuristic reason; "
        "technique_ids must be a subset of [T1566.002, T1110, T1204, T1071.001].\n"
        f"IOC: {ioc}\nContext: {context[:800]}\nHeuristic reasons: {reasons}\n"
        'Reply ONLY as JSON: {"delta": int, "justification": str, '
        '"technique_ids": [...], "confidence": float}.'
    )


def groq_rerank_one(ioc: str, context: str = "", reasons: list[str] | None = None) -> AI.AIRerankOutput:
    """Rerank a single IOC via Groq; fail-open to zero delta on any problem."""
    reasons = reasons or []
    disabled = AI.AIRerankOutput(ioc=ioc, delta=0, justification="ai_skipped: groq disabled or no key",
                                 technique_ids=[], confidence=0.0, accepted=False)
    if not AI.AI_RERANK_ENABLED:
        return disabled
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return disabled
    try:
        payload = json.dumps({
            "model": GROQ_MODEL,
            "temperature": 0,
            "messages": [{"role": "user", "content": _prompt(ioc, context, reasons)}],
        }).encode()
        req = urllib.request.Request(
            GROQ_API_URL, data=payload,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"]["content"]
        start, end = text.find("{"), text.rfind("}") + 1
        parsed = json.loads(text[start:end])
        outs = AI.rerank([{"ioc": ioc, "delta": int(parsed.get("delta", 0)),
                           "justification": str(parsed.get("justification", "")),
                           "technique_ids": list(parsed.get("technique_ids", [])),
                           "confidence": float(parsed.get("confidence", 0.0))}],
                         context, {ioc: reasons})
        return outs[0]
    except Exception:
        return disabled
