# SENIOR QA — IOC Module

## Q: What was used?
Pinned heuristic pipeline in `backend/app/ioc/`: defang-aware regex extractor,
false-positive validator, private-capped/phishing-critical scorer, 4-rule MITRE
mapper (`v19.2-2025-10-24`), Pydantic v2 schemas with null-text + fallback flag,
CSV-safe/XSS-safe exporters, deterministic tenant dedupe keys, fail-open AI
rerank. Frozen contract (`contracts/ioc.schema.json`), Postgres migration
(`db/migrations_ioc.sql`), full gate in `tests/test_ioc_all.py`.

## Q: What data?
Only local allowlists/snapshots (`allowlist.json`: private CIDRs, benign
domains, phishing keywords, abused TLDs, empty hashes; `mitre_snapshot.json`:
4 techniques) plus the analyzed tenant evidence text. No live-feed dependency
at runtime. External intelligence (when refreshed offline) comes from trusted
sources: attack.mitre.org, cisa.gov AIS/KEV, NIST SP 800-150 guidance,
abuse.ch feeds, MISP, OpenCTI conventions, PSL.

## Q: What is the proof?
- `pytest tests/test_ioc_all.py -v` — all green (defang, version/UUID/48-hex
  rejection, private-cap + phishing-critical, 4 mitre rules, null-text,
  fallback flag, CSV `=+-@` safety, XSS escaping, dedupe determinism).
- `contracts/ioc.schema.json` parses and forbids extra fields.
- `db/migrations_ioc.sql` applies: both UNIQUEs, `gin_trgm` + mitre GIN
  indexes, CHECKs on type/score/level/status/source.
- Manual: defanged `hxxp://evil[.]tk/login` extracts + scores critical;
  `=cmd` exports as `'=cmd`; `<script>` renders as `&lt;script&gt;`.

## Q: Is it safe?
Yes — by construction: tenant isolation (`tenant_id` on every row + UNIQUEs),
XSS neutralized (`html_escape`), CSV injection neutralized (`safe_csv_cell`
prefix-quote, verified no cell starts with `=+-@`), false positives rejected
(versions/UUIDs/48-hex), private IPs capped (no RFC1918 false-criticals),
MITRE IDs closed-world (4 pinned, no hallucination), AI fail-open (disabled by
default, ±15 clamp, grounding check).

## Q: ML answers?
The only ML/AI surface is `ai_enhance.rerank()`: opt-in via
`AI_RERANK_ENABLED`, deltas clamped to ±15, technique IDs restricted to the 4
pinned, justifications must ground nouns in context/reasons/IOC or the
proposal is rejected with `delta=0`. Heuristics always stand on rejection or
when disabled. No training, no PII exfil, no prompt-injected score changes.

## Trusted sources
- https://attack.mitre.org (ATT&CK IDs/tactics)
- https://www.cisa.gov (AIS sharing; KEV catalog)
- NIST SP 800-150 (threat-info sharing guide)
- https://abuse.ch (URLhaus/ThreatFox/MalwareBazaar)
- MISP (https://www.misp-project.org), OpenCTI (https://www.opencti.io)
- PSL (https://publicsuffix.org)
