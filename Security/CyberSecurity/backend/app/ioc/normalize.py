"""Normalization helpers for Intern-5 IOC module.

Covers: IP, domain, URL, email, hash.

Rules:
  - lowercase (where case-insensitive)
  - strip surrounding whitespace and sentence/trailing punctuation: . , ; : ) ] } ! ? ' "
  - strip leading wrappers: < ( [ { ' "
  - domains (and email domains): IDNA ToASCII
  - URLs: defanged ``hxxp(s)`` -> ``http(s)``, strip ``<>``/quotes, canonicalize
    scheme+host case, drop default ports.
"""

from __future__ import annotations

import re
import urllib.parse

_LEADING_STRIP = "<([{\"' \t\r\n"
_TRAILING_STRIP = ".,;:)]}`!?'\" \t\r\n"
_TRAILING_SENTENCE = ".,;:)]!?"  # extra safety set applied iteratively

_HXXP_RE = re.compile(r"^hxxps?", re.IGNORECASE)


def _strip_wrappers(value: str) -> str:
    """Strip surrounding whitespace, quotes/brackets and trailing punctuation."""
    s = value.strip()
    # Strip surrounding angle brackets / quotes used in email/log contexts:
    #   <http://evil.tk/x>, "http://evil.tk/x", '...'
    while len(s) >= 2 and (
        (s[0] == "<" and s[-1] == ">")
        or (s[0] == '"' and s[-1] == '"')
        or (s[0] == "'" and s[-1] == "'")
    ):
        s = s[1:-1].strip()
    # Strip leading wrappers and trailing sentence punctuation iteratively.
    prev = None
    while prev != s:
        prev = s
        s = s.strip()
        s = s.lstrip(_LEADING_STRIP)
        s = s.rstrip(_TRAILING_STRIP)
        # lone angle bracket leftovers
        if s.startswith("<"):
            s = s[1:]
        if s.endswith(">"):
            s = s[:-1]
    return s.strip()


def _to_ascii_domain(domain: str) -> str:
    """IDNA ToASCII; fall back to lowered input on failure."""
    try:
        return domain.encode("idna").decode("ascii")
    except Exception:
        return domain


def normalize_ip(value: str) -> str:
    """Normalize an IP literal: strip wrappers/brackets, lowercase (IPv6)."""
    s = _strip_wrappers(value.strip())
    # Strip brackets around IPv6 literals: [::1] -> ::1
    if len(s) >= 2 and s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    # Strip IPv6 zone id (%eth0) for canonical form.
    if "%" in s and ":" in s:
        s = s.split("%", 1)[0]
    return s.lower()


def normalize_domain(value: str) -> str:
    """Lowercase, strip trailing dot/punct, wildcard, IDNA ToASCII."""
    s = _strip_wrappers(value.strip()).lower()
    # Strip wildcard prefix: *.example.com -> example.com
    while s.startswith("*."):
        s = s[2:]
    # Strip port if accidentally attached (example.com:443 -> example.com).
    # Only when there is exactly one colon and the suffix is numeric.
    if s.count(":") == 1:
        host, _, port = s.partition(":")
        if port.isdigit() and "." in host:
            s = host
    # Strip single trailing dot (FQDN root), but keep internal dots.
    s = s.rstrip(".")
    if not s:
        return s
    return _to_ascii_domain(s)


def normalize_url(value: str) -> str:
    """Canonicalize a URL.

    - strip whitespace / ``<>`` / quotes
    - defang ``hxxp://`` / ``hxxps://`` (any case) -> ``http(s)://``
    - strip trailing sentence punctuation ``.,;:)]!?``
    - lowercase scheme + host, drop default ports (:80/:443)
    """
    s = value.strip()
    # Strip <> wrapping and quotes first so scheme regex anchors correctly.
    s = s.strip().strip("<>").strip("\"'").strip()
    s = _strip_wrappers(s)
    # Defang: hxxp://... -> http://...  (also HXXP, HxxP, hxxps)
    s = _HXXP_RE.sub(lambda m: "http" + ("s" if m.group(0).lower().endswith("s") else ""), s, count=1)
    # Handle bracket-defanged scheme leftovers like http://, https:// untouched.
    # Re-strip trailing sentence punctuation that often trails URLs in prose.
    s = s.rstrip(_TRAILING_SENTENCE + "\"'")
    # Lowercase scheme + host via urlsplit; keep path/query/fragment as-is.
    try:
        parts = urllib.parse.urlsplit(s)
        if parts.scheme and parts.netloc:
            scheme = parts.scheme.lower()
            netloc = parts.netloc.lower()
            # Drop default ports.
            if scheme == "http" and netloc.endswith(":80"):
                netloc = netloc[: -len(":80")]
            elif scheme == "https" and netloc.endswith(":443"):
                netloc = netloc[: -len(":443")]
            # IDNA-encode host portion (preserve userinfo/port).
            host_only = netloc
            userinfo, at, hostport = netloc.rpartition("@")
            hostport_ascii = _to_ascii_domain(hostport.split(":")[0]) if hostport else hostport
            if ":" in hostport and not hostport.startswith("["):
                # re-attach numeric port
                pname, _, pport = hostport.partition(":")
                hostport = f"{_to_ascii_domain(pname)}:{pport}" if pport else _to_ascii_domain(pname)
            else:
                hostport = hostport_ascii if "@" not in netloc else hostport
            netloc = f"{userinfo}{at}{hostport}" if at else hostport
            s = urllib.parse.urlunsplit((scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return s


def normalize_email(value: str) -> str:
    """Lowercase, strip punct, IDNA-encode domain part."""
    s = _strip_wrappers(value.strip()).lower()
    if "@" not in s:
        return s
    local, _, domain = s.rpartition("@")
    domain = domain.rstrip(".")
    if domain:
        domain = _to_ascii_domain(domain)
    return f"{local}@{domain}"


def normalize_hash(value: str) -> str:
    """Lowercase + strip (hashes are hex, case-insensitive)."""
    return _strip_wrappers(value.strip()).lower()


def normalize(value: str, ioc_type: str) -> str:
    """Dispatch normalizer by IOC type.

    ``ioc_type``: ip | domain | url | email | hash | md5 | sha1 | sha256 | sha512
    """
    t = (ioc_type or "").strip().lower()
    if t == "ip":
        return normalize_ip(value)
    if t == "domain":
        return normalize_domain(value)
    if t == "url":
        return normalize_url(value)
    if t == "email":
        return normalize_email(value)
    if t in ("hash", "md5", "sha1", "sha256", "sha512"):
        return normalize_hash(value)
    # Unknown type: generic strip + lowercase.
    return _strip_wrappers(value.strip()).lower()


__all__ = [
    "normalize",
    "normalize_ip",
    "normalize_domain",
    "normalize_url",
    "normalize_email",
    "normalize_hash",
]
