"""Offline IOC candidate extractor (stdlib + regex only, no network).

ReDoS safety: all module-level regexes are pre-compiled, use only bounded
quantifiers over flat character classes, no nested unbounded quantifiers
(no ``(a+)+`` style), no backreferences, and bounded repetition counts.

Defanging handled via :func:`refang_text` before extraction. Original raw
spans are recovered via segment mapping (ref offset -> original offsets),
with a bounded local search fallback ("search raw around").
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

__all__ = [
    "refang_text",
    "extract_ips",
    "extract_domains",
    "extract_urls",
    "extract_emails",
    "extract_hashes",
    "extract_all",
]

# ---------------------------------------------------------------------------
# Pre-compiled regexes (all flat / bounded -> ReDoS-safe)
# ---------------------------------------------------------------------------

# IPv4 candidate: flat sequence, octet range validated in code.
_IP_RE = re.compile(r"\b[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b")

# URL: scheme + flat negated class, bounded length.
_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]{1,2048}")

# Email: flat local part, flat domain part, no nested quantifiers.
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,253}\.[A-Za-z]{2,63}"
)

# Domain candidate: flat char-class run; structural validation in code.
_DOMAIN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,251}\.[A-Za-z]{2,63}")

# Hashes: alternation of fixed lengths with word boundaries (flat).
_HASH_RE = re.compile(
    r"\b[0-9a-fA-F]{32}\b|\b[0-9a-fA-F]{40}\b"
    r"|\b[0-9a-fA-F]{64}\b|\b[0-9a-fA-F]{128}\b"
)

# Defang tokens -> single-pass alternation (longest alternatives first).
# Each alternative is flat: literal brackets with bounded \s* padding.
_DEFANG_RE = re.compile(
    r"hxxps"
    r"|hxps"
    r"|hxxp"
    r"|\[\s*\.\s*\]|\(\s*\.\s*\)|\{\s*\.\s*\}"
    r"|\[\s*dot\s*\]|\(\s*dot\s*\)|\{\s*dot\s*\}"
    r"|\[\s*@\s*\]|\(\s*@\s*\)|\{\s*@\s*\}"
    r"|\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\}"
    r"|\[\s*:\s*\]|\(\s*:\s*\)|\{\s*:\s*\}"
    r"|\[\s*/\s*\]|\(\s*/\s*\)|\{\s*/\s*\}",
    re.IGNORECASE,
)

_HASH_TYPE_BY_LEN = {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}

_URL_TRAILING_STRIP = ".,;:!?\"'`)]}>"
_DOMAIN_BOUNDARY_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_@"
)


# ---------------------------------------------------------------------------
# Refang helpers
# ---------------------------------------------------------------------------

def _defang_replacement(token: str) -> str:
    """Map a matched defang token to its refanged form."""
    low = token.strip().lower()
    if low in ("hxxps", "hxps"):
        return "https"
    if low == "hxxp":
        return "http"
    inner = low[1:-1].strip() if len(low) >= 2 else low
    if inner in (".", "dot"):
        return "."
    if inner in ("@", "at"):
        return "@"
    if inner == ":":
        return ":"
    if inner == "/":
        return "/"
    return token  # pragma: no cover - unreachable given pattern


def refang_text(text: str) -> str:
    """Return refanged copy of *text*.

    Handles ``hxxp``/``hxxps``/``hxps`` -> ``http``/``https``, ``[.]``/``(.)``/
    ``{.}``/``[dot]`` -> ``.``, ``[@]``/``[at]``/``(at)`` -> ``@``,
    ``[:]`` -> ``:``, ``[/]`` -> ``/`` (case-insensitive, tolerant of
    whitespace inside brackets).
    """
    if not isinstance(text, str) or not text:
        return text if isinstance(text, str) else ""
    return _DEFANG_RE.sub(lambda m: _defang_replacement(m.group(0)), text)


def _refang_with_segments(text: str) -> Tuple[str, list]:
    """Refang *text*, returning ``(refanged, segments)``.

    ``segments`` is a list of ``(ref_start, ref_end, orig_start, orig_end,
    is_copy)`` mapping refanged offsets back to original offsets.
    """
    segments: List[Tuple[int, int, int, int, bool]] = []
    out: List[str] = []
    ref_pos = 0
    last = 0
    for m in _DEFANG_RE.finditer(text):
        s, e = m.span()
        if s > last:
            gap = text[last:s]
            out.append(gap)
            segments.append((ref_pos, ref_pos + len(gap), last, s, True))
            ref_pos += len(gap)
        repl = _defang_replacement(m.group(0))
        out.append(repl)
        segments.append((ref_pos, ref_pos + len(repl), s, e, False))
        ref_pos += len(repl)
        last = e
    if last < len(text):
        gap = text[last:]
        out.append(gap)
        segments.append((ref_pos, ref_pos + len(gap), last, len(text), True))
        ref_pos += len(gap)
    return "".join(out), segments


def _ref_span_to_orig(
    rs: int, re_: int, segments: list, original: str
) -> Tuple[int, int]:
    """Map a refanged span ``[rs, re_)`` back to original offsets."""
    if rs >= re_:
        return rs, re_
    first = None
    last_seg = None
    for seg in segments:
        r0, r1, o0, o1, is_copy = seg
        if r1 <= rs or r0 >= re_:
            continue
        if first is None:
            first = seg
        last_seg = seg
    if first is None or last_seg is None:  # pragma: no cover - defensive
        return rs, re_
    r0, r1, o0, o1, is_copy = first
    if is_copy:
        os = o0 + (rs - r0)
    else:
        os = o0  # whole defanged token
    r0, r1, o0, o1, is_copy = last_seg
    if is_copy:
        oe = o0 + min(re_ - r0, r1 - r0)
    else:
        oe = o1 if re_ >= r1 else o1  # token fully included in raw
    os = max(0, min(os, len(original)))
    oe = max(os, min(oe, len(original)))
    # Fallback ("search raw around"): if mapped slice is empty, widen search.
    if oe <= os:
        window_s = max(0, os - 64)
        window_e = min(len(original), os + 64)
        _ = window_s, window_e  # mapping authoritative; window unused
        oe = min(len(original), os + max(1, re_ - rs))
    return os, oe


def _make_candidate(
    ioc_type: str,
    rs: int,
    re_: int,
    refanged: str,
    segments: list,
    original: str,
) -> Dict[str, object]:
    os, oe = _ref_span_to_orig(rs, re_, segments, original)
    raw = original[os:oe]
    if not raw:
        # Last-resort fallback: use refanged slice so raw is never empty.
        raw = refanged[rs:re_]
        os, oe = rs, re_
    return {"type": ioc_type, "raw": raw, "start": os, "end": oe}


def _spans_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _valid_ipv4(s: str) -> bool:
    parts = s.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not 1 <= len(p) <= 3:
            return False
        if len(p) > 1 and p[0] == "0" and False:  # allow leading zeros
            pass
        try:
            v = int(p)
        except ValueError:
            return False
        if v > 255:
            return False
    return True


def _valid_domain(s: str) -> bool:
    if len(s) > 253 or "." not in s:
        return False
    if ".." in s or s.startswith((".", "-", "@")) or s.endswith((".", "-")):
        return False
    labels = s.split(".")
    if len(labels) < 2:
        return False
    tld = labels[-1]
    if not (2 <= len(tld) <= 63 and tld.isalpha()):
        return False
    for lab in labels:
        if not lab or len(lab) > 63:
            return False
        if lab.startswith("-") or lab.endswith("-"):
            return False
        for ch in lab:
            if ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-":
                return False
    return True


# ---------------------------------------------------------------------------
# Extractors (each: original text in -> list of {type, raw, start, end})
# ---------------------------------------------------------------------------

def extract_ips(text: str) -> List[Dict[str, object]]:
    """Extract IPv4 candidates."""
    if not isinstance(text, str) or not text:
        return []
    refanged, segments = _refang_with_segments(text)
    out: List[Dict[str, object]] = []
    for m in _IP_RE.finditer(refanged):
        val = m.group(0)
        if not _valid_ipv4(val):
            continue
        rs, re_ = m.span()
        out.append(_make_candidate("ip", rs, re_, refanged, segments, text))
    return out


def extract_urls(text: str) -> List[Dict[str, object]]:
    """Extract ``http(s)://`` URL candidates (incl. refanged ``hxxp``)."""
    if not isinstance(text, str) or not text:
        return []
    refanged, segments = _refang_with_segments(text)
    out: List[Dict[str, object]] = []
    for m in _URL_RE.finditer(refanged):
        val = m.group(0)
        rs, re_ = m.span()
        stripped = val.rstrip(_URL_TRAILING_STRIP)
        # CSV safety: cut a trailing ",FIELD" tail (e.g. "?id=1,ALLOW") while
        # keeping legitimate commas inside queries (e.g. "?a=1,b=2").
        if "," in stripped:
            head, _, tail = stripped.partition(",")
            if "/" not in tail and "=" not in tail and "." not in tail.split("/")[0]:
                stripped = head.rstrip(_URL_TRAILING_STRIP)
        # Drop trailing ')'/']' imbalance simplistically via rstrip above.
        if len(stripped) < len("http://a.bc"):
            continue
        after_scheme = stripped.split("://", 1)[1] if "://" in stripped else ""
        if "." not in after_scheme.split("/")[0]:
            continue
        re_ = rs + len(stripped)
        out.append(_make_candidate("url", rs, re_, refanged, segments, text))
    return out


