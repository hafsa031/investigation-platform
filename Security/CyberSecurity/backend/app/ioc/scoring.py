"""Transparent heuristic IOC scorer (pure stdlib).

score_ioc(ioc_type, value, context, allowlisted) -> (score, level, reasons).
Every score delta appends a human-readable reason string.
"""

from __future__ import annotations

import ipaddress
import math
import re
from urllib.parse import urlparse

# --- static lists -----------------------------------------------------------

PHISHING_KEYWORDS = (
    "login",
    "verify",
    "secure",
    "paypal",
    "invoice",
    "suspended",
    "urgent",
    "password",
    "account",
    "update",
    "bank",
    "credential",
    "confirm",
    "signin",
    "sign-in",
    "free",
    "prize",
    "winner",
)

SUSPICIOUS_EXTS = (".exe", ".scr", ".lnk", ".iso", ".hta", ".vbs", ".one", ".cpl")

ABUSED_TLDS = (".tk", ".top", ".xyz", ".click", ".zip", ".mov")

BRANDS = ("paypal", "microsoft", "google", "apple", "amazon")

BRUTE_TOKENS = ("fail", "401", "blocked")

C2_TOKENS = ("beacon", "curl", "wget", "powershell")

USER_EXEC_TOKENS = (
    "clicked",
    "click",
    "downloaded",
    "download",
    "opened",
    "open",
    "attachment",
    "macro",
    "executed",
    "execute",
    "enabled content",
    "launched",
    "launch",
)

_IPV4_RE = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
_HOST_LABEL_RE = re.compile(r"[a-z0-9-]+")
_VOWELS = set("aeiou")

_PRIVATE_NETS = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
)


# --- helpers ----------------------------------------------------------------

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(s)
    ent = 0.0
    for c in freq.values():
        p = c / n
        ent -= p * math.log2(p)
    return ent


