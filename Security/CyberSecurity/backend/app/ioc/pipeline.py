"""IOC analysis pipeline: extractor -> normalize -> validate -> allowlist -> scoring -> mitre_map.

All sibling imports are defensive (try/except) so this module works even if
some sibling module is missing, falling back to naive local implementations.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from backend.app.ioc.schemas import AnalyzeResponse, IOCAnalyzeRequest, IOCRecord

# ---------------------------------------------------------------------------
# Defensive sibling imports — fall back to None when module/function missing.
# ---------------------------------------------------------------------------

_extractor_fn = None
_normalize_fn = None
_validate_fn = None
_allowlist_fn = None
_score_fn = None
_mitre_fn = None

try:  # extractor (real fn: extract_all(text) -> [{type,raw,start,end}])
    try:
        from backend.app.ioc.extractor import extract_all as _extract_all  # type: ignore
    except Exception:
        from .extractor import extract_all as _extract_all  # type: ignore
    _extractor_fn = _extract_all
except Exception:
    _extractor_fn = None

try:  # normalize (real fn: normalize(value, ioc_type))
    try:
        from backend.app.ioc.normalize import normalize as _normalize_real  # type: ignore
    except Exception:
        from .normalize import normalize as _normalize_real  # type: ignore

    def _normalize_fn(ioc_type: str, raw: str) -> str:  # type: ignore[misc]
        return str(_normalize_real(raw, ioc_type))
except Exception:
    _normalize_fn = None

try:  # validate (real fns: is_valid_ip/domain/email/hash in validate.py)
    try:
        from backend.app.ioc import validate as _validate_mod  # type: ignore
    except Exception:
        from . import validate as _validate_mod  # type: ignore

    def _validate_fn(ioc_type: str, value: str) -> bool:  # type: ignore[misc]
        t = (ioc_type or "").lower()
        if t == "ip":
            return bool(_validate_mod.is_valid_ip(value))
        if t == "domain":
            return bool(_validate_mod.is_valid_domain(value))
        if t == "email":
            return bool(_validate_mod.is_valid_email(value))
        if t in ("md5", "sha1", "sha256", "sha512"):
            return bool(_validate_mod.is_valid_hash(value))
        if t == "url":
            try:
                host = urlparse(value).hostname or ""
                return bool(_validate_mod.is_valid_domain(host) or _validate_mod.is_valid_ip(host))
            except Exception:
                return False
        return False
except Exception:
    _validate_fn = None

try:  # allowlist (real fn: validate.is_allowlisted(value, allowlist=None))
    try:
        from backend.app.ioc.validate import is_allowlisted as _allowlisted_real  # type: ignore
    except Exception:
        from .validate import is_allowlisted as _allowlisted_real  # type: ignore

    def _allowlist_fn(ioc_type: str, value: str) -> bool:  # type: ignore[misc]
        try:
            return bool(_allowlisted_real(value, None))
        except TypeError:
            return bool(_allowlisted_real(value))
except Exception:
    _allowlist_fn = None

try:  # scoring
    try:
        from backend.app.ioc.scoring import score_ioc as _score_fn  # type: ignore
    except Exception:
        from .scoring import score_ioc as _score_fn  # type: ignore
except Exception:
    _score_fn = None

try:  # mitre_map (exists in-repo)
    try:
        from backend.app.ioc.mitre_map import map_ioc as _mitre_fn  # type: ignore
    except Exception:
        from .mitre_map import map_ioc as _mitre_fn  # type: ignore
except Exception:
    _mitre_fn = None


# ---------------------------------------------------------------------------
# Naive fallbacks
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"\b(?:https?|hxxps?)://[^\s'\"<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HEX_RE = re.compile(r"\b[0-9a-fA-F]{32,128}\b")
_DOMAIN_RE = re.compile(r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")

_TRAILING_PUNCT = ".,;:)]}'\"!?"


def _naive_extract(text: str) -> list[dict]:
    """Return list of {type, raw, start, end} using regexes.

    Order matters: urls/emails first (masked), then ip/hash, then domains.
    """
    out: list[dict] = []
    masked = list(text)

    def _mask(s: int, e: int) -> None:
        for i in range(s, e):
            if masked[i] != "\n":
                masked[i] = " "

    def _masked_text() -> str:
        return "".join(masked)

    # URLs (incl. defanged hxxp)
    for m in _URL_RE.finditer(text):
        raw = m.group(0).rstrip(_TRAILING_PUNCT)
        e = m.start() + len(raw)
        out.append({"type": "url", "raw": raw, "start": m.start(), "end": e})
        _mask(m.start(), e)
    # Emails
    mt = _masked_text()
    for m in _EMAIL_RE.finditer(mt):
        raw = m.group(0)
        out.append({"type": "email", "raw": raw, "start": m.start(), "end": m.end()})
        _mask(m.start(), m.end())
    # IPs
    mt = _masked_text()
    for m in _IP_RE.finditer(mt):
        out.append({"type": "ip", "raw": m.group(0), "start": m.start(), "end": m.end()})
        _mask(m.start(), m.end())
    # Hashes (32..128 hex; classify by length, keep even invalid lens for validate)
    mt = _masked_text()
    for m in _HEX_RE.finditer(mt):
        raw = m.group(0)
        n = len(raw)
        if n == 32:
            t = "md5"
        elif n == 40:
            t = "sha1"
        elif n == 64:
            t = "sha256"
        elif n == 128:
            t = "sha512"
        else:
            t = "sha256"  # placeholder type so validate can reject 48-char etc.
        out.append({"type": t, "raw": raw, "start": m.start(), "end": m.end()})
        _mask(m.start(), m.end())
    # Domains (residual)
    mt = _masked_text()
    for m in _DOMAIN_RE.finditer(mt):
        raw = m.group(0).rstrip(_TRAILING_PUNCT)
        if not raw or "." not in raw:
            continue
        # skip pure-numeric dotted (already handled as IP attempts)
        out.append({"type": "domain", "raw": raw, "start": m.start(), "end": m.start() + len(raw)})
    out.sort(key=lambda d: d["start"])
    return out


def _naive_normalize(ioc_type: str, raw: str) -> str:
    v = (raw or "").strip().strip(_TRAILING_PUNCT)
    if ioc_type in ("domain", "email"):
        return v.lower()
    if ioc_type in ("md5", "sha1", "sha256", "sha512"):
        return v.lower()
    if ioc_type == "url":
        # unfang: hxxp->http, [.] -> ., [:] -> :
        u = re.sub(r"^hxxps?", lambda m: "http" + m.group(0)[4:], v, flags=re.IGNORECASE)
        u = u.replace("[.]", ".").replace("(.)", ".")
        u = u.replace("[:]", ":")
        return u.rstrip(_TRAILING_PUNCT)
    if ioc_type == "ip":
        return v
    return v


def _naive_validate(ioc_type: str, value: str) -> bool:
    if not value:
        return False
    if ioc_type == "ip":
        try:
            ipaddress.ip_address(value)
            # reject octets with leading zeros ambiguity? ipaddress handles; also
            # ensure dotted-quad textual form matches
            return True
        except ValueError:
            return False
    if ioc_type == "domain":
        if len(value) > 253 or "." not in value:
            return False
        if value.startswith(("-", ".")) or value.endswith(("-", ".")):
            return False
        labels = value.split(".")
        if any(len(x) == 0 or len(x) > 63 for x in labels):
            return False
        if not re.fullmatch(r"[A-Za-z0-9.-]+", value):
            return False
        tld = labels[-1]
        if not re.fullmatch(r"[A-Za-z]{2,}", tld):
            return False
        return True
    if ioc_type == "url":
        try:
            p = urlparse(value)
            if p.scheme not in ("http", "https"):
                return False
            if not p.hostname:
                return False
            return _naive_validate("domain", p.hostname) or _naive_validate("ip", p.hostname)
        except Exception:
            return False
    if ioc_type == "email":
        if "@" not in value:
            return False
        local, _, dom = value.rpartition("@")
        if not local or not dom:
            return False
        return _naive_validate("domain", dom)
    if ioc_type in ("md5", "sha1", "sha256", "sha512"):
        exp = {"md5": 32, "sha1": 40, "sha256": 64, "sha512": 128}[ioc_type]
        if len(value) != exp:
            return False
        return bool(re.fullmatch(r"[0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}|[0-9a-f]{128}", value))
    return False


_ALLOWLIST_CACHE: dict | None = None


def _load_allowlist_data() -> dict:
    global _ALLOWLIST_CACHE
    if _ALLOWLIST_CACHE is not None:
        return _ALLOWLIST_CACHE
    try:
        p = Path(__file__).resolve().parent / "data" / "allowlist.json"
        if p.exists():
            import json

            _ALLOWLIST_CACHE = json.loads(p.read_text())
            return _ALLOWLIST_CACHE
    except Exception:
        pass
    _ALLOWLIST_CACHE = {
        "private_cidrs": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                          "127.0.0.0/8", "169.254.0.0/16", "::1/128",
                          "fc00::/7", "fe80::/10"],
        "loopback": ["127.0.0.1", "::1"],
        "benign_domains": ["localhost", "example.com", "example.net", "microsoft.com", "w3.org"],
        "empty_hashes": [],
    }
    return _ALLOWLIST_CACHE


def _naive_allowlisted(ioc_type: str, value: str) -> bool:
    data = _load_allowlist_data()
    v = (value or "").lower()
    if ioc_type == "ip":
        if value in data.get("loopback", []):
            return True
        try:
            ip = ipaddress.ip_address(value)
            for cidr in data.get("private_cidrs", []):
                try:
                    if ip in ipaddress.ip_network(cidr, strict=False):
                        return True
                except ValueError:
                    continue
        except ValueError:
            pass
        return False
    if ioc_type in ("domain", "email", "url"):
        host = v
        if ioc_type == "email":
            _, _, host = v.rpartition("@")
        elif ioc_type == "url":
            try:
                host = (urlparse(value).hostname or "").lower()
            except Exception:
                host = v
        for b in data.get("benign_domains", []):
            b = b.lower()
            if host == b or host.endswith("." + b):
                return True
        if host in ("localhost",):
            return True
        return False
    if ioc_type in ("md5", "sha1", "sha256", "sha512"):
        return v in {h.lower() for h in data.get("empty_hashes", [])}
    return False


_PHISH_KWS = ("login", "verify", "secure", "paypal", "invoice", "suspended", "urgent", "password", "phish", "account")
_ABUSED_TLDS = (".tk", ".top", ".xyz", ".click", ".zip", ".mov")
_BRUTE_TOKS = ("fail", "brute", "401", "ssh", "failed password", "invalid user")


def _naive_score(ioc_type: str, value: str, context: str) -> tuple[int, str, list[str]]:
    base = {"ip": 65, "domain": 55, "url": 70, "email": 50,
            "md5": 60, "sha1": 60, "sha256": 60, "sha512": 60}.get(ioc_type, 50)
    reasons = [f"heuristic base score for {ioc_type}"]
    score = base
    blob = f"{value} {context}".lower()
    if any(k in blob for k in _PHISH_KWS):
        score += 15
        reasons.append("phishing keyword match")
    if ioc_type in ("domain", "url") and any(blob.find(t) != -1 and value.lower().endswith(t) or t in value.lower() for t in _ABUSED_TLDS):
        score += 10
        reasons.append("abused TLD")
    if ioc_type == "ip" and any(t in blob for t in _BRUTE_TOKS):
        score += 10
        reasons.append("brute-force context (fail/ssh)")
    score = max(0, min(100, score))
    level = "low" if score < 40 else "medium" if score < 65 else "high" if score < 85 else "critical"
    return score, level, reasons


def _naive_mitre(ioc_type: str, value: str, context: str) -> list[str]:
    ids: list[str] = []
    blob = f"{value} {context}".lower()
    if ioc_type in ("url", "domain") and any(k in blob for k in ("login", "verify", "secure", "phish", "account", "paypal")):
        ids.append("T1566.002")
    if ioc_type == "ip" and any(t in context.lower() for t in ("fail", "brute", "401", "ssh")):
        ids.append("T1110")
    if ioc_type in ("md5", "sha1", "sha256", "sha512") and any(t in context.lower() for t in (".exe", ".ps1", ".scr", ".dll")):
        ids.append("T1204")
    if ioc_type == "domain" and any(t in context.lower() for t in ("dns", "http", "beacon", "c2")):
        ids.append("T1071.001")
    return ids[:3]


# ---------------------------------------------------------------------------
# Helpers honoring the required semantics
# ---------------------------------------------------------------------------

def _line_no(text: str, start: int) -> int:
    """1-based line number by counting newlines before match start."""
    return text.count("\n", 0, max(0, min(start, len(text)))) + 1


def _context_snippet(text: str, s: int, e: int, window: int = 80) -> str:
    """text[max(0,s-window):e+window], newlines->space, capped at 400 chars."""
    s = max(0, min(s, len(text)))
    e = max(0, min(e, len(text)))
    lo = max(0, s - window)
    hi = min(len(text), e + window)
    snippet = text[lo:hi].replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return snippet[:400]


def _dedupe_key(ioc_type: str, value: str, evidence_id: str) -> str:
    return hashlib.sha256(f"{ioc_type}|{value}|{evidence_id}".encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(request: IOCAnalyzeRequest) -> AnalyzeResponse:
    """Analyze raw text and return structured IOCs.

    Implements: max-bytes truncation, None-text fallback path, per-match
    line_no / context_snippet, sha256 dedupe, and the
    extractor -> normalize -> validate -> allowlist -> scoring -> mitre_map
    wiring (each stage uses the sibling module when importable, else naive).
    """
    opts = request.options
    max_bytes = int(getattr(opts, "max_bytes", 5242880) or 5242880)
    window = int(getattr(opts, "context_window", 80) or 0)
    enable_fallback = bool(getattr(opts, "enable_fallback", True))

    raw_text = request.text
    fallback_used = False
    if raw_text is None:
        if enable_fallback:
            raw_text = ""
            fallback_used = True
        else:
            raw_text = ""
            fallback_used = False
    text = raw_text

    # 5MB cap: truncate on byte length, set flag.
    text_truncated = False
    encoded = text.encode("utf-8", errors="ignore")
    if len(encoded) > max_bytes:
        truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
        text = truncated
        text_truncated = True
    text_bytes = len(text.encode("utf-8"))

    evidence_id_s = str(request.evidence_id)

    # Stage 1: extractor
    try:
        if _extractor_fn is not None:
            raw_hits = _extractor_fn(text)  # type: ignore[misc]
        else:
            raw_hits = _naive_extract(text)
    except Exception:
        raw_hits = _naive_extract(text)

    records: list[IOCRecord] = []
    seen: set[str] = set()
    for hit in raw_hits:
        try:
            itype = str(hit.get("type", "")).lower()
            raw = str(hit.get("raw", ""))
            s = int(hit.get("start", 0))
            e = int(hit.get("end", s + len(raw)))
        except Exception:
            continue
        if itype == "hash":
            itype = "sha256"  # generic hash -> validate will classify/reject
        if itype not in ("ip", "domain", "url", "email", "md5", "sha1", "sha256", "sha512"):
            continue

        # Stage 2: normalize (refang defanged raw first, then canonicalize)
        try:
            value = _normalize_fn(itype, raw) if _normalize_fn is not None else _naive_normalize(itype, raw)
        except Exception:
            value = _naive_normalize(itype, raw)
        try:
            from backend.app.ioc.extractor import refang_text as _refang  # type: ignore
        except Exception:
            try:
                from .extractor import refang_text as _refang  # type: ignore
            except Exception:
                _refang = None  # type: ignore[assignment]
        if _refang is not None and any(t in raw for t in ("hxxp", "hxps", "[.]", "(.)", "{.}", "[dot]", "[@]", "[at]", "[:]")):
            try:
                value = _normalize_fn(itype, _refang(raw)) if _normalize_fn is not None else _naive_normalize(itype, _refang(raw))
            except Exception:
                pass
        value = str(value)

        # Stage 3: validate
        try:
            valid = _validate_fn(itype, value) if _validate_fn is not None else _naive_validate(itype, value)
        except Exception:
            valid = _naive_validate(itype, value)
        if not valid:
            continue

        # Stage 4: allowlist — flag, don't silently drop IPs (scoring caps them
        # to CLEAN via private-ip-cap so analysts still see RFC1918/TEST-NET in
        # logs). Drop allowlisted domains/emails only (documentation noise).
        try:
            denied = _allowlist_fn(itype, value) if _allowlist_fn is not None else _naive_allowlisted(itype, value)
        except Exception:
            denied = _naive_allowlisted(itype, value)
        if denied and itype in ("domain", "email"):
            continue

        lineno = _line_no(text, s)
        snippet = _context_snippet(text, s, e, window)

        # Stage 5: scoring
        try:
            if _score_fn is not None:
                scored = _score_fn(itype, value, snippet)  # type: ignore[misc]
                if isinstance(scored, dict):
                    score = int(scored.get("risk_score", scored.get("score", 50)))
                    level = str(scored.get("risk_level", scored.get("level", "medium")))
                    reasons = list(scored.get("reasons", []))
                elif isinstance(scored, (list, tuple)) and len(scored) >= 2:
                    score, level = int(scored[0]), str(scored[1])
                    reasons = list(scored[2]) if len(scored) > 2 else []
                else:
                    score, level, reasons = _naive_score(itype, value, snippet)
            else:
                score, level, reasons = _naive_score(itype, value, snippet)
        except Exception:
            score, level, reasons = _naive_score(itype, value, snippet)
        score = max(0, min(100, int(score)))
        if level not in ("low", "medium", "high", "critical"):
            level = "low" if score < 40 else "medium" if score < 65 else "high" if score < 85 else "critical"

        # Stage 6: mitre_map
        try:
            if _mitre_fn is not None:
                mapped = _mitre_fn(itype, value, snippet)  # type: ignore[misc]
                if mapped and isinstance(mapped, list) and isinstance(mapped[0], dict):
                    mitre_ids = [str(d.get("id", "")) for d in mapped if d.get("id")][:3]
                elif mapped and isinstance(mapped, list):
                    mitre_ids = [str(x) for x in mapped][:3]
                else:
                    mitre_ids = []
            else:
                mitre_ids = _naive_mitre(itype, value, snippet)
        except Exception:
            mitre_ids = _naive_mitre(itype, value, snippet)

        # Dedupe via sha256(type|value|evidence_id)
        key = _dedupe_key(itype, value, evidence_id_s)
        if key in seen:
            continue
        seen.add(key)

        records.append(
            IOCRecord(
                type=itype,  # type: ignore[arg-type]
                value_normalized=value,
                raw_found=raw,
                line_no=lineno,
                context_snippet=snippet,
                risk_score=score,
                risk_level=level,  # type: ignore[arg-type]
                reasons=reasons,
                mitre_ids=mitre_ids,
                status="new",
                dedupe_key=key,
            )
        )

    # Stage 7: optional Groq AI rerank (opt-in, top-N, quota-guarded, fail-open).
    # risk_score stays heuristic (source of truth); final = risk_score + ai_delta when accepted.
    try:
        use_ai = bool(getattr(opts, "use_ai", False))
    except Exception:
        use_ai = False
    if use_ai and records:
        try:
            from backend.app.ioc import groq_rerank as _groq  # type: ignore[import]
            from backend.app.ioc import quota as _quota  # type: ignore[import]
        except Exception:
            _groq = None  # type: ignore[assignment]
            _quota = None  # type: ignore[assignment]
        if _groq is not None:
            ranked = sorted(records, key=lambda r: r.risk_score, reverse=True)[:20]
            for rec in ranked:
                if rec.risk_level not in ("medium", "high", "critical"):
                    continue
                try:
                    allowed = True if _quota is None else bool(_quota.check_and_bump(str(request.tenant_id)))
                except Exception:
                    allowed = True
                if not allowed:
                    rec.ai_justification = "ai_skipped: quota"
                    continue
                try:
                    out = _groq.groq_rerank_one(rec.value_normalized, rec.context_snippet, rec.reasons)
                    d = out if isinstance(out, dict) else out.model_dump()
                    if d.get("accepted"):
                        rec.ai_delta = max(-15, min(15, int(d.get("delta", 0))))
                        rec.ai_justification = str(d.get("justification", ""))[:300]
                        rec.ai_accepted = True
                    else:
                        rec.ai_justification = str(d.get("justification", "ai_skipped"))[:300]
                except Exception:
                    continue

    counts: dict[str, int] = {}
    for r in records:
        counts[r.type] = counts.get(r.type, 0) + 1

<<<<<<< HEAD
=======
    # Stage 8 (Sprint-2): Threat Findings + correlation. Defensive: never fail
    # the analysis if findings/correlation break — return empty and continue.
    findings: list[dict] = []
    correlations: dict = {}
    try:
        from backend.app.ioc import threat_findings as _tf  # type: ignore[import]
        findings = [f.model_dump(mode="json") for f in _tf.build_findings(
            records, request.case_id, request.evidence_id, request.source_type)]
    except Exception:
        findings = []
    try:
        from backend.app.ioc import correlation as _corr  # type: ignore[import]
        correlations = dict(_corr.correlate(records))
    except Exception:
        correlations = {}

>>>>>>> 6cc0db3bd6a58ee1cde08412fc6c76bf75c42423
    return AnalyzeResponse(
        analysis_id=uuid.uuid4(),
        tenant_id=request.tenant_id,
        case_id=request.case_id,
        evidence_id=request.evidence_id,
        source_type=request.source_type,
        fallback_used=fallback_used,
        text_bytes=text_bytes,
        text_truncated=text_truncated,
        counts=counts,
        iocs=records,
<<<<<<< HEAD
=======
        findings=findings,
        correlations=correlations,
>>>>>>> 6cc0db3bd6a58ee1cde08412fc6c76bf75c42423
    )
