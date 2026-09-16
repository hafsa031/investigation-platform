"""Validation + allowlist + overlap helpers for Intern-5 IOC module.

- ``is_valid_ip``: ``ipaddress`` module (v4/v6).
- ``is_valid_domain``: ``tldextract`` with fallback to a simple grammar/PSL
  check when tldextract is unavailable. Rejects single-label names and
  numeric TLDs.
- ``is_valid_email``: local-part grammar + ``is_valid_domain`` on the domain.
- ``is_valid_hash``: hex charset + length {32,40,64,128}, rejects uniform
  strings (``000..``/``fff..``) and known empty-file hashes.
- ``is_allowlisted``: RFC1918/loopback/multicast (+reserved/link-local/
  unspecified) for IPs, benign domains (+ subdomains) for names.
- ``resolve_overlaps``: priority url > email > ip > domain > hash,
  longest-match wins.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:  # optional dependency (declared in requirements.txt)
    import tldextract as _tldextract_mod

    _HAS_TLDEXTRACT = True
except Exception:  # pragma: no cover - fallback path
    _tldextract_mod = None
    _HAS_TLDEXTRACT = False

# ---------------------------------------------------------------------------
# Shared grammar
# ---------------------------------------------------------------------------

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_LOCAL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_HASH_LENS = frozenset({32, 40, 64, 128})

_ALLOWLIST_PATH = Path(__file__).resolve().parent / "data" / "allowlist.json"


def _load_default_allowlist() -> dict:
    try:
        return json.loads(_ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _empty_hashes() -> frozenset[str]:
    """Known empty-file digests (computed + allowlist.json entries)."""
    known = {
        hashlib.md5(b"").hexdigest(),      # d41d8cd98f00b204e9800998ecf8427e
        hashlib.sha1(b"").hexdigest(),     # da39a3ee5e6b4b0d3255bfef95601890afd80709
        hashlib.sha256(b"").hexdigest(),   # e3b0c442...b52256
        hashlib.sha512(b"").hexdigest(),   # cf83e135...927da3e
    }
    try:
        data = _load_default_allowlist()
        for h in data.get("empty_hashes", []):
            known.add(str(h).strip().lower())
    except Exception:
        pass
    return frozenset(known)


_EMPTY_HASHES = _empty_hashes()

_DEFAULT_BENIGN_DOMAINS = frozenset(
    {
        "localhost",
        "example.com",
        "example.net",
        "example.org",
        "test",
        "invalid",
        "localhost.localdomain",
    }
)

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def is_valid_ip(value: str) -> bool:
    """True if ``value`` parses via :mod:`ipaddress` (v4 or v6)."""
    s = (value or "").strip().strip("[]").strip()
    if not s:
        return False
    # Reject trailing-dot / CIDR / port artefacts.
    if "/" in s or s.count(":") == 1 and s.rsplit(":", 1)[-1].isdigit() and "." in s:
        host, _, port = s.rpartition(":")
        if port.isdigit():
            s = host
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def _grammar_domain_ok(ascii_domain: str) -> bool:
    s = ascii_domain.strip().lower().rstrip(".")
    if not s or len(s) > 253:
        return False
    if "." not in s:
        return False  # reject single-label
    if ".." in s or s.startswith((".", "-")) or s.endswith((".", "-")):
        return False
    labels = s.split(".")
    if len(labels) < 2:
        return False
    for lab in labels:
        if not lab or len(lab) > 63 or not _LABEL_RE.match(lab):
            return False
    tld = labels[-1]
    if tld.isdigit():
        return False  # reject numeric TLD (e.g. 123, IPv4 lookalikes)
    if len(tld) < 2:
        return False
    if not re.search(r"[a-z]", tld):
        return False  # TLD must contain a letter
    return True


def is_valid_domain(value: str, *, use_tldextract: bool = True) -> bool:
    """Validate a domain name.

    Uses ``tldextract`` (registered suffix + non-empty domain) when available;
    always enforces grammar: multi-label, label charset, non-numeric TLD.
    Falls back to the grammar-only ("simple PSL") check if tldextract is
    missing or disabled.
    """
    raw = (value or "").strip().lower().rstrip(".")
    if not raw:
        return False
    try:
        ascii_domain = raw.encode("idna").decode("ascii")
    except Exception:
        return False
    if not _grammar_domain_ok(ascii_domain):
        return False
    if use_tldextract and _HAS_TLDEXTRACT:
        try:
            ext = _tldextract_mod.extract(ascii_domain)
            if not ext.suffix or not ext.domain:
                return False
            if ext.suffix.isdigit():
                return False
        except Exception:
            return False
    return True


def is_valid_email(value: str) -> bool:
    """Validate ``local@domain`` with local-part grammar + PSL domain."""
    s = (value or "").strip()
    if not s or s.count("@") != 1:
        return False
    local, _, domain = s.partition("@")
    if not local or not domain:
        return False
    if len(local) > 64 or len(s) > 254:
        return False
    if not _LOCAL_RE.match(local):
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    return is_valid_domain(domain)


def is_valid_hash(value: str) -> bool:
    """Hex charset + length 32/40/64/128; reject uniform + empty-file hashes."""
    s = (value or "").strip().lower()
    if len(s) not in _HASH_LENS:
        return False
    if not _HEX_RE.match(s):
        return False
    if len(set(s)) <= 1:
        return False  # e.g. 000...0, fff...f
    if s in _EMPTY_HASHES:
        return False
    return True


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def _coerce_allowlist(allowlist: Any) -> dict:
    """Normalize the ``allowlist`` arg to {'domains': set, 'ips': set, 'hashes': set}."""
    domains: set[str] = set()
    ips: set[str] = set()
    hashes: set[str] = set()
    nets: list[str] = []
    if allowlist is None:
        data = _load_default_allowlist()
        domains |= {str(d).lower().rstrip(".") for d in data.get("benign_domains", [])}
        nets.extend(str(c) for c in data.get("private_cidrs", []))
        ips |= {str(x).lower() for x in data.get("loopback", [])}
        hashes |= {str(h).lower() for h in data.get("empty_hashes", [])}
        domains |= set(_DEFAULT_BENIGN_DOMAINS)
        return {"domains": domains, "ips": ips, "hashes": hashes, "nets": nets}
    if isinstance(allowlist, Mapping):
        for key in ("benign_domains", "domains", "allow_domains"):
            for d in allowlist.get(key, []) or []:
                domains.add(str(d).lower().rstrip("."))
        for key in ("ips", "allow_ips", "loopback", "private_cidrs", "nets"):
            for x in allowlist.get(key, []) or []:
                x = str(x).strip()
                if "/" in x:
                    nets.append(x)
                else:
                    ips.add(x.lower())
        for key in ("hashes", "empty_hashes", "allow_hashes"):
            for h in allowlist.get(key, []) or []:
                hashes.add(str(h).lower())
        if not domains and not ips and not hashes and not nets:
            # Unknown dict shape: treat all string values as domains/ips.
            for v in allowlist.values():
                if isinstance(v, (list, tuple, set)):
                    for item in v:
                        domains.add(str(item).lower().rstrip("."))
                        ips.add(str(item).lower())
                elif isinstance(v, str):
                    domains.add(v.lower().rstrip("."))
                    ips.add(v.lower())
        defaults = _load_default_allowlist()
        domains |= {str(d).lower().rstrip(".") for d in defaults.get("benign_domains", [])}
        domains |= set(_DEFAULT_BENIGN_DOMAINS)
        nets.extend(str(c) for c in defaults.get("private_cidrs", []))
        return {"domains": domains, "ips": ips, "hashes": hashes, "nets": nets}
    # Iterable of strings.
    if isinstance(allowlist, (str, bytes)):
        items = [allowlist]
    else:
        try:
            items = list(allowlist)  # type: ignore[arg-type]
        except TypeError:
            items = [allowlist]
    for item in items:
        t = str(item).lower().rstrip(".")
        domains.add(t)
        ips.add(t)
        if "/" in t:
            nets.append(t)
    defaults = _load_default_allowlist()
    domains |= {str(d).lower().rstrip(".") for d in defaults.get("benign_domains", [])}
    domains |= set(_DEFAULT_BENIGN_DOMAINS)
    nets.extend(str(c) for c in defaults.get("private_cidrs", []))
    return {"domains": domains, "ips": ips, "hashes": hashes, "nets": nets}


def _domain_allowlisted(domain: str, domains: set[str]) -> bool:
    d = domain.lower().rstrip(".")
    if d in domains:
        return True
    # Subdomains of benign domains are benign too: evil.example.com? No —
    # only for reserved/benign roots like example.com / localhost. Keep the
    # general suffix rule: x.<benign> is allowlisted.
    for b in domains:
        if b and d.endswith("." + b):
            return True
    return False


def is_allowlisted(value: str, allowlist: Any = None) -> bool:
    """True if ``value`` is benign/private and should be suppressed.

    - IPs: RFC1918 private, loopback, multicast, reserved, link-local,
      unspecified, or contained in allowlist CIDRs / explicit IP entries.
    - domains/emails: exact or subdomain match against benign domains.
    - hashes: membership in empty-hash / allowlisted hash sets.
    """
    s = (value or "").strip()
    if not s:
        return False
    coerced = _coerce_allowlist(allowlist)
    domains: set[str] = coerced["domains"]
    ips: set[str] = coerced["ips"]
    hashes: set[str] = coerced["hashes"]
    nets: list[str] = coerced.get("nets", [])

    low = s.lower().rstrip(".")
    if low in hashes or low in ips:
        return True
    if "@" in s and "://" not in s:
        # email -> check domain part
        _, _, dom = s.rpartition("@")
        if dom and _domain_allowlisted(dom, domains):
            return True
    # IP check (strip brackets/zone first).
    probe = s.strip("[]").split("%", 1)[0]
    try:
        ip = ipaddress.ip_address(probe)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_link_local
            or ip.is_unspecified
        ):
            return True
        for net in nets:
            try:
                if ip in ipaddress.ip_network(net, strict=False):
                    return True
            except ValueError:
                continue
        if probe.lower() in ips:
            return True
        return False
    except ValueError:
        pass
    # URL -> extract host for domain check.
    host = low
    if "://" in low:
        try:
            import urllib.parse as _up

            host = (_up.urlsplit(low).hostname or low).rstrip(".")
        except Exception:
            host = low
    host = host.split(":")[0] if host.count(":") == 1 and "." in host else host
    # Bare single-label like 'localhost'.
    if host in domains:
        return True
    return _domain_allowlisted(host, domains)


# ---------------------------------------------------------------------------
# Overlap resolution
# ---------------------------------------------------------------------------

_PRIORITY: dict[str, int] = {
    "url": 0,
    "email": 1,
    "ip": 2,
    "domain": 3,
    "hash": 4,
    "md5": 4,
    "sha1": 4,
    "sha256": 4,
    "sha512": 4,
}


def _span_key(item: Mapping[str, Any]) -> tuple[int, int, int]:
    t = str(item.get("type", "")).lower()
    pri = _PRIORITY.get(t, 99)
    start = int(item.get("start", 0))
    end = int(item.get("end", start + len(str(item.get("value", "")))))
    return (pri, -(end - start), start)


def resolve_overlaps(candidates: Sequence[Mapping[str, Any] | Any]) -> list:
    """Resolve overlapping IOC spans.

    Priority: url > email > ip > domain > hash; ties broken by longest
    match. Accepts a sequence of ``{'type', 'value', 'start', 'end'}``
    mappings (objects with the same attributes also work). Returns the
    accepted subset sorted by ``start``.
    """
    normed: list[dict] = []
    for c in candidates:
        if isinstance(c, Mapping):
            d = dict(c)
            s = int(d.get("start", 0))
            e = int(d.get("end", s + len(str(d.get("value", "")))))
            d["start"], d["end"] = s, e
            normed.append(d)
        else:  # attribute-style record
            d = {
                "type": getattr(c, "type", ""),
                "value": getattr(c, "value", getattr(c, "value_normalized", "")),
                "start": int(getattr(c, "start", 0)),
                "end": int(
                    getattr(
                        c,
                        "end",
                        getattr(c, "start", 0) + len(str(getattr(c, "value", ""))),
                    )
                ),
            }
            d["_obj"] = c
            normed.append(d)
    # Highest priority + longest first; greedily accept non-overlapping.
    ordered = sorted(normed, key=_span_key)
    accepted: list[dict] = []
    spans: list[tuple[int, int]] = []
    for d in ordered:
        s, e = d["start"], d["end"]
        if any(s < ae and e > astart for astart, ae in spans):
            continue
        accepted.append(d)
        spans.append((s, e))
    accepted.sort(key=lambda d: (d["start"], d["end"]))
    out = []
    for d in accepted:
        out.append(d.pop("_obj", None) or d)
        # dict branch: d is already the output mapping
        if out[-1] is None:
            out[-1] = d
    return out


__all__ = [
    "is_valid_ip",
    "is_valid_domain",
    "is_valid_email",
    "is_valid_hash",
    "is_allowlisted",
    "resolve_overlaps",
]