def _extract_host(value: str, ioc_type: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    itype = (ioc_type or "").lower()
    if itype == "url":
        try:
            to_parse = v if "://" in v else "//" + v
            host = urlparse(to_parse).hostname or ""
            if host:
                return host.lower()
        except Exception:
            pass
        m = re.search(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", v.lower())
        return m.group(0) if m else v.lower()
    if itype == "email":
        parts = v.rsplit("@", 1)
        if len(parts) == 2:
            return parts[1].lower().strip(" <>;,.\"'")
        return v.lower()
    s = v.lower()
    s = s.split("/")[0].split(":")[0].strip(" <>;,.\"'")
    return s


def _is_private_ip_str(s: str) -> bool:
    s = (s or "").strip().strip("[]")
    try:
        ip = ipaddress.ip_address(s)
    except ValueError:
        return False
    # Spec: private/loopback cap only (RFC1918 + loopback + link-local),
    # NOT documentation/test nets (e.g. 203.0.113.0/24 stays external).
    for net in _PRIVATE_NETS:
        try:
            if ip in ipaddress.ip_network(net, strict=False):
                return True
        except ValueError:
            continue
    return False


def _value_has_private_ip(value: str, ioc_type: str) -> bool:
    v = (value or "").strip()
    itype = (ioc_type or "").strip().lower()
    if itype == "ip":
        return _is_private_ip_str(v)
    if itype == "url":
        for m in _IPV4_RE.findall(v):
            if _is_private_ip_str(m):
                return True
        low = v.lower()
        if "::1" in low or "127.0.0.1" in low:
            return True
        return False
    if itype == "domain":
        if v.lower() in ("localhost",):
            return True
        return _is_private_ip_str(v)
    return False


def _is_external(value: str, ioc_type: str, allowlisted: bool) -> bool:
    if allowlisted:
        return False
    return not _value_has_private_ip(value, ioc_type)


def level_for_score(score: int) -> str:
    s = int(score)
    if s <= 0:
        return "UNKNOWN"
    if 1 <= s <= 19:
        return "CLEAN"
    if 20 <= s <= 39:
        return "LOW"
    if 40 <= s <= 59:
        return "MEDIUM"
    if 60 <= s <= 79:
        return "HIGH"
    return "CRITICAL"


# --- main API ---------------------------------------------------------------

def score_ioc(
    ioc_type: str,
    value: str,
    context: str = "",
    allowlisted: bool = False,
) -> tuple[int, str, list[str]]:
    """Score a single IOC with transparent heuristics.

    Args:
        ioc_type: url | ip | domain | hash | md5 | sha1 | sha256 | sha512 | email.
        value: IOC string.
        context: surrounding free-text context.
        allowlisted: True if the IOC/domain is on the allowlist.

    Returns:
        (score 0-100, level, reasons list).
    """
    itype = (ioc_type or "").strip().lower()
    val = (value or "").strip()
    ctx = context if isinstance(context, str) else ("" if context is None else str(context))
    val_l = val.lower()
    ctx_l = ctx.lower()
    combined_l = f"{val_l} {ctx_l}"

    score = 0
    reasons: list[str] = []

    def add(delta: int, reason: str) -> None:
        nonlocal score
        score += delta
        reasons.append(reason)

    # ---- base scores ----
    if itype == "url":
        add(20, "base:url+20")
    elif itype == "ip":
        add(20, "base:ip+20")
    elif itype == "domain":
        add(15, "base:domain+15")
    elif itype in ("hash", "md5", "sha1", "sha256", "sha512"):
        add(25, f"base:hash({itype})+25")
    elif itype == "email":
        add(15, "base:email+15")
    else:
        return 0, "UNKNOWN", [f"unknown-type:{ioc_type}+0"]

    host = _extract_host(val, itype)

    # ---- +20 phishing keywords ----
    hit_kw = next((k for k in PHISHING_KEYWORDS if k in combined_l), None)
    if hit_kw:
        add(20, f"phishing-keyword:{hit_kw}+20")

    # ---- +20 suspicious extension ----
    path_part = val_l.split("?", 1)[0].split("#", 1)[0]
    hit_ext = next((e for e in SUSPICIOUS_EXTS if path_part.endswith(e)), None)
    if hit_ext:
        add(20, f"suspicious-ext:{hit_ext}+20")

    # ---- +15 punycode ----
    if "xn--" in val_l:
        add(15, "punycode:xn--+15")

    # ---- +15 typosquat (levenshtein <= 2 vs brands) ----
    labels = [p for p in _HOST_LABEL_RE.findall(host.lower()) if p]
    typo_hit: tuple[str, str] | None = None
    for label in labels:
        for brand in BRANDS:
            if label == brand:
                continue  # exact brand match is not squatting
            if _levenshtein(label, brand) <= 2:
                typo_hit = (label, brand)
                break
        if typo_hit:
            break
    if typo_hit:
        add(15, f"typosquat:{typo_hit[0]}~{typo_hit[1]}+15")

    # ---- +15 DGA (len>15, vowel ratio<0.2, entropy>4.0) ----
    dga_target = ""
    if host:
        dga_target = host.split(".")[0].lower()
        if not dga_target:
            dga_target = host.replace(".", "").lower()
    if dga_target:
        n = len(dga_target)
        vowels = sum(1 for c in dga_target if c in _VOWELS)
        vratio = (vowels / n) if n else 1.0
        ent = _shannon_entropy(dga_target)
        if n > 15 and vratio < 0.2 and ent > 4.0:
            add(15, f"dga:len={n},vowel={vratio:.2f},entropy={ent:.2f}+15")

    # ---- +10 abused TLD ----
    hit_tld = next((t for t in ABUSED_TLDS if host.endswith(t)), None)
    if hit_tld:
        add(10, f"abused-tld:{hit_tld}+10")

    # ---- +10 ip-in-url ----
    if itype == "url" and _IPV4_RE.search(val):
        add(10, "ip-in-url+10")

    # ---- +25 bruteforce (fail|401|blocked in context) ----
    hit_brute = next((t for t in BRUTE_TOKENS if t in ctx_l), None)
    if hit_brute:
        add(25, f"bruteforce:{hit_brute}+25")

    # ---- +25 c2 (beacon|curl|wget|powershell + external) ----
    hit_c2 = next((t for t in C2_TOKENS if t in ctx_l), None)
    if hit_c2 and _is_external(val, itype, bool(allowlisted)):
        add(25, f"c2:{hit_c2}+external+25")

    # ---- +20 user-exec chain ----
    hit_exec = next((t for t in USER_EXEC_TOKENS if t in ctx_l), None)
    if hit_exec is None and hit_ext and itype in ("url", "hash", "domain"):
        hit_exec = f"artifact:{hit_ext}"
    if hit_exec:
        add(20, f"user-exec:{hit_exec}+20")

    # ---- clamp then caps ----
    score = max(0, min(100, score))

    if _value_has_private_ip(val, itype):
        if score > 10:
            score = 10
        reasons.append("private-ip-cap:10")

    if bool(allowlisted):
        if score > 10:
            score = 10
        reasons.append("allowlisted-cap:10")

    score = max(0, min(100, score))
    level = level_for_score(score)
    return score, level, reasons


__all__ = ["score_ioc", "level_for_score"]
