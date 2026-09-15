"""Jagspire Intern-5 — IOC & Threat Analysis Dashboard (Streamlit viewer).

Run:  streamlit run streamlit_app.py
Env:  AI_RERANK_ENABLED=true GROQ_API_KEY=... streamlit run streamlit_app.py  # AI column live

Read-only demo viewer over backend/app/ioc/pipeline.py. No evidence stored.
All fixtures bundled are synthetic (RFC5737 / example.*).
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.app.ioc.export import export_csv
from backend.app.ioc.pipeline import analyze
from backend.app.ioc.schemas import IOCAnalyzeOptions, IOCAnalyzeRequest

FIX = Path(__file__).resolve().parent / "backend" / "app" / "ioc" / "tests" / "fixtures"

LEVEL_COLOR = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢",
               "clean": "⚪", "unknown": "⚪"}

st.set_page_config(page_title="Jagspire IOC & Threat Analysis", layout="wide")
st.title("🛡️ Jagspire — IOC & Threat Analysis (Intern-5)")
st.caption("Offline-first extractor → transparent scoring → MITRE map → optional Groq rerank. "
           "Every row carries proof: raw text, line number, snippet, reasons.")

with st.sidebar:
    st.header("Input")
    fixture = st.selectbox("Bundled synthetic fixture", ["(none)", "auth.log", "phish.eml", "doc_with_hashes.txt"])
    source_type = st.selectbox("source_type",
        ["auth_log", "email_header", "file_text", "syslog", "firewall", "pcap_text", "generic"])
    uploaded = st.file_uploader("…or upload evidence text (.log/.eml/.txt/.csv/.json/.md/.yaml, ≤5MB)",
        type=["log", "eml", "txt", "csv", "json", "md", "yaml", "yml"])
    pasted = st.text_area("…or paste text", height=150)
    use_ai = st.checkbox("Enable Groq AI rerank (needs GROQ_API_KEY + AI_RERANK_ENABLED=true)")
    f_level = st.selectbox("Filter level", ["all", "critical", "high", "medium", "low"])
    f_type = st.selectbox("Filter type", ["all", "ip", "domain", "url", "email", "md5", "sha1", "sha256", "sha512"])
    show_raw = st.checkbox("Show raw_found (defanged proof)", value=True)

if fixture != "(none)":
    text = (FIX / fixture).read_text()
elif uploaded is not None:
    text = uploaded.read().decode("utf-8", errors="ignore")
else:
    text = pasted

if st.button("🔍 Analyze", type="primary", disabled=not text.strip()):
    req = IOCAnalyzeRequest(
        tenant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4(),
        text=text, source_type=source_type,  # type: ignore[arg-type]
        options=IOCAnalyzeOptions(use_ai=use_ai))
    with st.spinner("Extracting IOCs…"):
        res = analyze(req)
    st.success(f"{len(res.iocs)} IOCs · fallback={res.fallback_used} · truncated={res.text_truncated}")

    rows = [i for i in res.iocs
            if (f_level == "all" or i.risk_level == f_level)
            and (f_type == "all" or i.type == f_type)]
    if not rows:
        st.info("No IOCs match the filters.")
    else:
        st.dataframe([{
            "risk": f"{LEVEL_COLOR.get(i.risk_level, '')} {i.risk_level} ({i.risk_score})",
            "type": i.type, "value": i.value_normalized,
            "MITRE": ",".join(i.mitre_ids) or "-",
            "AI Δ": (f"{i.ai_delta:+d}" if i.ai_accepted else "-"),
            "final": i.risk_score + (i.ai_delta if i.ai_accepted else 0),
            "line": i.line_no,
        } for i in rows], use_container_width=True, hide_index=True)

        sel = st.selectbox("Inspect row", [f"{i.type} {i.value_normalized}" for i in rows])
        rec = next(i for i in rows if f"{i.type} {i.value_normalized}" == sel)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Why this score")
            st.write(f"**{rec.risk_score} → {rec.risk_level}**")
            st.write(rec.reasons or ["no-signal"])
            if rec.mitre_ids:
                st.write("MITRE:", ", ".join(rec.mitre_ids))
            if rec.ai_accepted:
                st.write(f"AI {rec.ai_delta:+d}: {rec.ai_justification}")
        with c2:
            st.subheader("Proof")
            if show_raw:
                st.code(rec.raw_found)
            st.write(f"Line {rec.line_no}")
            st.code(rec.context_snippet)

        st.download_button("⬇ Export CSV (injection-safe)", export_csv(
            [{"type": i.type, "value": i.value_normalized, "risk": i.risk_level,
              "score": i.risk_score, "mitre": ",".join(i.mitre_ids),
              "line": i.line_no, "reasons": ";".join(i.reasons)} for i in rows],
            ["type", "value", "risk", "score", "mitre", "line", "reasons"]),
            file_name="iocs.csv", mime="text/csv")
else:
    st.info("Pick a fixture, upload a file, or paste text — then Analyze.")
    st.write("Try `auth.log`: attacker `198.51.100.23` → HIGH `T1110`, loopback capped LOW.")
