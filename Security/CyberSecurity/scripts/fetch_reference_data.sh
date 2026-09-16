#!/usr/bin/env bash
# Safe reference-data fetch (authoritative, no victim data, no keys needed).
# Downloads: Mozilla PSL, CISA KEV catalog, MITRE ATT&CK Enterprise STIX.
# Live malicious IOC feeds (URLhaus/ThreatFox dumps) are intentionally NOT
# fetched: they need Auth-Keys, change every 5 min, and must never ship as fixtures.
set -euo pipefail
OUT="${1:-backend/app/ioc/data/reference}"
mkdir -p "$OUT"
echo "-> Mozilla Public Suffix List"
curl -fsSL --max-time 60 https://publicsuffix.org/list/public_suffix_list.dat -o "$OUT/public_suffix_list.dat"
echo "-> CISA Known Exploited Vulnerabilities catalog"
curl -fsSL --max-time 60 https://www.cisa.gov/sites/default/files/csv/known_exploited_vulnerabilities.csv -o "$OUT/kev.csv"
echo "-> MITRE ATT&CK Enterprise STIX 2.1 (large, ~30MB)"
curl -fsSL --max-time 300 https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json -o "$OUT/enterprise-attack.json"
ls -la "$OUT"
echo "OK. Compare data/mitre_snapshot.json techniques against reference bundle; do NOT commit live IOC feeds."
