# Sprint-2 Handoff — Intern-4 Cyber Security Module (Threat Findings + Correlation)

## What was added on top of the Sprint-1 IOC engine
- `backend/app/ioc/threat_findings.py` — `ThreatFinding{ioc,type,source{case,evidence,source_type,line_no},severity,timestamp,reason,observation}`.
  Severity = deterministic `risk_level` map; accepted AI may promote at most one
  step when final crosses 40/65/85. AI alone can never set severity.
- `backend/app/ioc/correlation.py` — `correlate()` → `shared_iocs` (pivot across
  evidence), `colocated_links` (IP+URL/domain same line), `timeline` (line-ordered),
  `rollup{worst_severity, by_level, verdict}` incl. optional Intern-3 forensic input.
- `pipeline.analyze` Stage 8 emits `findings[] + correlations{}` on every response
  (fail-open: analysis never breaks if these stages error).
- `api.py` case endpoints for Intern-1's gateway to mount behind
  `/cases/{id}/iocs|findings`: `GET /api/v1/iocs/by-case/{id}/{iocs,findings,summary}`.
- Streamlit Investigation View: findings table (severity filter), verdict/severity
  cards, pivot + colocated tables, timeline expander.

## Intern-1 / Intern-3 contracts
- Intern-1: mount `api.router`; persist `findings` per evidence; map gateway
  `/cases/{id}/findings` → `by-case/{id}/findings`. DDL addition: `findings`
  table `(id, tenant_id, case_id, evidence_id, ioc, type, severity, reason, observation, created_at)`.
- Intern-3: send `[{"evidence_id","severity": normal|suspicious|critical,"title","timestamp"}]`
  per evidence → feeds `rollup.verdict` agreement. Absent = tolerated (`[]`).

## Resources used (extraction + building + data)
- Extraction logic studied from: InQuest `iocextract` (defang tables,
  https://github.com/InQuest/iocextract), Floyd Hightower `ioc-finder` (grammars,
  https://github.com/fhightower/ioc-finder), `iocflow` (PSL + allowlist pattern).
- Sharing/export shape follows OASIS STIX 2.1 / CISA AIS (`https://www.cisa.gov/topics/.../automated-indicator-sharing-ais`).
- Technique IDs/tactics from MITRE ATT&CK Enterprise, pinned `v19.2-2025-10-24`
  (`https://attack.mitre.org`, STIX bundle `https://github.com/mitre-attack/attack-stix-data`).
- Domain validity via Mozilla Public Suffix List (`https://publicsuffix.org`).
- Severity practice aligned to CISA KEV / NIST SP 800-150 handling
  (`https://www.cisa.gov/known-exploited-vulnerabilities-catalog`).
- Test data: 100% synthetic, authored locally (RFC5737 + `example.*`); no live
  feeds, no victim data, no keys in repo.

## Verify
`pytest tests/test_ioc_sprint2.py -v` (4) · `pytest tests/ -q` (65 green) ·
`streamlit run streamlit_app.py` → upload `uploads_demo/sample_report.md` → findings + correlation visible.
