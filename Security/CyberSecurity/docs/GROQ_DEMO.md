# Groq Demo Script — 13 Sept (mocked locally, live optional)

## Setup (your shell only; key never in repo)
```bash
cp .env.example .env && chmod 600 .env   # put YOUR rotated key in .env
set -a; source .env; set +a
```

## Demo part 1 — heuristic only (AI off, always works)
```bash
AI_RERANK_ENABLED=false python3 -c "
import uuid
from backend.app.ioc.schemas import IOCAnalyzeRequest
from backend.app.ioc.pipeline import analyze
req = IOCAnalyzeRequest(tenant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4(),
  text=open('backend/app/ioc/tests/fixtures/phish.eml').read(), source_type='email_header')
for i in analyze(req).iocs:
    print(i.type, i.value_normalized, i.risk_score, i.risk_level, i.mitre_ids)"
```
Say: "Deterministic baseline — same input, same score, every row has reasons + line number."

## Demo part 2 — AI on (same evidence)
```bash
AI_RERANK_ENABLED=true GROQ_API_KEY="$GROQ_API_KEY" python3 -c "
import uuid
from backend.app.ioc.schemas import IOCAnalyzeOptions, IOCAnalyzeRequest
from backend.app.ioc.pipeline import analyze
req = IOCAnalyzeRequest(tenant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4(),
  text=open('backend/app/ioc/tests/fixtures/phish.eml').read(), source_type='email_header',
  options=IOCAnalyzeOptions(use_ai=True))
for i in analyze(req).iocs:
    final = i.risk_score + (i.ai_delta if i.ai_accepted else 0)
    print(i.value_normalized, 'heuristic=', i.risk_score, 'ai_delta=', i.ai_delta, 'final=', final, '|', i.ai_justification[:80])"
```
Say: "AI only nudges ±15 with a cited justification. Rejected/timeout/quota → heuristic stands. No new IOCs ever appear."

## Quota guard proof
`GROQ_DAILY_CAP=2` → third IOC shows `ai_skipped: quota`. Free tier is safe.

## Dashboard columns for Intern-2 (add to IOC table)
`value | type | heuristic | AI ± | final | MITRE chip | Why (AI justification tooltip) | snippet+line | raw toggle | CSV export`.
`final = risk_score + ai_delta` when `ai_accepted`, else `risk_score`.
