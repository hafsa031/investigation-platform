-- IOC module migration: per-tenant IOC store
-- Postgres / pg_trgm required for value similarity search.
-- Idempotent-ish: safe to run once per environment.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE IF NOT EXISTS iocs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID        NOT NULL,
  evidence_id   UUID        NOT NULL,
  case_id       UUID,
  type          TEXT        NOT NULL,
  value         TEXT        NOT NULL,
  value_normalized TEXT     NOT NULL,
  raw_found     TEXT,
  context_snippet TEXT,
  dedupe_key    TEXT        NOT NULL,
  risk_score    INTEGER     NOT NULL DEFAULT 0,
  risk_level    TEXT        NOT NULL DEFAULT 'low',
  confidence    DOUBLE PRECISION,
  mitre_ids     TEXT[]      NOT NULL DEFAULT '{}',
  tags          TEXT[]      NOT NULL DEFAULT '{}',
  source        TEXT        NOT NULL DEFAULT 'generic',
  status        TEXT        NOT NULL DEFAULT 'new',
  fallback_used BOOLEAN     NOT NULL DEFAULT FALSE,
  first_seen    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  last_seen     TIMESTAMPTZ  NOT NULL DEFAULT now(),
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT chk_ioc_type CHECK (type IN ('ip','domain','url','email','md5','sha1','sha256','sha512')),
  CONSTRAINT chk_risk_score CHECK (risk_score >= 0 AND risk_score <= 100),
  CONSTRAINT chk_risk_level CHECK (risk_level IN ('low','medium','high','critical')),
  CONSTRAINT chk_status CHECK (status IN ('new','triaged','benign','malicious')),
  CONSTRAINT chk_source CHECK (source IN ('syslog','auth_log','firewall','pcap_text','email_header','file_text','generic')),
  CONSTRAINT chk_value_nonempty CHECK (char_length(value_normalized) > 0),
  CONSTRAINT chk_confidence_range CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),

  CONSTRAINT uq_ioc_evidence UNIQUE (tenant_id, evidence_id, type, value),
  CONSTRAINT uq_ioc_dedupe UNIQUE (tenant_id, dedupe_key)
);

CREATE INDEX IF NOT EXISTS idx_iocs_tenant ON iocs (tenant_id);
CREATE INDEX IF NOT EXISTS idx_iocs_tenant_evidence ON iocs (tenant_id, evidence_id);
CREATE INDEX IF NOT EXISTS idx_iocs_tenant_type ON iocs (tenant_id, type);
CREATE INDEX IF NOT EXISTS idx_iocs_risk ON iocs (tenant_id, risk_level, risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_iocs_status ON iocs (tenant_id, status);
-- trigram index for fuzzy value search (typosquat / contains)
CREATE INDEX IF NOT EXISTS gin_trgm_iocs_value ON iocs USING gin (value_normalized gin_trgm_ops);
CREATE INDEX IF NOT EXISTS gin_iocs_mitre ON iocs USING gin (mitre_ids);
