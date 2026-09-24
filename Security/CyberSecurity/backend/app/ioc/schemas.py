"""Pydantic v2 schemas for Intern-5 IOC module."""

from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

SourceType = Literal[
    "syslog", "auth_log", "firewall", "pcap_text", "email_header", "file_text", "generic"
]
IOCType = Literal["ip", "domain", "url", "email", "md5", "sha1", "sha256", "sha512"]
RiskLevel = Literal["low", "medium", "high", "critical"]
IOCStatus = Literal["new", "triaged", "benign", "malicious"]


class IOCAnalyzeOptions(BaseModel):
    max_bytes: int = Field(default=5242880, ge=1, le=5242880, description="Max text bytes to analyze (server-clamped 5MB)")
    context_window: int = Field(default=80, ge=0, le=500, description="Chars of context around match")
    enable_fallback: bool = Field(default=True, description="Allow regex fallback extraction")
    use_ai: bool = Field(default=False, description="Opt-in Groq rerank (top-N, quota-guarded, fail-open)")


class IOCAnalyzeRequest(BaseModel):
    tenant_id: UUID
    case_id: UUID
    evidence_id: UUID
    text: Optional[str] = Field(default=None, description="Raw text to extract IOCs from")
    source_type: SourceType = Field(default="generic")
    options: IOCAnalyzeOptions = Field(default_factory=IOCAnalyzeOptions)


class IOCRecord(BaseModel):
    type: IOCType
    value_normalized: str = Field(min_length=1)
    raw_found: str = Field(min_length=1)
    line_no: Optional[int] = Field(default=None, ge=1)
    context_snippet: str = Field(default="")
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    reasons: list[str] = Field(default_factory=list)
    mitre_ids: list[str] = Field(default_factory=list)
    status: IOCStatus = Field(default="new")
    dedupe_key: str = Field(min_length=1)
    tenant_id: Optional[UUID] = Field(default=None, description="Inherited from AnalyzeResponse; set on persist")
    ai_delta: int = Field(default=0, ge=-15, le=15, description="Groq-proposed adjustment (0 when AI off/rejected)")
    ai_justification: str = Field(default="", description="One-sentence AI justification citing a heuristic reason")
    ai_accepted: bool = Field(default=False, description="True only when AI output passed validation")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AnalyzeResponse(BaseModel):
    analysis_id: UUID
    tenant_id: UUID
    case_id: UUID
    evidence_id: UUID
    source_type: SourceType
    fallback_used: bool = Field(default=False)
    text_bytes: int = Field(ge=0)
    text_truncated: bool = Field(default=False)
    counts: dict[str, int] = Field(default_factory=dict)
    iocs: list[IOCRecord] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list, description="Sprint-2 ThreatFinding dicts (ioc/type/source/severity/timestamp/reason)")
    correlations: dict = Field(default_factory=dict, description="Sprint-2 correlate() output")
