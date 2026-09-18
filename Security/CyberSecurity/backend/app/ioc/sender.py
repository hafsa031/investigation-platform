"""Sprint-2 (Intern-4): send Threat Findings + IOCs to the Backend gateway.

Targets Intern-1's Sprint-2 endpoints (team repo ``Backend/app/routers``):
  POST /cases/{case_id}/findings   (threat findings list)
  POST /cases/{case_id}/iocs       (ioc records list)

Fail-open by design: unreachable backend -> {"sent": False, "reason": ...},
logged, pipeline results are still returned and demoable. Base URL from
``BACKEND_URL`` env (default http://localhost:8000). No auth in Sprint-2;
Intern-1 adds JWT (pass ``BACKEND_TOKEN`` to send as Bearer when ready).
"""
from __future__ import annotations

import json
import os
import urllib.request


def _post(url: str, payload: dict, timeout_s: float = 8.0) -> dict:
    """POST JSON with Bearer token only if BACKEND_TOKEN is set. Critical: the
    token/key is read from env and never logged or stored."""
    token = os.getenv("BACKEND_TOKEN", "")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read().decode()[:10_000]
        return {"sent": True, "status": resp.status, "response": body}


def send_case_results(case_id: str, findings: list[dict], iocs: list[dict]) -> dict:
    """Send one evidence analysis to the backend. Returns per-endpoint status."""
    base = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    out: dict = {"case_id": case_id, "findings": None, "iocs": None}
    for key, suffix, payload in (
        ("findings", f"/cases/{case_id}/findings", {"case_id": case_id, "findings": findings}),
        ("iocs", f"/cases/{case_id}/iocs", {"case_id": case_id, "iocs": iocs}),
    ):
        try:
            out[key] = _post(base + suffix, payload)
        except Exception as e:  # fail-open: backend down must not lose local results
            out[key] = {"sent": False, "reason": f"{type(e).__name__}: {e}"[:200]}
    return out