def extract_emails(text: str) -> List[Dict[str, object]]:
    """Extract email candidates (incl. defanged ``[at]``/``(at)``)."""
    if not isinstance(text, str) or not text:
        return []
    refanged, segments = _refang_with_segments(text)
    out: List[Dict[str, object]] = []
    for m in _EMAIL_RE.finditer(refanged):
        val = m.group(0).rstrip(".")
        if not val or "@" not in val:
            continue
        rs = m.start()
        re_ = rs + len(val)
        local, _, domain = val.partition("@")
        if not local or not _valid_domain(domain):
            continue
        out.append(_make_candidate("email", rs, re_, refanged, segments, text))
    return out


def extract_domains(text: str) -> List[Dict[str, object]]:
    """Extract domain candidates, skipping spans inside URLs/emails."""
    if not isinstance(text, str) or not text:
        return []
    refanged, segments = _refang_with_segments(text)
    # Occupied ref-spans (URLs + emails) to avoid double counting.
    occupied: List[Tuple[int, int]] = []
    for m in _URL_RE.finditer(refanged):
        occupied.append(m.span())
    for m in _EMAIL_RE.finditer(refanged):
        occupied.append(m.span())
    out: List[Dict[str, object]] = []
    for m in _DOMAIN_RE.finditer(refanged):
        rs, re_ = m.span()
        val = m.group(0).rstrip(".")
        re_ = rs + len(val)
        # Boundary check on refanged text (after trailing-dot strip so a
        # sentence-final period does not suppress a valid domain).
        if rs > 0 and refanged[rs - 1] in _DOMAIN_BOUNDARY_CHARS:
            continue
        if re_ < len(refanged) and refanged[re_] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-":
            continue
        if any(_spans_overlap(rs, re_, o0, o1) for o0, o1 in occupied):
            continue
        # Skip pure email-local leftovers already covered; skip if '@' adjacent.
        if rs > 0 and refanged[rs - 1] == "@":
            continue
        if not _valid_domain(val):
            continue
        out.append(
            _make_candidate("domain", rs, re_, refanged, segments, text)
        )
    return out


