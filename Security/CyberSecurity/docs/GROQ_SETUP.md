# Groq AI Rerank — Safe Setup (Intern-5)

## 1. Rotate first
If a key was ever pasted in chat, tickets, screenshots, or code: it is
compromised. Delete it in Groq console → create a fresh key.

## 2. Local setup (your machine only)
```bash
cp .env.example .env
chmod 600 .env
# edit .env: put YOUR key after GROQ_API_KEY=, set AI_RERANK_ENABLED=true
set -a; source .env; set +a
python3 -c "import os; print('key loaded:', bool(os.getenv('GROQ_API_KEY')))"
```

## 3. Guarantees
- `.env` is gitignored (`git check-ignore -v .env`). It can never be pushed.
- Code reads `os.getenv("GROQ_API_KEY")` only — no hardcoded secrets.
- No key in logs: `groq_rerank.py` never prints/returns the key.
- Fail-open: no key, `AI_RERANK_ENABLED=false`, timeout, or 429 →
  `delta=0, accepted=False`, heuristic score stands. Demo-safe.
- Free-tier guard: 8s timeout per IOC; quota errors degrade to heuristic.

## 4. What the AI does / does not do
- DOES: propose delta ±15 + 1-sentence justification citing a heuristic reason.
- DOES NOT: create IOCs, change values, pick techniques outside
  {T1566.002, T1110, T1204, T1071.001}. Violations are rejected by Pydantic.
