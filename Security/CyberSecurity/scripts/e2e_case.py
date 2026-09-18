"""Sprint-2 E2E (Intern-4): sample evidence -> forensic -> IOC -> findings -> correlation -> case summary.

Usage:
    python3 scripts/e2e_case.py [--send]   # --send also POSTs to BACKEND_URL (fail-open)

Flow mirrors the sprint board: Hash+Metadata (forensic engine) -> IOC
extraction (security module) -> correlation -> Case Summary. All sample data
is synthetic (backend/app/ioc/tests/fixtures/testdata/).
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EVIDENCE = [  # (fixture file, source_type) — approved sample evidence only
    ("testdata/auth_ssh_bruteforce.log", "auth_log"),
    ("testdata/phish_credential_harvest.eml", "email_header"),
    ("testdata/malware_drop_report.txt", "file_text"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="POST results to BACKEND_URL")
    args = ap.parse_args()

    from backend.app.ioc import correlation as C
    from backend.app.ioc import forensic_adapter as FA
    from backend.app.ioc import threat_findings as TF
    from backend.app.ioc.pipeline import analyze
    from backend.app.ioc.schemas import IOCAnalyzeRequest

    fix = Path("backend/app/ioc/tests/fixtures")
    process = FA.load_engine()  # real team engine when FORENSIC_ENGINE_PATH resolves
    print(f"forensic engine: {'real process_evidence()' if process else 'adapter-only (engine not on path)'}")

    case_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    all_recs, all_forensic, all_sent = [], [], {}
    for fname, stype in EVIDENCE:
        path = fix / fname
        ev_id = uuid.uuid4()
        eng_result = None
        if process is not None:
            try:
                eng_result = process(str(path), case_id=str(case_id), evidence_id=str(ev_id))
            except Exception as e:
                print(f"engine failed on {fname}: {e} — continuing with raw text")
        if eng_result is not None:
            text = FA.evidence_text(eng_result) or path.read_text()
            forensic = FA.forensic_inputs(eng_result, str(ev_id))
        else:
            text, forensic = path.read_text(), []
        # SHA-256 of the sample file = chain-of-custody anchor for the demo
        import hashlib
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        resp = analyze(IOCAnalyzeRequest(tenant_id=tenant_id, case_id=case_id,
                                         evidence_id=ev_id, text=text, source_type=stype))  # type: ignore[arg-type]
        all_recs.extend(resp.iocs)
        all_forensic.extend(forensic)
        if args.send:
            from backend.app.ioc import sender as S
            all_sent[str(ev_id)] = S.send_case_results(
                str(case_id), [f.model_dump(mode="json") for f in
                               TF.build_findings(resp.iocs, case_id, ev_id, stype)],
                [r.model_dump(mode="json") for r in resp.iocs])
        print(f"{fname}: sha256={sha[:16]}… iocs={len(resp.iocs)} "
              f"forensic={[f['severity'] + ':' + f['title'] for f in forensic]}")

    corr = C.correlate(all_recs, all_forensic)
    summary = {"case_id": str(case_id), "evidence": [f[0] for f in EVIDENCE],
               "rollup": corr["rollup"], "shared_pivots": corr["shared_iocs"],
               "backend_send": all_sent or "skipped (--send not passed)"}
    print("\n=== CASE SUMMARY ===")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
