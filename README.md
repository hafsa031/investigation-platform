# Jagspire Investigation Platform

An investigation and digital-evidence management platform designed to help investigators organize cases, securely manage evidence, perform forensic analysis, build investigation timelines and entity relationships, and maintain audit records.

## Overview

Jagspire provides a web-based investigator dashboard backed by a FastAPI REST API and PostgreSQL database.

The platform supports:

- User registration and authentication
- Case creation and management
- Evidence upload, storage and download
- Evidence hashing and forensic analysis
- Forensic findings associated with evidence
- Investigation entities and relationships
- Timeline events and timeline items
- Investigation report records
- User audit logs
- API and database health checks

## Project Structure

```text
investigation-platform/
├── Backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── security.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── cases.py
│   │   │   ├── evidence.py
│   │   │   ├── entities.py
│   │   │   ├── events.py
│   │   │   ├── reports.py
│   │   │   └── audit.py
│   │   ├── schemas/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── main.py
│   │   └── models.py
│   ├── requirements.txt
│   └── README.md
│
├── Frontend/
│   └── investigator-dashboard/
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   ├── services/
│       │   └── types/
│       ├── package.json
│       └── vite.config.ts
│
├── Forensic/
│   ├── run_engine.py
│   └── ...
│
└── README.md
```

## Technology Stack

### Frontend

- React 19
- TypeScript
- Vite
- React Router
- Axios
- ESLint

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT authentication
- Python Multipart
- Pillow
- python-docx
- openpyxl
- python-pptx
- pefile
- olefile

### Storage

Evidence files are stored on the backend filesystem using the configured evidence storage directory. Metadata and investigation records are stored in PostgreSQL.

## Core Features

### Authentication

The API provides:

- User registration
- Login using username/password
- JWT-based authentication
- Current-user information
- Password-reset flow

Protected API requests use a bearer token:

```http
Authorization: Bearer <access_token>
```

### Case Management

Investigators can:

- Create cases
- List cases
- View case details
- Update case status
- Delete cases
- View case statistics
- Retrieve case findings

Supported case statuses include:

- `Open`
- `Under Investigation`
- `Closed`

### Evidence Management

Evidence can be uploaded and associated with a case.

Each evidence record can contain:

- Filename
- MIME type
- File size
- Description
- Acquisition source
- Storage location
- Upload information
- Cryptographic hashes

Evidence endpoints also expose forensic analysis and stored analysis results.

### Forensic Analysis

The evidence analysis workflow is integrated with the repository's forensic processing component.

The forensic processing/reporting flow can extract information such as:

- File identification
- File-system metadata
- Cryptographic hashes
- EXIF metadata
- Camera/capture information
- GPS information where available
- Processing errors
- Timeline events

The `Forensic/run_engine.py` utility can also process an individual file and print or save a readable evidence-processing report.

Example:

```bash
py run_engine.py "<file path>"
```

Or:

```bash
py run_engine.py "<file path>" report.txt
```

### Investigation Graph

The platform maintains entities and relationships for a case.

Example entity types can include:

- IP
- Domain
- Person
- Other investigation-relevant entities

Relationships contain a relationship type and confidence value.

### Timeline

Investigators can create and retrieve:

- Investigation events
- Timeline items
- Event timestamps
- Source evidence references
- Event descriptions
- Timezone information

Forensic analysis can also generate timeline events from processed evidence.

### Reports

The backend supports case report records containing:

- Report title
- Report type
- Summary
- Storage key
- Status
- Creation timestamp

### Audit Logs

Authenticated users can create and retrieve their audit records.

Audit entries can record:

- Action
- Resource type
- Resource ID
- Additional details
- Timestamp
- User

## Getting Started

### Prerequisites

Install:

- Python 3.11 or 3.12
- Node.js and npm
- PostgreSQL

The backend README recommends Python 3.11 or 3.12 because some dependencies include native components.

---

## 1. Configure PostgreSQL

Create a PostgreSQL database for the application.

Then configure the backend environment with the database connection string and a strong secret key.

Do not commit real credentials or secrets to source control.

The backend configuration should provide values for the application's project settings, secret key, database URL, CORS configuration and evidence storage location.

---

## 2. Start the Backend

Open a terminal in:

```bash
cd Backend
```

Create a virtual environment:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 3. Start the Frontend

Open another terminal:

```bash
cd Frontend/investigator-dashboard
```

Install dependencies:

```bash
npm install
```

Configure the API URL using the frontend environment configuration.

For a local backend, the API base URL should point to:

```text
http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

The Vite development server will print the local frontend URL in the terminal.

---

## 4. Build the Frontend

To create a production build:

```bash
npm run build
```

To preview the production build:

```bash
npm run preview
```

Run linting with:

```bash
npm run lint
```

## API Overview

The backend exposes the following major API areas:

| Area | Prefix | Purpose |
|---|---|---|
| Authentication | `/auth` | Registration, login and account authentication |
| Cases | `/cases` | Case management and case statistics |
| Evidence | `/evidence` | Upload, retrieve, download and analyze evidence |
| Investigation Graph | `/graph` | Entities and relationships |
| Timeline | `/timeline` | Events and timeline items |
| Reports | `/reports` | Case report records |
| Audit | `/audit` | User audit logs |
| Health | `/` and `/health/db` | API and database health |

The complete endpoint definitions can be explored through FastAPI's Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

## Typical Investigation Workflow

```text
        ┌──────────────────┐
        │     Login        │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │   Create Case    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Upload Evidence  │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Hash / Analyze   │
        │     Evidence     │
        └────────┬─────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
┌───────────────┐   ┌────────────────┐
│   Findings    │   │ Timeline Events│
└───────┬───────┘   └───────┬────────┘
        │                    │
        └─────────┬──────────┘
                  ▼
        ┌──────────────────┐
        │ Entities / Graph │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Investigation    │
        │     Report       │
        └──────────────────┘
```

## Database Model

The backend defines models for the core investigation data, including:

- Users
- Cases
- Evidence
- Evidence hashes
- Events
- Timeline events
- Entities
- Relationships
- Reports
- Audit logs
- Forensic analysis results

The application initializes missing SQLAlchemy tables during startup. Existing schema changes should be handled with an appropriate migration strategy before production deployment.
