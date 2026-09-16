# Backend/app/ioc/schemas.py

from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


SourceType = Literal[
    "syslog",
    "auth_log",
    "firewall",
    "pcap_text",
    "email_header",
    "file_text",
    "generic",
]

IOCType = Literal[
    "ip",
    "domain",
    "url",
    "email",
    "md5",
    "sha1",
    "sha256",
    "sha512",
]

RiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

IOCStatus = Literal[
    "new",
    "triaged",
    "benign",
    "malicious",
]


class IOCAnalyzeOptions(BaseModel):
    max_bytes: int = Field(
        default=5242880,
        ge=1,
        le=5242880,
    )

    context_window: int = Field(
        default=80,
        ge=0,
        le=500,
    )

    enable_fallback: bool = True

    use_ai: bool = False


class IOCAnalyzeRequest(BaseModel):
    tenant_id: str
    case_id: str
    evidence_id: str

    text: Optional[str] = None

    source_type: SourceType = "generic"

    options: IOCAnalyzeOptions = Field(
        default_factory=IOCAnalyzeOptions
    )


class IOCRecord(BaseModel):
    type: IOCType

    value_normalized: str = Field(
        min_length=1
    )

    raw_found: str = Field(
        min_length=1
    )

    line_no: Optional[int] = Field(
        default=None,
        ge=1,
    )

    context_snippet: str = ""

    risk_score: int = Field(
        ge=0,
        le=100,
    )

    risk_level: RiskLevel

    reasons: list[str] = Field(
        default_factory=list
    )

    mitre_ids: list[str] = Field(
        default_factory=list
    )

    status: IOCStatus = "new"

    dedupe_key: str = Field(
        min_length=1
    )

    tenant_id: Optional[str] = None

    ai_delta: int = Field(
        default=0,
        ge=-15,
        le=15,
    )

    ai_justification: str = ""

    ai_accepted: bool = False


class AnalyzeResponse(BaseModel):
    analysis_id: UUID

    tenant_id: str

    case_id: str

    evidence_id: str

    source_type: SourceType

    fallback_used: bool = False

    text_bytes: int = Field(
        ge=0
    )

    text_truncated: bool = False

    counts: dict[str, int] = Field(
        default_factory=dict
    )

    iocs: list[IOCRecord] = Field(
        default_factory=list
    )