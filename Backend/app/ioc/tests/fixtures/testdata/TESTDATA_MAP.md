# Test-Data Map — which file tests which work

All files live in `backend/app/ioc/tests/fixtures/testdata/`. 100% synthetic:
RFC5737 IPs (`192.0.2.x`, `198.51.100.x`, `203.0.113.x`), `example.*` domains,
hashes of short ASCII strings. Safe to download, open, and run anywhere.

| File | Work it tests | Must happen |
|---|---|---|
| `auth_ssh_bruteforce.log` | Log IOC extraction + `T1110` brute-force rule + fail→success + private-IP cap | `198.51.100.23` HIGH/`T1110`; `127.0.0.1` LOW max |
| `firewall_c2_beacon.log` | `T1071.001` C2 context + IP-host URL scoring + allowlist (`cdn.example` LOW) | `203.0.113.55` flagged; `cdn.example` never HIGH |
| `phish_credential_harvest.eml` | `T1566.002` spearphishing-link + defang (`hxxp/[.]`) + Reply-To/domain link | defanged URL → refanged + MITRE; sender domains extracted |
| `malware_drop_report.txt` | Hash classify (32/40/64) + `T1204` (hash+`.exe`/`.ps1`) + rejections (48-hex, empty-MD5) | sha256+md5+sha1 kept; `aaa…(48)` + empty hash dropped |
| `benign_ham.eml` | Precision / false-positive rate | NOTHING scores HIGH or CRITICAL |
| `defang_variants.txt` | Extractor refang table per line | every bracketed IOC extracted |
| `edge_noise.txt` | Adversarial noise (versions, UUID, localhost, bad IPs, `.dll` as domain) | no HIGH/CRITICAL; UUID/empty-hash/`999…` absent |
| `metadata_strings.txt` | `metadata` source_type (EXIF-style strings) | host + hash + email extracted |

Run: `pytest tests/test_ioc_testdata.py -v` · Full app: `pytest tests/ -q` · See it: `streamlit run streamlit_app.py`
