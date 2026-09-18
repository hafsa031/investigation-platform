# Case Investigation Workflow — Intern-4 Runbook (Sprint-2)

## End-to-end flow (actually runs)
```bash
python3 scripts/e2e_case.py           # sample -> forensic -> IOC -> findings -> correlation -> summary
python3 scripts/e2e_case.py --send    # + POST findings/iocs to BACKEND_URL (fail-open)
pytest tests/test_ioc_caseflow.py -v  # adapter + sender + e2e tests
streamlit run streamlit_app.py        # Investigation View: findings + correlation + verdict
```

## How modules connect (no disconnected parts)
- `Forensic/forensic_engine.py::process_evidence()` (team repo, real, 478 lines)
  → `backend/app/ioc/forensic_adapter.py` (text for IOC + forensic severity inputs)
  → `pipeline.analyze` (IOCs + `findings[]` + `correlations{}`)
  → `sender.send_case_results` → Intern-1 `POST /cases/{id}/{findings,iocs}`
  → dashboard (Streamlit now; React `CaseDetails` later via same JSON).

## Honest gaps flagged (not hidden)
- Team `Backend/app/routers/analysis.py` returns hardcoded statuses — Intern-1
  must replace with real pipeline calls in this sprint.
- Team `Backend` cases/evidence are in-memory stubs — Intern-1/6 must persist.
- `Ai/`, `Database/`, `Tests/` folders are empty (Intern 6/7 absent) — our `db/`,
  `contracts/`, `tests/` cover the security slice only.
- AI rerank is opt-in (`use_ai` + `GROQ_API_KEY`); detection is deterministic.

## Resources (for mentor questions — what/where/data)
- Defang/extraction logic studied from InQuest `iocextract`
  (https://github.com/InQuest/iocextract) and `ioc-finder`
  (https://github.com/fhightower/ioc-finder); re-implemented, not copied (GPL/LGPL).
- ATT&CK IDs from MITRE ATT&CK Enterprise v19.2 (https://attack.mitre.org),
  STIX bundle (https://github.com/mitre-attack/attack-stix-data).
- Sharing format: OASIS STIX 2.1 / CISA AIS
  (https://www.cisa.gov/topics/cyber-threats-and-advisories/information-sharing/automated-indicator-sharing-ais).
- Domain validity: Mozilla PSL (https://publicsuffix.org).
- Severity practice: CISA KEV (https://www.cisa.gov/known-exploited-vulnerabilities-catalog),
  NIST SP 800-150.
- Test/evidence data: 100% synthetic, authored in-repo
  (`backend/app/ioc/tests/fixtures/`); forensic behavior verified against the
  real team engine output shape. No live feeds, no victim data, no keys in repo.
