# INTERN-6 Handoff — IOC Module (what was used / data / proof)

## 1. What was used
- Code: `backend/app/ioc/` — `extractor.py` (defang/refang + regex extract),
  `validate.py` (reject version-numbers / UUIDs / 48-hex), `scoring.py`
  (private-cap + phishing-critical), `mitre_map.py` (4 pinned rules),
  `schemas.py` (Pydantic v2, null-text allowed, `fallback_used` flag),
  `export.py` (CSV-injection-safe + XSS escape), `dedupe.py`
  (deterministic tenant `dedupe_key`), `ai_enhance.py` (fail-open rerank).
- Contracts: `contracts/ioc.schema.json` (frozen field list, `additionalProperties: false`).
- DB: `db/migrations_ioc.sql` (`iocs` table, `tenant_id`,
  `UNIQUE(tenant_id,evidence_id,type,value)`, `UNIQUE(tenant_id,dedupe_key)`,
  `gin_trgm` index, CHECK constraints).
- Tests: `tests/test_ioc_all.py` (extractor defang, validate rejections,
  scoring, 4 mitre rules, schemas, fallback, CSV safety, XSS, dedupe determinism).
- Data: `backend/app/ioc/data/allowlist.json` (private CIDRs, benign domains,
  phishing keywords, abused TLDs, empty-file hashes),
  `backend/app/ioc/data/mitre_snapshot.json` (pinned `v19.2-2025-10-24`:
  T1566.002, T1110, T1204, T1071.001).

## 2. Data sources (trusted only)
- MITRE ATT&CK Enterprise — https://attack.mitre.org (technique IDs/tactics)
- CISA AIS + KEV — https://www.cisa.gov (AIS sharing, KEV catalog)
- NIST SP 800-150 (Cyber Threat Information Sharing)
- abuse.ch (URLhaus / ThreatFox / MalwareBazaar feeds)
- MISP threat-sharing platform, OpenCTI knowledge-graph conventions
- Public Suffix List (PSL) — https://publicsuffix.org (domain/TLD parsing)

## 3. Proof (how to verify)
```bash
pytest tests/test_ioc_all.py -v
python3 -c "from backend.app.ioc.schemas import IOCAnalyzeRequest; print('schemas ok')"
python3 -c "import backend.app.ioc as m; print(m.__version__)"
psql -f db/migrations_ioc.sql   # creates iocs table + indexes
python3 -c "import json; json.load(open('contracts/ioc.schema.json')); print('contract ok')"
```

## 4. Safe answers (what Intern-6 must NOT do)
- Never render raw IOC text into HTML without `html_escape()` (XSS).
- Never export CSV without `safe_csv_cell()` (formula injection `=+-@`).
- Never persist without `tenant_id` scoping; dedupe via `dedupe_key` only.
- Never invent MITRE IDs outside the 4-rule pinned snapshot.
- AI rerank stays fail-open (`AI_RERANK_ENABLED=false` default); heuristics win.

## 5. ML answers (rerank policy)
- `ai_enhance.rerank()` validates deltas to ±15, technique IDs to the pinned
  allowlist, and requires justification grounding in context/reasons/IOC.
- Ungrounded or invalid proposals return `accepted=False, delta=0`.
- Disabled by default → heuristic scores stand; no silent score changes.