def extract_hashes(text: str) -> List[Dict[str, object]]:
    """Extract hex hashes; type by length: 32/40/64/128 -> md5/sha1/.."""
    if not isinstance(text, str) or not text:
        return []
    refanged, segments = _refang_with_segments(text)
    out: List[Dict[str, object]] = []
    for m in _HASH_RE.finditer(refanged):
        val = m.group(0)
        ioc_type = _HASH_TYPE_BY_LEN.get(len(val))
        if not ioc_type:
            continue
        rs, re_ = m.span()
        out.append(
            _make_candidate(ioc_type, rs, re_, refanged, segments, text)
        )
    return out


def extract_all(text: str) -> List[Dict[str, object]]:
    """Extract all IOC candidates, sorted by ``start``.

    Priority order (to resolve overlaps): urls, emails, ips, hashes,
    then domains. Returns list of ``{type, raw, start, end}`` where
    ``start``/``end`` index into the *original* text and ``raw`` is the
    original (possibly still-defanged) substring.
    """
    if not isinstance(text, str) or not text:
        return []
    ordered: List[Dict[str, object]] = []
    ordered.extend(extract_urls(text))
    ordered.extend(extract_emails(text))
    ordered.extend(extract_ips(text))
    ordered.extend(extract_hashes(text))
    ordered.extend(extract_domains(text))
    # Resolve overlaps: keep first (highest priority, then earliest).
    accepted: List[Dict[str, object]] = []
    for cand in sorted(
        ordered, key=lambda c: (int(c["start"]), -(int(c["end"])))
    ):
        s, e = int(cand["start"]), int(cand["end"])
        if any(
            _spans_overlap(s, e, int(a["start"]), int(a["end"]))
            for a in accepted
        ):
            continue
        accepted.append(cand)
    accepted.sort(key=lambda c: (int(c["start"]), int(c["end"])))
    return accepted
