"""One-command demo: heuristic vs AI IOC analysis on synthetic fixtures.

Usage:
    python3 scripts/demo_ioc.py                # offline, heuristic only
    AI_RERANK_ENABLED=true GROQ_API_KEY=... python3 scripts/demo_ioc.py --ai
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.ioc.pipeline import analyze
from backend.app.ioc.schemas import IOCAnalyzeOptions, IOCAnalyzeRequest

FIX = Path(__file__).resolve().parent.parent / "backend" / "app" / "ioc" / "tests" / "fixtures"


def run(fixture: str, source_type: str, use_ai: bool) -> None:
    text = (FIX / fixture).read_text()
    req = IOCAnalyzeRequest(
        tenant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4(),
        text=text, source_type=source_type,  # type: ignore[arg-type]
        options=IOCAnalyzeOptions(use_ai=use_ai))
    r = analyze(req)
    print(f"\n=== {fixture} (use_ai={use_ai}, fallback={r.fallback_used}, truncated={r.text_truncated}) ===")
    print(f"{'TYPE':8} {'VALUE':52} {'SCORE':5} {'LEVEL':8} {'MITRE':10} AI")
    for i in r.iocs:
        final = i.risk_score + (i.ai_delta if i.ai_accepted else 0)
        ai = f"{i.ai_delta:+d} {i.ai_justification[:60]}" if i.ai_accepted else "-"
        print(f"{i.type:8} {i.value_normalized[:52]:52} {i.risk_score:<5} {i.risk_level:8} "
              f"{','.join(i.mitre_ids) or '-':10} {ai} (final={final})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true", help="enable Groq rerank (needs env)")
    args = ap.parse_args()
    run("auth.log", "auth_log", args.ai)
    run("phish.eml", "email_header", args.ai)
    run("doc_with_hashes.txt", "file_text", args.ai)
    print("\nDone. Same input + same code = same output (reproducible).")


if __name__ == "__main__":
    main()
