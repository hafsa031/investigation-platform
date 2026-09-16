# INTERN-2 UI Spec — IOC Views

## 1. Screens
1. **IOC list** (tenant-scoped table): columns `value_normalized | type |
   risk_level(score) | mitre_ids | status | last_seen`. Filters: type,
   risk_level, status, mitre_id, free-text (uses `gin_trgm` index).
2. **IOC detail drawer**: raw_found, context_snippet, reasons, mitre
   cards (tactic + technique name + reason), evidence link, tags editor.
3. **Upload/analyze panel**: paste text / pick `source_type`; shows
   `fallback_used` + `text_truncated` badges.

## 2. Rendering rules (security)
- ALL IOC-derived strings through `html_escape()` before `innerHTML`;
  prefer `textContent`. Covers: value, context_snippet, reasons, justification.
- Risk badges: low (gray), medium (amber), high (orange), critical (red).
- Phishing-critical rows pin to top, show `phishing-critical` chip.
- CSV export button MUST call `export_csv()` server-side; client must not
  build CSV from raw values (formula-injection risk).

## 3. States
- Empty: "No IOCs for this evidence yet."
- Fallback: show "fallback extraction used" warning chip when
  `fallback_used=true` (empty/null input or parser fallback path).
- Null-text: `raw_found/context_snippet/description/raw_text` may be null →
  render em-dash, never the string "None"/"null".

## 4. Tenant safety
- Every request sends `tenant_id`; UI never displays cross-tenant rows.
- Dedupe: rows keyed by `dedupe_key`; re-analysis updates `last_seen`,
  never duplicates within `(tenant_id, dedupe_key)`.

## 5. MITRE display
- Only the 4 pinned techniques (T1566.002, T1110, T1204, T1071.001,
  snapshot `v19.2-2025-10-24`); link each ID to
  `https://attack.mitre.org/techniques/<ID without dot-suffix>/` fallback
  search `https://attack.mitre.org/search/?query=<ID>`.
