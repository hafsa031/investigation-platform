"""MITRE ATT&CK heuristic mapping for IOCs.

MITRE_VERSION pinned to the Enterprise ATT&CK release used for IDs/tactics.
"""

from __future__ import annotations

MITRE_VERSION = "v19.2-2025-10-24"

_PHISH_KEYWORDS = (
    "phish",
    "login",
    "signin",
    "sign-in",
    "verify",
    "account",
    "update",
    "secure",
    "bank",
    "paypal",
    "credential",
    "password",
    "confirm",
    "invoice",
    "payment",
    "free",
    "gift",
)

_IP_BRUTE_TOKENS = ("fail", "brute", "401", "ssh")

_HASH_EXEC_TOKENS = (".exe", ".ps1", ".scr", ".dll")

_DOMAIN_C2_TOKENS = ("dns", "http", "beacon", "c2")

_MAX_RESULTS = 3


def map_ioc(ioc_type: str, value: str, context: str = "") -> list[dict]:
    """Map an IOC to MITRE ATT&CK techniques.

    Args:
        ioc_type: One of ``url`` | ``domain`` | ``ip`` | ``hash`` (case-insensitive).
        value: The IOC value (URL, domain, IP, or hash string).
        context: Free-text context (log snippet, alert text, sandbox note).

    Returns:
        List of at most 3 dicts shaped as ``{id, tactic, reason}``.
        Empty list when no rule matches.
    """
    itype = (ioc_type or "").strip().lower()
    val = (value or "")
    ctx = (context or "")
    val_l = val.lower()
    ctx_l = ctx.lower()
    combined_l = f"{val_l} {ctx_l}"

    results: list[dict] = []

    # Rule 1: phishing url/domain (phish keywords or login in url) -> T1566.002
    if itype in ("url", "domain"):
        if any(k in combined_l for k in _PHISH_KEYWORDS) or ("login" in val_l):
            results.append(
                {
                    "id": "T1566.002",
                    "tactic": "Initial Access",
                    "reason": f"phishing indicator in {itype} '{val}': "
                    "phish keyword/login match",
                }
            )

    # Rule 2: ip + fail|brute|401|ssh in context -> T1110
    if itype == "ip":
        if any(t in ctx_l for t in _IP_BRUTE_TOKENS):
            results.append(
                {
                    "id": "T1110",
                    "tactic": "Credential Access",
                    "reason": f"brute-force signal for ip '{val}': "
                    "fail/brute/401/ssh in context",
                }
            )

    # Rule 3: hash (any algo) + .exe/.ps1/.scr/.dll in context -> T1204
    if itype in ("hash", "md5", "sha1", "sha256", "sha512"):
        if any(t in ctx_l for t in _HASH_EXEC_TOKENS):
            results.append(
                {
                    "id": "T1204",
                    "tactic": "Execution",
                    "reason": f"user-execution signal for hash '{val}': "
                    "executable artifact (.exe/.ps1/.scr/.dll) in context",
                }
            )

    # Rule 4: domain + dns|http|beacon|c2 in context -> T1071.001
    if itype == "domain":
        if any(t in ctx_l for t in _DOMAIN_C2_TOKENS):
            results.append(
                {
                    "id": "T1071.001",
                    "tactic": "Command and Control",
                    "reason": f"c2-over-web signal for domain '{val}': "
                    "dns/http/beacon/c2 in context",
                }
            )

    return results[:_MAX_RESULTS]
