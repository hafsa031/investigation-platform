# Jagspire Investigation Platform Frontend

React, TypeScript and Vite frontend for the Jagspire FastAPI investigation platform. The existing dark navy/grey palette has been retained.

## Setup

```bash
npm install
```

Copy `.env.example` to `.env` and set the API base URL if the backend is not running at the default address:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

## Available screens

- Login, account registration and password reset.
- Dashboard with live case/evidence counts and backend/database status.
- Case list, create case and case filtering.
- Case details: evidence upload/download, forensic analysis and saved analysis results, hashes, findings, entities, relationships, manual/extracted timeline events, report records, case editing and deletion.
- Evidence Explorer across the user's cases.
- Account profile and audit history.

The frontend expects the backend CORS configuration to allow the Vite development origin.
