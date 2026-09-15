# Intern-5 IOC Module

Version: 1.0.0

Extracts Indicators of Compromise (IP, domain, URL, email, MD5/SHA1/SHA256/SHA512)
from unstructured text (syslog, auth_log, firewall, pcap_text, email_header,
file_text, generic).

## Layout

- `backend/app/ioc/__init__.py` — exports `__version__ = "1.0.0"`.
- `backend/app/ioc/schemas.py` — Pydantic v2 models:
  `IOCAnalyzeRequest`, `IOCRecord`, `AnalyzeResponse`.
- `backend/app/ioc/data/allowlist.json` — private CIDRs, loopback,
  benign domains, phishing keywords, abused TLDs, empty-file hashes.
- `backend/app/ioc/data/mitre_snapshot.json` — pinned MITRE snapshot
  `v19.2-2025-10-24` (T1566.002, T1110, T1204, T1071.001).

## Request defaults

- `options.max_bytes = 5242880` (5 MiB cap, truncates with flag)
- `options.context_window = 80`
- `options.enable_fallback = True`

## Quickstart

```python
from backend.app.ioc import __version__
from backend.app.ioc.schemas import IOCAnalyzeRequest
req = IOCAnalyzeRequest(
    tenant_id="00000000-0000-0000-0000-000000000001",
    case_id="00000000-0000-0000-0000-000000000002",
    evidence_id="00000000-0000-0000-0000-000000000003",
    text="Failed login from 203.0.113.10, see http://evil.tk/login",
    source_type="auth_log",
)
```

## Verify

```bash
python3 -c "import backend.app.ioc as m; print(m.__version__)"
python3 -c "from backend.app.ioc.schemas import IOCAnalyzeRequest,IOCRecord,AnalyzeResponse; print('schemas ok')"
```
