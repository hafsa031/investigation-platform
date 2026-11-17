# Jagspire Investigation Platform Backend

## Setup

Use Python 3.11 or 3.12 (the project dependencies include native packages that may not yet support the newest Python releases).

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set a strong `SECRET_KEY` and your PostgreSQL `DATABASE_URL`. Do not commit or share `.env`.

Run from this `Backend` directory:

```bash
uvicorn app.main:app --reload
```

API documentation is available at `http://127.0.0.1:8000/docs`.

## API areas exposed to the frontend

- Authentication: register, login, current user, forgot password and reset password.
- Cases: create, list, read, update, delete, stats and forensic findings.
- Evidence: upload, list by case, read, download, analyze, retrieve saved analysis and evidence hashes.
- Investigation graph: create/list entities and relationships.
- Timeline: create/list events and timeline items.
- Reports: create and list case report records.
- Audit: create and list the authenticated user's audit entries.
- Health: API and database health checks.

Evidence files are stored on the backend filesystem under `EVIDENCE_STORAGE_DIR`, not inside PostgreSQL. In production, use persistent storage and a controlled access policy.

The forgot-password endpoint currently returns a reset token in its response for demonstration/testing. Replace this with an email delivery flow before production use.
