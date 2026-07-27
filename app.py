import contextlib
import csv
import io
import json
import os
import tempfile
from datetime import date

import pandas as pd
import streamlit as st

from report_generator import generate_report
from ui_helpers import (
    PAGES,
    PAGE_COMMAND_CENTER,
    PAGE_EVIDENCE_VAULT,
    PAGE_MATURITY_EXPLORER,
    PAGE_PRIORITY_QUEUE,
    PAGE_MIGRATION_PLANNER,
    PAGE_VALIDATION_LAB,
    PAGE_REPORTS,
    NAV_STATE_KEY,
    BADGE_MEASURED,
    BADGE_CALCULATED,
    BADGE_PROJECTED,
    BADGE_VALIDATED,
    BADGE_URGENT,
    BADGE_NEUTRAL,
    LABEL_MEASURED_CBOMKIT,
    LABEL_MEASURED_CRYPTOLYZER,
    LABEL_CALCULATED_MATURITY,
    LABEL_PROJECTED_IMPACT,
    DEFAULT_CRQC_YEAR,
    DEFAULT_BASE_MIGRATION_YEARS,
    DEFAULT_DATA_RETENTION_YEARS,
    EvidenceValidationError,
    validate_uploaded_json,
    escape,
    escape_join,
    render_html,
    badge,
    metric_card,
    dimension_card,
    display_score,
    load_validation_summary,
)


# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Crypto Agility Command Center",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------------------------------------------------
# Design system
# -------------------------------------------------------------------

st.markdown(
    """
    <style>
    :root {
        --background: #060b16;
        --surface: #0b1324;
        --surface-soft: #101a30;
        --surface-light: #15223a;
        --border: rgba(124, 156, 205, 0.18);
        --text: #f4f7fb;
        --muted: #8d9bb5;
        --cyan: #39d9f9;
        --cyan-soft: rgba(57, 217, 249, 0.13);
        --violet: #a981ff;
        --violet-soft: rgba(169, 129, 255, 0.13);
        --amber: #ffbd59;
        --amber-soft: rgba(255, 189, 89, 0.13);
        --coral: #ff6a79;
        --coral-soft: rgba(255, 106, 121, 0.13);
        --green: #43e0ad;
        --green-soft: rgba(67, 224, 173, 0.13);
        --slate: #72809a;
        --slate-soft: rgba(114, 128, 154, 0.16);
    }

    html,
    body,
    [class*="css"] {
        font-family:
            Inter,
            ui-sans-serif,
            system-ui,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
    }

    .stApp {
        background:
            radial-gradient(
                circle at 12% 5%,
                rgba(57, 217, 249, 0.08),
                transparent 28%
            ),
            radial-gradient(
                circle at 88% 12%,
                rgba(169, 129, 255, 0.09),
                transparent 25%
            ),
            linear-gradient(
                180deg,
                #060b16 0%,
                #080e1b 45%,
                #060b16 100%
            );
        color: var(--text);
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                rgba(7, 13, 26, 0.98),
                rgba(8, 15, 29, 0.98)
            );
        border-right: 1px solid var(--border);
        min-width: 320px;
        max-width: 320px;
    }

    [data-testid="stSidebar"] > div {
        padding-top: 1.1rem;
    }

    .block-container {
        max-width: 1600px;
        padding-top: 1.4rem;
        padding-bottom: 4rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    h1,
    h2,
    h3 {
        color: var(--text);
        letter-spacing: -0.025em;
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 2rem 2.2rem;
        margin-bottom: 1.35rem;
        border: 1px solid var(--border);
        border-radius: 22px;
        background:
            linear-gradient(
                120deg,
                rgba(14, 29, 52, 0.96),
                rgba(11, 19, 36, 0.95)
            );
        box-shadow:
            0 22px 80px rgba(0, 0, 0, 0.24),
            inset 0 1px 0 rgba(255, 255, 255, 0.04);
    }

    .hero::after {
        content: "";
        position: absolute;
        width: 340px;
        height: 340px;
        top: -210px;
        right: -80px;
        border-radius: 50%;
        background: rgba(57, 217, 249, 0.12);
        filter: blur(60px);
    }

    .hero-eyebrow {
        color: var(--cyan);
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: 0.7rem;
    }

    .hero-title {
        position: relative;
        z-index: 2;
        margin: 0;
        font-size: clamp(2rem, 4vw, 3.2rem);
        line-height: 1.05;
        font-weight: 800;
        background:
            linear-gradient(
                90deg,
                #ffffff,
                #bdefff 48%,
                #cbb9ff
            );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-copy {
        position: relative;
        z-index: 2;
        max-width: 850px;
        margin-top: 0.9rem;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.7;
    }

    .section-label {
        margin: 1.8rem 0 0.8rem;
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }

    .metric-grid {
        display: grid;
        grid-template-columns:
            repeat(auto-fit, minmax(190px, 1fr));
        gap: 0.9rem;
        margin: 0.9rem 0 1.35rem;
    }

    .metric-card {
        position: relative;
        min-height: 138px;
        padding: 1.15rem 1.2rem;
        overflow: hidden;
        border: 1px solid var(--border);
        border-radius: 18px;
        background:
            linear-gradient(
                145deg,
                rgba(15, 26, 47, 0.94),
                rgba(9, 17, 32, 0.94)
            );
        box-shadow:
            0 15px 45px rgba(0, 0, 0, 0.18),
            inset 0 1px 0 rgba(255, 255, 255, 0.025);
    }

    .metric-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 16px;
        right: 16px;
        height: 2px;
        border-radius: 999px;
        background: var(--accent);
    }

    .metric-value {
        margin-top: 0.6rem;
        color: var(--accent);
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.04em;
    }

    .metric-title {
        margin-top: 0.15rem;
        color: var(--text);
        font-size: 0.82rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .metric-note {
        margin-top: 0.35rem;
        color: var(--muted);
        font-size: 0.76rem;
        line-height: 1.4;
    }

    .accent-cyan { --accent: var(--cyan); }
    .accent-violet { --accent: var(--violet); }
    .accent-amber { --accent: var(--amber); }
    .accent-coral { --accent: var(--coral); }
    .accent-green { --accent: var(--green); }
    .accent-slate { --accent: var(--slate); }

    .panel {
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
        border-radius: 18px;
        background:
            linear-gradient(
                145deg,
                rgba(13, 23, 42, 0.94),
                rgba(8, 16, 30, 0.94)
            );
        box-shadow:
            0 16px 45px rgba(0, 0, 0, 0.16);
    }

    .panel-title {
        color: var(--text);
        font-size: 1rem;
        font-weight: 760;
        margin-bottom: 0.25rem;
    }

    .panel-copy {
        color: var(--muted);
        font-size: 0.84rem;
        line-height: 1.55;
    }

    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0.7rem 0;
    }

    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        width: fit-content;
        padding: 0.34rem 0.65rem;
        border: 1px solid transparent;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.075em;
        text-transform: uppercase;
    }

    .badge-measured {
        color: var(--cyan);
        border-color: rgba(57, 217, 249, 0.28);
        background: var(--cyan-soft);
    }

    .badge-calculated {
        color: var(--amber);
        border-color: rgba(255, 189, 89, 0.28);
        background: var(--amber-soft);
    }

    .badge-projected {
        color: var(--violet);
        border-color: rgba(169, 129, 255, 0.28);
        background: var(--violet-soft);
    }

    .badge-validated {
        color: var(--green);
        border-color: rgba(67, 224, 173, 0.28);
        background: var(--green-soft);
    }

    .badge-urgent {
        color: var(--coral);
        border-color: rgba(255, 106, 121, 0.3);
        background: var(--coral-soft);
    }

    .badge-neutral {
        color: var(--slate);
        border-color: rgba(114, 128, 154, 0.32);
        background: var(--slate-soft);
    }

    .evidence-chain {
        display: grid;
        grid-template-columns:
            repeat(4, minmax(130px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0 1.4rem;
    }

    .chain-node {
        position: relative;
        min-height: 118px;
        padding: 1rem;
        border: 1px solid var(--border);
        border-radius: 16px;
        background: rgba(12, 23, 42, 0.84);
    }

    .chain-node:not(:last-child)::after {
        content: "→";
        position: absolute;
        right: -0.65rem;
        top: 39%;
        z-index: 4;
        color: var(--slate);
        font-size: 1.1rem;
        font-weight: 800;
    }

    .chain-kicker {
        color: var(--cyan);
        font-size: 0.67rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .chain-value {
        margin-top: 0.55rem;
        color: var(--text);
        font-size: 1rem;
        font-weight: 750;
    }

    .chain-note {
        margin-top: 0.3rem;
        color: var(--muted);
        font-size: 0.72rem;
    }

    .dimension-grid {
        display: grid;
        grid-template-columns:
            repeat(4, minmax(170px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0;
    }

    .dimension-card {
        padding: 1rem;
        border: 1px solid var(--border);
        border-radius: 16px;
        background: rgba(10, 20, 37, 0.9);
    }

    .dimension-name {
        min-height: 42px;
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }

    .dimension-badge-row {
        margin: 0.5rem 0 0;
    }

    .dimension-score {
        margin-top: 0.4rem;
        color: var(--amber);
        font-size: 1.8rem;
        font-weight: 800;
    }

    .dimension-source {
        color: var(--muted);
        font-size: 0.7rem;
        line-height: 1.4;
    }

    .flight-plan {
        position: relative;
        padding-left: 1.65rem;
    }

    .flight-plan::before {
        content: "";
        position: absolute;
        top: 0.35rem;
        bottom: 0.35rem;
        left: 0.42rem;
        width: 2px;
        background:
            linear-gradient(
                180deg,
                var(--cyan),
                var(--violet),
                var(--green)
            );
    }

    .flight-step {
        position: relative;
        padding: 0.2rem 0 1.35rem 0.55rem;
    }

    .flight-step::before {
        content: "";
        position: absolute;
        left: -1.5rem;
        top: 0.25rem;
        width: 0.72rem;
        height: 0.72rem;
        border: 3px solid #0a1323;
        border-radius: 50%;
        background: var(--violet);
        box-shadow: 0 0 18px rgba(169, 129, 255, 0.75);
    }

    .flight-step-title {
        color: var(--text);
        font-weight: 780;
    }

    .flight-step-copy {
        margin-top: 0.3rem;
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.55;
    }

    .status-strip {
        display: grid;
        grid-template-columns:
            repeat(4, minmax(140px, 1fr));
        gap: 0.7rem;
    }

    .status-item {
        padding: 0.85rem;
        border: 1px solid var(--border);
        border-radius: 14px;
        background: rgba(10, 19, 35, 0.82);
    }

    .status-dot {
        display: inline-block;
        width: 0.52rem;
        height: 0.52rem;
        margin-right: 0.45rem;
        border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 14px rgba(67, 224, 173, 0.7);
    }

    .status-dot-off {
        background: var(--slate);
        box-shadow: none;
    }

    .status-label {
        color: var(--text);
        font-size: 0.8rem;
        font-weight: 750;
    }

    .status-copy {
        margin-top: 0.35rem;
        color: var(--muted);
        font-size: 0.7rem;
    }

    .urgent-banner {
        padding: 1rem 1.1rem;
        margin: 0.8rem 0;
        border: 1px solid rgba(255, 106, 121, 0.3);
        border-radius: 15px;
        color: #ffc1c8;
        background:
            linear-gradient(
                90deg,
                rgba(255, 106, 121, 0.14),
                rgba(255, 106, 121, 0.04)
            );
    }

    .info-banner {
        padding: 1rem 1.1rem;
        margin: 0.8rem 0;
        border: 1px solid rgba(57, 217, 249, 0.24);
        border-radius: 15px;
        color: #b9effb;
        background:
            linear-gradient(
                90deg,
                rgba(57, 217, 249, 0.12),
                rgba(57, 217, 249, 0.03)
            );
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 15px;
        overflow: hidden;
    }

    div[data-testid="stFileUploader"] {
        padding: 0.45rem;
        border: 1px dashed rgba(57, 217, 249, 0.22);
        border-radius: 14px;
        background: rgba(10, 19, 35, 0.58);
    }

    div.stButton > button {
        min-height: 42px;
        color: #03131d;
        font-weight: 800;
        border: 0;
        border-radius: 12px;
        background:
            linear-gradient(
                90deg,
                var(--cyan),
                #77e6ff,
                #b9a3ff
            );
        box-shadow:
            0 10px 30px rgba(57, 217, 249, 0.18);
    }

    div.stButton > button:hover {
        color: #03131d;
        transform: translateY(-1px);
        border: 0;
    }

    div[data-testid="stDownloadButton"] > button {
        min-height: 42px;
        border: 1px solid var(--border);
        border-radius: 12px;
    }

    /* ---------- Sidebar navigation (native buttons, not radio) ---------- */
    [data-testid="stSidebar"] div[data-testid="stButton"] > button {
        min-height: 38px;
        padding: 0.4rem 0.75rem;
        margin-bottom: 0.22rem;
        font-size: 0.86rem;
        font-weight: 650;
        border-radius: 10px;
        letter-spacing: 0;
        text-transform: none;
    }

    [data-testid="stSidebar"]
        div[data-testid="stButton"]
        > button[kind="secondary"] {
        color: #a8b4c8;
        background: transparent;
        border: 1px solid transparent;
        box-shadow: none;
    }

    [data-testid="stSidebar"]
        div[data-testid="stButton"]
        > button[kind="secondary"]:hover {
        color: #eff7ff;
        border-color: rgba(57, 217, 249, 0.2);
        background: rgba(57, 217, 249, 0.07);
        transform: none;
    }

    [data-testid="stSidebar"]
        div[data-testid="stButton"]
        > button[kind="primary"] {
        color: #55e2ff;
        background: linear-gradient(
            90deg,
            rgba(57, 217, 249, 0.16),
            rgba(57, 217, 249, 0.04)
        );
        border: 1px solid rgba(57, 217, 249, 0.3);
        box-shadow: inset 3px 0 0 #39d9f9;
    }

    /* ---------- Compact evidence/settings controls ---------- */
    [data-testid="stSidebar"] details {
        margin: 0.45rem 0 0.65rem;
        border: 1px solid rgba(124, 156, 205, 0.16);
        border-radius: 12px;
        background: rgba(10, 19, 35, 0.64);
        overflow: hidden;
    }

    [data-testid="stSidebar"] details summary {
        min-height: 42px;
        padding: 0.35rem 0.5rem;
        color: #b8c3d5;
        font-size: 0.8rem;
        font-weight: 720;
    }

    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        padding: 0.18rem;
        margin-bottom: 0.35rem;
        border-radius: 10px;
    }

    [data-testid="stSidebar"] [data-testid="stNumberInput"] {
        margin-bottom: 0.25rem;
    }

    .assumption-summary {
        margin: 0.55rem 0 0.8rem;
        padding: 0.68rem 0.72rem;
        border: 1px solid rgba(124, 156, 205, 0.14);
        border-radius: 10px;
        background: rgba(10, 19, 35, 0.56);
        color: #8d9bb5;
        font-size: 0.68rem;
        line-height: 1.65;
    }

    .assumption-summary strong {
        color: #dfe7f5;
        font-size: 0.7rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    /* ---------- Cleaner page shell ---------- */
    [data-testid="stHeader"] {
        background: rgba(6, 11, 22, 0.82);
        border-bottom: 1px solid rgba(124, 156, 205, 0.08);
        backdrop-filter: blur(14px);
    }

    @media (max-width: 950px) {
        .evidence-chain,
        .dimension-grid,
        .status-strip {
            grid-template-columns: 1fr 1fr;
        }

        .chain-node:not(:last-child)::after {
            display: none;
        }
    }

    @media (max-width: 620px) {
        .evidence-chain,
        .dimension-grid,
        .status-strip {
            grid-template-columns: 1fr;
        }

        [data-testid="stSidebar"] {
            min-width: 100%;
            max-width: 100%;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Temp-file handling (guaranteed cleanup)
# -------------------------------------------------------------------

@contextlib.contextmanager
def temp_evidence_files(contents):
    """
    Writes each byte string in `contents` to its own temporary
    file and yields the list of paths. Every temp file is removed
    when the block exits, whether or not an exception was raised,
    so a failed assessment never leaks a temp file. No temporary
    path is ever shown to the user.
    """

    paths = []

    try:
        for content in contents:
            descriptor, path = tempfile.mkstemp(suffix=".json")

            with os.fdopen(descriptor, "wb") as file:
                file.write(content)

            paths.append(path)

        yield paths

    finally:
        for path in paths:
            try:
                os.remove(path)
            except OSError:
                pass


# -------------------------------------------------------------------
# Presentation-only DataFrame builders
# -------------------------------------------------------------------

def build_summary_rows(report):
    rows = []

    for item in report:
        dimensions = item["dimensions"]
        protocol = item["protocol_evidence"]
        impact = item.get("impact_chain") or {}
        mosca = item["mosca"]

        rows.append({
            "Status": item.get("status", "Assessed"),
            "Asset": item["asset"],
            "Component": item["component"],
            "Primitive": display_score(item.get("primitive")),
            "TLS": display_score(protocol.get("tls_version")),
            "D1": str(display_score(dimensions.get("d1_coordination"))),
            "D2": str(display_score(dimensions.get("d2_pervasiveness"))),
            "D3": str(display_score(dimensions.get("d3_protocol"))),
            "D4": str(display_score(dimensions.get("d4_material"))),
            "Maturity": str(display_score(item["maturity"])),
            "Label": item["maturity_label"],
            "Confidence": item["confidence"],
            "Priority": str(display_score(item["priority"])),
            "Projected": str(
                display_score(impact.get("final_maturity"))
            ),
            "Migrate By": str(
                display_score(mosca.get("migrate_by"))
            ),
            "HNDL": (
                "Urgent" if mosca.get("urgent")
                else "Not Assessed" if mosca.get("urgent") is None
                else "Monitor"
            ),
        })

    return rows


def build_csv_bytes(report):
    rows = build_summary_rows(report)

    if not rows:
        return b""

    output = io.StringIO()

    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue().encode("utf-8-sig")


def build_migration_plan(report):
    """
    A presentation-only projection of already-calculated report
    data (recommendations, target levels, impact-chain steps).
    Adds no new methodology and fabricates no new values.
    """

    plan = []

    for item in report:
        if item.get("status") == "Not Assessed":
            continue

        impact = item.get("impact_chain") or {}

        plan.append({
            "asset": item["asset"],
            "component": item["component"],
            "current_maturity": item["maturity"],
            "projected_maturity": impact.get("final_maturity"),
            "binding_constraints": item["binding_constraints"],
            "recommendations": item["recommendations"],
            "impact_chain_steps": impact.get("steps", []),
            "current_priority": item["priority"],
            "migrate_by": item["mosca"]["migrate_by"],
            "hndl_urgent": item["mosca"]["urgent"],
        })

    return plan


def get_asset_names(report):
    return [item["asset"] for item in report]


def get_selected_asset(report, asset_name):
    return next(
        item
        for item in report
        if item["asset"] == asset_name
    )


# -------------------------------------------------------------------
# Sidebar: navigation
# -------------------------------------------------------------------

with st.sidebar:

    render_html(
        """
        <div style="padding: 0.4rem 0 1.1rem;">
            <div style="
                color: #39d9f9;
                font-size: 1.2rem;
                font-weight: 850;
                letter-spacing: -0.02em;
            ">
                ◈ Crypto Agility
            </div>
            <div style="
                margin-top: 0.25rem;
                color: #7f8da7;
                font-size: 0.68rem;
                font-weight: 750;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            ">
                PQC Readiness Command Center
            </div>
        </div>
        """
    )

    if NAV_STATE_KEY not in st.session_state:
        st.session_state[NAV_STATE_KEY] = PAGES[0]

    for page_name in PAGES:
        is_active_page = (
            st.session_state[NAV_STATE_KEY] == page_name
        )

        nav_clicked = st.button(
            page_name,
            key=f"nav_{page_name}",
            use_container_width=True,
            type="primary" if is_active_page else "secondary",
        )

        if nav_clicked and not is_active_page:
            st.session_state[NAV_STATE_KEY] = page_name
            st.rerun()

    page = st.session_state[NAV_STATE_KEY]

    render_html(
        '<div class="section-label">Assessment Input</div>'
    )

    with st.expander("Evidence files", expanded=True):
        cbom_upload = st.file_uploader(
            "CycloneDX CBOM",
            type=["json"],
            key="cbom_upload",
        )

        mapping_upload = st.file_uploader(
            "Component mapping",
            type=["json"],
            key="mapping_upload",
        )

        cryptolyzer_upload = st.file_uploader(
            "CryptoLyzer evidence",
            type=["json"],
            key="cryptolyzer_upload",
        )

    evidence_status_line = "  ·  ".join(
        f"{label}: {'Ready' if upload is not None else 'Not loaded'}"
        for label, upload in (
            ("CBOM", cbom_upload),
            ("Mapping", mapping_upload),
            ("CryptoLyzer", cryptolyzer_upload),
        )
    )

    st.caption(evidence_status_line)

    with st.expander("Advanced settings", expanded=False):
        st.caption(
            "Recommended defaults are already selected. "
            "Change them only when the assessment requires it."
        )

        assessment_year = st.number_input(
            "Assessment year",
            min_value=2020,
            max_value=2100,
            value=date.today().year,
            step=1,
            key="assessment_year",
        )

        crqc_year = st.number_input(
            "Assumed CRQC year",
            min_value=assessment_year,
            max_value=2200,
            value=max(DEFAULT_CRQC_YEAR, assessment_year),
            step=1,
            key="crqc_year",
        )

        base_migration_years = st.number_input(
            "Base migration time (years)",
            min_value=0.1,
            max_value=20.0,
            value=DEFAULT_BASE_MIGRATION_YEARS,
            step=0.5,
            key="base_migration_years",
        )

        data_retention_years = st.number_input(
            "Data-retention period (years)",
            min_value=0.0,
            max_value=50.0,
            value=DEFAULT_DATA_RETENTION_YEARS,
            step=1.0,
            key="data_retention_years",
        )

    render_html(
        f"""
        <div class="assumption-summary">
            <strong>Active assumptions</strong><br>
            Assessment: {escape(assessment_year)}
            &nbsp;·&nbsp; CRQC: {escape(crqc_year)}<br>
            Migration: {escape(f"{base_migration_years:g}")}y
            &nbsp;·&nbsp;
            Retention: {escape(f"{data_retention_years:g}")}y
        </div>
        """
    )

    run_assessment = st.button(
        "Analyze evidence",
        use_container_width=True,
        type="primary",
    )

    reset_clicked = st.button(
        "Reset assessment",
        use_container_width=True,
        type="secondary",
    )


# -------------------------------------------------------------------
# Reset action
# -------------------------------------------------------------------

if reset_clicked:
    for key in (
        "assessment_report",
        "cbom_data",
        "component_mapping_data",
        "cryptolyzer_data",
    ):
        st.session_state.pop(key, None)

    st.success("Assessment and evidence state cleared.")
    st.rerun()


# -------------------------------------------------------------------
# Assessment execution
# -------------------------------------------------------------------

if run_assessment:

    missing_files = []

    if cbom_upload is None:
        missing_files.append("CycloneDX CBOM")

    if mapping_upload is None:
        missing_files.append("Component Mapping")

    if cryptolyzer_upload is None:
        missing_files.append("CryptoLyzer Evidence")

    if missing_files:
        st.error(
            "Upload required evidence: "
            + ", ".join(missing_files)
        )

        st.stop()

    try:
        cbom_data = validate_uploaded_json(
            cbom_upload,
            required_keys=["components"],
        )

        component_mapping_data = validate_uploaded_json(
            mapping_upload
        )

        cryptolyzer_data = validate_uploaded_json(
            cryptolyzer_upload,
            required_keys=["component"],
        )

        with temp_evidence_files(
            [
                cbom_upload.getvalue(),
                mapping_upload.getvalue(),
                cryptolyzer_upload.getvalue(),
            ]
        ) as (cbom_path, mapping_path, cryptolyzer_path):

            report = generate_report(
                cbom_file=cbom_path,
                component_mapping_file=mapping_path,
                cryptolyzer_evidence_file=cryptolyzer_path,
                base_migration_years=base_migration_years,
                data_retention_years=data_retention_years,
                crqc_year=crqc_year,
                assessment_year=assessment_year,
            )

    except EvidenceValidationError as error:
        st.error(str(error))
        st.stop()

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        OSError,
        AttributeError,
    ):
        st.error(
            "Assessment failed while processing the uploaded "
            "evidence. Confirm the files match the expected CBOM, "
            "component-mapping, and CryptoLyzer evidence formats."
        )
        st.stop()

    if not report:
        st.warning(
            "No algorithm assets were found or assessed."
        )
        st.stop()

    st.session_state["assessment_report"] = report
    st.session_state["cbom_data"] = cbom_data
    st.session_state["component_mapping_data"] = (
        component_mapping_data
    )
    st.session_state["cryptolyzer_data"] = cryptolyzer_data

    st.success(
        f"Assessment completed for {len(report)} "
        "algorithm asset(s)."
    )


report = st.session_state.get("assessment_report")
cbom_data = st.session_state.get("cbom_data")
component_mapping_data = st.session_state.get(
    "component_mapping_data"
)
cryptolyzer_data = st.session_state.get("cryptolyzer_data")


def section_hero(eyebrow, title, description):
    render_html(
        f"""
        <div class="hero">
            <div class="hero-eyebrow">{escape(eyebrow)}</div>
            <h1 class="hero-title">{escape(title)}</h1>
            <div class="hero-copy">{escape(description)}</div>
        </div>
        """
    )


# -------------------------------------------------------------------
# Empty state
# -------------------------------------------------------------------

if not report:

    section_hero(
        "Evidence-driven PQC readiness",
        "Crypto Agility Command Center",
        (
            "Transform CycloneDX CBOMKit evidence and "
            "CryptoLyzer runtime observations into "
            "maturity, confidence, migration priority, "
            "recommendations, impact projections, and "
            "Mosca/HNDL urgency."
        ),
    )

    render_html(
        """
        <div class="evidence-chain">
            <div class="chain-node">
                <div class="chain-kicker">Measured</div>
                <div class="chain-value">CBOMKit</div>
                <div class="chain-note">
                    Algorithms, primitives, OIDs,
                    locations and material relationships
                </div>
            </div>

            <div class="chain-node">
                <div class="chain-kicker">Measured</div>
                <div class="chain-value">CryptoLyzer</div>
                <div class="chain-note">
                    Runtime TLS and hybrid/PQC evidence
                    from an authorized endpoint
                </div>
            </div>

            <div class="chain-node">
                <div class="chain-kicker">Calculated</div>
                <div class="chain-value">Maturity Engine</div>
                <div class="chain-note">
                    D1-D4, confidence, constraints,
                    priority and HNDL
                </div>
            </div>

            <div class="chain-node">
                <div class="chain-kicker">Projected</div>
                <div class="chain-value">Migration Plan</div>
                <div class="chain-note">
                    Recommendations, impact chain and
                    verification requirements
                </div>
            </div>
        </div>
        """
    )

    validation_summary = load_validation_summary()

    validated_badge_label = (
        f"Validated · {validation_summary['passed']} / "
        f"{validation_summary['total_tests']}"
        if validation_summary
        else "Validated · Summary Unavailable"
    )

    render_html(
        f"""
        <div class="panel">
            <div class="panel-title">
                Start an assessment
            </div>
            <div class="panel-copy">
                Upload the CycloneDX CBOM, component
                mapping, and normalized CryptoLyzer
                evidence from the sidebar. The dashboard
                does not invent missing evidence:
                unsupported or unavailable dimensions
                are marked Not Assessed.
            </div>
            <div class="badge-row">
                {badge(LABEL_MEASURED_CBOMKIT, BADGE_MEASURED)}
                {badge(LABEL_MEASURED_CRYPTOLYZER, BADGE_MEASURED)}
                {badge(LABEL_CALCULATED_MATURITY, BADGE_CALCULATED)}
                {badge(validated_badge_label, BADGE_VALIDATED)}
            </div>
        </div>
        """
    )

    st.stop()


# -------------------------------------------------------------------
# Shared assessment values
# -------------------------------------------------------------------

total_assets = len(report)

assessed_assets = [
    item for item in report
    if item.get("status") != "Not Assessed"
]

excluded_assets = [
    item for item in report
    if item.get("status") == "Not Assessed"
]

mapped_assets = sum(
    1 for item in report if item["component_mapped"]
)

urgent_assets = sum(
    1 for item in assessed_assets if item["mosca"]["urgent"]
)

highest_priority = (
    max(item["priority"] for item in assessed_assets)
    if assessed_assets
    else None
)

average_maturity = (
    sum(item["maturity"] for item in assessed_assets)
    / len(assessed_assets)
    if assessed_assets
    else None
)

average_projected = (
    sum(
        item["impact_chain"]["final_maturity"]
        for item in assessed_assets
    )
    / len(assessed_assets)
    if assessed_assets
    else None
)

summary_dataframe = pd.DataFrame(build_summary_rows(report))


# -------------------------------------------------------------------
# Command Center
# -------------------------------------------------------------------

if page == PAGE_COMMAND_CENTER:

    section_hero(
        "Executive workspace",
        "Crypto Agility Command Center",
        (
            "A consolidated view of measured crypto "
            "evidence, calculated migration readiness, "
            "projected remediation impact, and validated "
            "engine behavior."
        ),
    )

    render_html(
        f"""
        <div class="badge-row">
            {badge(LABEL_MEASURED_CBOMKIT, BADGE_MEASURED)}
            {badge(LABEL_MEASURED_CRYPTOLYZER, BADGE_MEASURED)}
            {badge(LABEL_CALCULATED_MATURITY, BADGE_CALCULATED)}
            {badge(LABEL_PROJECTED_IMPACT, BADGE_PROJECTED)}
        </div>
        """
    )

    render_html(
        f"""
        <div class="metric-grid">
            {metric_card(
                total_assets,
                "Algorithm Assets",
                "Algorithm components assessed from the CBOM",
                "cyan",
            )}

            {metric_card(
                mapped_assets,
                "Mapped Assets",
                "Assets resolved to a payment component",
                "green",
            )}

            {metric_card(
                f"{average_maturity:.1f}"
                if average_maturity is not None
                else "Not Assessed",
                "Current Maturity",
                "Average assessed component maturity",
                "amber",
            )}

            {metric_card(
                f"{average_projected:.1f}"
                if average_projected is not None
                else "Not Assessed",
                "Projected Maturity",
                "Rubric-based post-remediation projection",
                "violet",
            )}

            {metric_card(
                display_score(highest_priority),
                "Highest Priority",
                "Highest migration-backlog score",
                "coral",
            )}

            {metric_card(
                urgent_assets,
                "HNDL Urgent",
                "Assets requiring immediate planning",
                "coral",
            )}
        </div>
        """
    )

    render_html('<div class="section-label">Evidence Pipeline</div>')

    render_html(
        f"""
        <div class="evidence-chain">
            <div class="chain-node">
                <div class="chain-kicker">Measured</div>
                <div class="chain-value">
                    CBOMKit Evidence
                </div>
                <div class="chain-note">
                    {escape(total_assets)} algorithm asset(s)
                    available for assessment
                </div>
            </div>

            <div class="chain-node">
                <div class="chain-kicker">Mapped</div>
                <div class="chain-value">
                    Payment Context
                </div>
                <div class="chain-note">
                    {escape(mapped_assets)} of
                    {escape(total_assets)}
                    assets mapped successfully
                </div>
            </div>

            <div class="chain-node">
                <div class="chain-kicker">Measured</div>
                <div class="chain-value">
                    Runtime Protocol
                </div>
                <div class="chain-note">
                    CryptoLyzer evidence applied only
                    when the component matches
                </div>
            </div>

            <div class="chain-node">
                <div class="chain-kicker">Calculated</div>
                <div class="chain-value">
                    {escape(len(excluded_assets))} Not Assessed
                </div>
                <div class="chain-note">
                    Algorithm asset(s) with no scorable
                    dimension are preserved, not dropped
                </div>
            </div>
        </div>
        """
    )

    if urgent_assets:
        render_html(
            f"""
            <div class="urgent-banner">
                <strong>HNDL urgency detected.</strong>
                {escape(urgent_assets)} asset(s) have an adjusted
                migration duration plus retention period
                greater than the remaining time until the
                assumed CRQC year.
            </div>
            """
        )

    render_html('<div class="section-label">Migration Portfolio</div>')

    st.dataframe(
        summary_dataframe,
        use_container_width=True,
        hide_index=True,
    )

    if assessed_assets:
        highest_item = max(
            assessed_assets,
            key=lambda item: item["priority"],
        )

        left_column, right_column = st.columns([1.1, 0.9])

        with left_column:

            render_html(
                '<div class="panel-title">'
                "Highest-priority asset</div>"
            )

            hndl_badge = (
                badge("HNDL · Urgent", BADGE_URGENT)
                if highest_item["mosca"]["urgent"]
                else badge("HNDL · Monitor", BADGE_NEUTRAL)
            )

            render_html(
                f"""
                <div class="panel">
                    <div class="badge-row">
                        {badge("Calculated · Priority", BADGE_CALCULATED)}
                        {hndl_badge}
                    </div>

                    <div style="
                        color: #ffffff;
                        font-size: 1.45rem;
                        font-weight: 820;
                    ">
                        {escape(highest_item["asset"])}
                    </div>

                    <div class="panel-copy">
                        Component:
                        <strong>
                            {escape(highest_item["component"])}
                        </strong>
                        <br>
                        Current maturity:
                        <strong>
                            Level {escape(highest_item["maturity"])}
                            &mdash;
                            {escape(highest_item["maturity_label"])}
                        </strong>
                        <br>
                        Priority:
                        <strong>
                            {escape(highest_item["priority"])}
                        </strong>
                        <br>
                        Migrate by:
                        <strong>
                            {escape(highest_item["mosca"]["migrate_by"])}
                        </strong>
                    </div>
                </div>
                """
            )

        with right_column:

            render_html(
                '<div class="panel-title">'
                "Executive recommendation</div>"
            )

            recommendation_text = (
                highest_item["recommendations"][0]["recommendation"]
                if highest_item["recommendations"]
                else "No immediate recommendation."
            )

            render_html(
                f"""
                <div class="panel">
                    <div class="badge-row">
                        {badge("Projected · Guidance", BADGE_PROJECTED)}
                    </div>

                    <div class="panel-copy">
                        {escape(recommendation_text)}
                    </div>

                    <div style="
                        margin-top: 0.8rem;
                        color: #8d9bb5;
                        font-size: 0.72rem;
                    ">
                        New CBOMKit and CryptoLyzer evidence
                        is required to confirm any projected
                        maturity improvement.
                    </div>
                </div>
                """
            )
    else:
        st.info(
            "No assessed assets are available to rank. "
            "All algorithm assets in this report are "
            "currently Not Assessed."
        )


# -------------------------------------------------------------------
# Evidence Vault (includes former Evidence Monitor)
# -------------------------------------------------------------------

elif page == PAGE_EVIDENCE_VAULT:

    section_hero(
        "Measured evidence",
        "Evidence Vault",
        (
            "Inspect the original CycloneDX CBOM, "
            "cryptographic inventory, material "
            "relationships, payment-component mapping, "
            "CryptoLyzer runtime observations, and "
            "evidence coverage."
        ),
    )

    (
        metadata_tab,
        inventory_tab,
        relationship_tab,
        runtime_tab,
        coverage_tab,
        raw_tab,
    ) = st.tabs([
        "CBOM Overview",
        "Crypto Inventory",
        "Relationships",
        "Runtime Evidence",
        "Coverage & Re-scan",
        "Raw JSON",
    ])

    with metadata_tab:

        metadata = (cbom_data or {}).get("metadata", {})

        tool_services = (
            metadata.get("tools", {}).get("services", [])
        )

        tool_name = (
            tool_services[0].get("name")
            if tool_services
            else None
        )

        tool_version = (
            tool_services[0].get("version")
            if tool_services
            else None
        )

        component_count = len(
            (cbom_data or {}).get("components", [])
        )

        dependency_count = len(
            (cbom_data or {}).get("dependencies", [])
        )

        render_html(
            f"""
            <div class="metric-grid">
                {metric_card(
                    (cbom_data or {}).get("bomFormat", "Unknown"),
                    "Format",
                    "Uploaded source evidence format",
                    "cyan",
                )}

                {metric_card(
                    (cbom_data or {}).get("specVersion", "Unknown"),
                    "Specification",
                    "CycloneDX specification version",
                    "violet",
                )}

                {metric_card(
                    component_count,
                    "Components",
                    "All crypto asset components",
                    "green",
                )}

                {metric_card(
                    dependency_count,
                    "Relationships",
                    "CycloneDX dependency records",
                    "amber",
                )}
            </div>
            """
        )

        render_html(
            f"""
            <div class="panel">
                <div class="panel-title">
                    Evidence generator
                </div>
                <div class="panel-copy">
                    Tool:
                    <strong>{escape(display_score(tool_name))}</strong>
                    <br>
                    Version:
                    <strong>
                        {escape(display_score(tool_version))}
                    </strong>
                    <br>
                    Timestamp:
                    <strong>
                        {escape(
                            display_score(metadata.get("timestamp"))
                        )}
                    </strong>
                </div>
                <div class="panel-copy" style="margin-top: 0.5rem;">
                    This CBOM was generated externally by
                    CBOMKit / the Sonar Cryptography Plugin.
                    The dashboard reads and presents this
                    evidence — it does not generate it.
                </div>
                <div class="badge-row">
                    {badge(LABEL_MEASURED_CBOMKIT, BADGE_MEASURED)}
                </div>
            </div>
            """
        )

    with inventory_tab:

        inventory_rows = []

        for item in report:
            inventory_rows.append({
                "Status": item.get("status", "Assessed"),
                "Asset": item["asset"],
                "Component": item["component"],
                "Primitive": display_score(item.get("primitive")),
                "Crypto Functions": (
                    ", ".join(item.get("crypto_functions", []))
                    or "Not Assessed"
                ),
                "Parameter Set": display_score(
                    item.get("parameter_set")
                ),
                "OID": display_score(item.get("oid")),
                "Locations": item["oid_location_count"],
                "Algorithm Risk": item["algorithm_risk"],
            })

        st.dataframe(
            pd.DataFrame(inventory_rows),
            use_container_width=True,
            hide_index=True,
        )

        selected_inventory_asset = st.selectbox(
            "Inspect asset evidence",
            get_asset_names(report),
            key="inventory_asset",
        )

        inventory_item = get_selected_asset(
            report, selected_inventory_asset
        )

        locations_html = (
            "<br>".join(
                escape(location)
                for location in inventory_item["locations"]
            )
            or "Not Assessed"
        )

        render_html(
            f"""
            <div class="panel">
                <div class="badge-row">
                    {badge(LABEL_MEASURED_CBOMKIT, BADGE_MEASURED)}
                </div>
                <div class="panel-title">
                    {escape(inventory_item["asset"])}
                </div>
                <div class="panel-copy">
                    Source locations (static CBOM evidence,
                    not runtime behavior):
                    <br>
                    {locations_html}
                </div>
            </div>
            """
        )

    with relationship_tab:

        selected_relationship_asset = st.selectbox(
            "Select relationship",
            get_asset_names(report),
            key="relationship_asset",
        )

        relationship_item = get_selected_asset(
            report, selected_relationship_asset
        )

        protocol = relationship_item["protocol_evidence"]
        target = protocol.get("target") or {}

        runtime_target = (
            f"{escape(target.get('address'))}:"
            f"{escape(target.get('port'))}"
            if target
            else "Not Assessed"
        )

        first_location = (
            relationship_item["locations"][0]
            if relationship_item["locations"]
            else None
        )

        render_html(
            f"""
            <div class="evidence-chain">
                <div class="chain-node">
                    <div class="chain-kicker">Source</div>
                    <div class="chain-value">
                        {escape(display_score(first_location))}
                    </div>
                    <div class="chain-note">
                        CBOM occurrence evidence
                    </div>
                </div>

                <div class="chain-node">
                    <div class="chain-kicker">Algorithm</div>
                    <div class="chain-value">
                        {escape(relationship_item["asset"])}
                    </div>
                    <div class="chain-note">
                        Primitive:
                        {escape(
                            display_score(
                                relationship_item["primitive"]
                            )
                        )}
                    </div>
                </div>

                <div class="chain-node">
                    <div class="chain-kicker">Component</div>
                    <div class="chain-value">
                        {escape(relationship_item["component"])}
                    </div>
                    <div class="chain-note">
                        Payment weight:
                        {escape(relationship_item["payment_weight"])}
                    </div>
                </div>

                <div class="chain-node">
                    <div class="chain-kicker">Runtime</div>
                    <div class="chain-value">
                        {runtime_target}
                    </div>
                    <div class="chain-note">
                        {escape(
                            display_score(
                                protocol.get("tls_version")
                            )
                        )}
                    </div>
                </div>
            </div>
            """
        )

        st.info(
            "Material relationships are read from "
            "CycloneDX dependencies. Unsupported "
            "material-and-primitive combinations are "
            "marked Not Assessed rather than assigned "
            "an optimistic score."
        )

    with runtime_tab:

        selected_runtime_asset = st.selectbox(
            "Select runtime evidence",
            get_asset_names(report),
            key="runtime_asset",
        )

        runtime_item = get_selected_asset(
            report, selected_runtime_asset
        )

        protocol = runtime_item["protocol_evidence"]
        target = protocol.get("target") or {}

        target_address = target.get("address")

        is_synthetic_endpoint = target_address in (
            "localhost", "127.0.0.1"
        )

        render_html(
            f"""
            <div class="metric-grid">
                {metric_card(
                    display_score(protocol.get("tls_version")),
                    "TLS Version",
                    "Runtime protocol observed by CryptoLyzer",
                    "violet",
                )}

                {metric_card(
                    "Yes" if protocol.get("hybrid") else "No",
                    "Hybrid / PQC",
                    "Negotiated-group hybrid/PQC evidence",
                    "green",
                )}

                {metric_card(
                    runtime_item["component"],
                    "Component",
                    "Component matched to the endpoint",
                    "cyan",
                )}

                {metric_card(
                    "Matched"
                    if protocol.get("component_match")
                    else "Not Matched",
                    "Evidence Match",
                    "Runtime-to-component association",
                    "amber",
                )}
            </div>
            """
        )

        if is_synthetic_endpoint:
            st.info(
                "Synthetic controlled runtime evidence — this "
                "endpoint is a local/synthetic test target, not "
                "production infrastructure."
            )

        st.json(
            {
                "source": protocol.get("source"),
                "target": target,
                "component_match": protocol.get("component_match"),
                "assessed": protocol.get("assessed"),
            },
            expanded=True,
        )

    with coverage_tab:

        assessed_dimensions = 0
        total_dimensions = total_assets * 4

        for item in report:
            assessed_dimensions += sum(
                1
                for score in item["dimensions"].values()
                if score is not None
            )

        cbom_dot = "status-dot" if cbom_data else "status-dot status-dot-off"
        mapping_dot = (
            "status-dot"
            if component_mapping_data
            else "status-dot status-dot-off"
        )
        cryptolyzer_dot = (
            "status-dot"
            if cryptolyzer_data
            else "status-dot status-dot-off"
        )

        render_html(
            f"""
            <div class="status-strip">
                <div class="status-item">
                    <span class="{cbom_dot}"></span>
                    <span class="status-label">
                        CBOM Evidence
                    </span>
                    <div class="status-copy">
                        {"Loaded" if cbom_data else "Not loaded"}
                    </div>
                </div>

                <div class="status-item">
                    <span class="{mapping_dot}"></span>
                    <span class="status-label">
                        Component Mapping
                    </span>
                    <div class="status-copy">
                        {escape(mapped_assets)}/{escape(total_assets)}
                        assets mapped
                    </div>
                </div>

                <div class="status-item">
                    <span class="{cryptolyzer_dot}"></span>
                    <span class="status-label">
                        CryptoLyzer Evidence
                    </span>
                    <div class="status-copy">
                        {
                            "Loaded" if cryptolyzer_data
                            else "Not loaded"
                        }
                    </div>
                </div>

                <div class="status-item">
                    <span class="status-dot"></span>
                    <span class="status-label">
                        Not Assessed Assets
                    </span>
                    <div class="status-copy">
                        {escape(len(excluded_assets))} preserved
                        without a fabricated score
                    </div>
                </div>
            </div>
            """
        )

        render_html(
            f"""
            <div class="metric-grid">
                {metric_card(
                    f"{assessed_dimensions}/{total_dimensions}",
                    "Dimension Coverage",
                    "Assessed dimensions across all assets",
                    "cyan",
                )}

                {metric_card(
                    total_dimensions - assessed_dimensions,
                    "Not Assessed",
                    "Dimensions missing or unsupported",
                    "amber",
                )}

                {metric_card(
                    mapped_assets,
                    "Mapped Components",
                    "Assets with one unambiguous component",
                    "green",
                )}

                {metric_card(
                    "Required",
                    "Post-remediation Scan",
                    "New evidence must confirm projections",
                    "violet",
                )}
            </div>
            """
        )

        coverage_rows = []

        for item in report:
            for dimension, score in item["dimensions"].items():
                coverage_rows.append({
                    "Asset": item["asset"],
                    "Dimension": dimension,
                    "Status": (
                        "Assessed" if score is not None
                        else "Not Assessed"
                    ),
                    "Score": str(display_score(score)),
                })

        st.dataframe(
            pd.DataFrame(coverage_rows),
            use_container_width=True,
            hide_index=True,
        )

        if excluded_assets:
            reasons = pd.DataFrame([
                {
                    "Asset": item["asset"],
                    "Reason": item.get("excluded_reason"),
                }
                for item in excluded_assets
            ])

            st.dataframe(
                reasons,
                use_container_width=True,
                hide_index=True,
            )

        render_html(
            """
            <div class="panel">
                <div class="panel-title">
                    Re-scan checklist
                </div>
                <div class="panel-copy">
                    1. Generate a new CycloneDX CBOM with
                    CBOMKit.
                    <br>
                    2. Run CryptoLyzer against the authorized
                    endpoint.
                    <br>
                    3. Update component mapping if source
                    paths changed.
                    <br>
                    4. Re-run the assessment.
                    <br>
                    5. Compare measured maturity with the
                    projection.
                    <br>
                    6. Preserve the new JSON and CSV reports.
                </div>
            </div>
            """
        )

    with raw_tab:

        raw_cbom_tab, raw_crypto_tab, raw_assessment_tab = st.tabs([
            "CycloneDX CBOM",
            "CryptoLyzer",
            "Assessment",
        ])

        with raw_cbom_tab:
            st.json(cbom_data, expanded=False)

        with raw_crypto_tab:
            st.json(cryptolyzer_data, expanded=False)

        with raw_assessment_tab:
            st.json(report, expanded=False)


# -------------------------------------------------------------------
# Maturity Explorer
# -------------------------------------------------------------------

elif page == PAGE_MATURITY_EXPLORER:

    section_hero(
        "Core assessment model",
        "Maturity Explorer",
        (
            "Understand how measured evidence becomes "
            "D1-D4 maturity, confidence, binding "
            "constraints, and projected improvement."
        ),
    )

    selected_asset_name = st.selectbox(
        "Select algorithm asset",
        get_asset_names(report),
        key="maturity_asset",
    )

    item = get_selected_asset(report, selected_asset_name)

    if item.get("status") == "Not Assessed":
        st.warning(
            "This asset is Not Assessed: "
            f"{item.get('excluded_reason')}"
        )
    else:
        dimensions = item["dimensions"]
        impact = item["impact_chain"]

        render_html(
            f"""
            <div class="metric-grid">
                {metric_card(
                    f"Level {item['maturity']}",
                    "Current Maturity",
                    item["maturity_label"],
                    "amber",
                )}

                {metric_card(
                    item["confidence"],
                    "Assessment Confidence",
                    "Based on available dimension evidence",
                    "cyan",
                )}

                {metric_card(
                    f"Level {impact['final_maturity']}",
                    "Projected Maturity",
                    "After projected remediation actions",
                    "violet",
                )}

                {metric_card(
                    len(item["binding_constraints"]),
                    "Binding Constraints",
                    "Dimensions currently limiting maturity",
                    "coral",
                )}
            </div>
            """
        )

        render_html(
            f"""
            <div class="dimension-grid">
                {dimension_card(
                    "D1",
                    "D1 · Migration Coordination",
                    display_score(dimensions["d1_coordination"]),
                    "MEASURED · CBOMKit primitive and crypto "
                    "functions",
                )}
                {dimension_card(
                    "D2",
                    "D2 · Implementation Pervasiveness",
                    display_score(dimensions["d2_pervasiveness"]),
                    "MEASURED · CBOMKit OID and distinct "
                    "locations",
                )}
                {dimension_card(
                    "D3",
                    "D3 · Protocol Agility",
                    display_score(dimensions["d3_protocol"]),
                    "MEASURED · CryptoLyzer runtime endpoint "
                    "evidence",
                )}
                {dimension_card(
                    "D4",
                    "D4 · Persistent Material",
                    display_score(dimensions["d4_material"]),
                    "MEASURED · CBOM material type and "
                    "primitive",
                )}
            </div>
            """
        )

        left, right = st.columns(2)

        with left:
            render_html(
                '<div class="panel-title">Binding constraints</div>'
            )

            if item["binding_constraints"]:
                for constraint in item["binding_constraints"]:
                    st.warning(constraint)
            else:
                st.info("No binding constraints identified.")

        with right:
            render_html(
                '<div class="panel-title">'
                "Evidence interpretation</div>"
            )

            if dimensions["d4_material"] is None:
                st.info(
                    "D4 is Not Assessed because the current "
                    "material-and-primitive combination is "
                    "not classified by the rubric."
                )

            if dimensions["d3_protocol"] is None:
                st.info(
                    "D3 is Not Assessed: no matching "
                    "CryptoLyzer evidence was found for this "
                    "asset's component."
                )

            st.caption(
                "The component maturity is the minimum of "
                "all assessed dimensions. Not Assessed "
                "dimensions are excluded and reduce "
                "confidence rather than being scored as "
                "zero or a default level."
            )


# -------------------------------------------------------------------
# Priority Queue
# -------------------------------------------------------------------

elif page == PAGE_PRIORITY_QUEUE:

    section_hero(
        "Migration decision support",
        "Priority Queue",
        (
            "Rank assets using algorithm risk, payment "
            "context, and the readiness gap without "
            "changing the evidence-based maturity score. "
            "Payment weight affects priority ranking only "
            "— it does not alter technical maturity."
        ),
    )

    priority_rows = []

    for item in assessed_assets:
        priority_rows.append({
            "Rank": 0,
            "Asset": item["asset"],
            "Component": item["component"],
            "Algorithm Risk": item["algorithm_risk"],
            "Payment Weight": item["payment_weight"],
            "Maturity": item["maturity"],
            "Readiness Gap": 5 - item["maturity"],
            "Priority": item["priority"],
            "Migrate By": item["mosca"]["migrate_by"],
            "HNDL": (
                "Urgent" if item["mosca"]["urgent"] else "Monitor"
            ),
        })

    priority_rows.sort(
        key=lambda row: row["Priority"],
        reverse=True,
    )

    for index, row in enumerate(priority_rows, start=1):
        row["Rank"] = index

    st.dataframe(
        pd.DataFrame(priority_rows),
        use_container_width=True,
        hide_index=True,
    )

    if excluded_assets:
        st.caption(
            f"{len(excluded_assets)} Not Assessed asset(s) "
            "are excluded from ranking — see Evidence Vault "
            "for details."
        )

    if assessed_assets:
        selected_priority_asset = st.selectbox(
            "Inspect priority calculation",
            get_asset_names(assessed_assets),
            key="priority_asset",
        )

        priority_item = get_selected_asset(
            assessed_assets, selected_priority_asset
        )

        render_html(
            f"""
            <div class="panel">
                <div class="badge-row">
                    {badge("Calculated · Priority", BADGE_CALCULATED)}
                </div>
                <div class="panel-title">Priority Formula</div>
                <div class="panel-copy">
                    Algorithm Risk &times; Payment Weight
                    &times; (5 &minus; Maturity)
                    <br><br>
                    {escape(priority_item["algorithm_risk"])}
                    &times; {escape(priority_item["payment_weight"])}
                    &times;
                    (5 &minus; {escape(priority_item["maturity"])})
                    =
                    <strong>{escape(priority_item["priority"])}</strong>
                </div>
            </div>
            """
        )


# -------------------------------------------------------------------
# Migration Planner (includes former Scenario Lab)
# -------------------------------------------------------------------

elif page == PAGE_MIGRATION_PLANNER:

    section_hero(
        "Projected remediation",
        "Migration Planner",
        (
            "Convert binding constraints into a staged "
            "migration flight plan and compare remediation "
            "sequencing options. Projected changes must be "
            "confirmed through post-remediation CBOMKit and "
            "CryptoLyzer evidence."
        ),
    )

    if not assessed_assets:
        st.info(
            "No assessed assets are available to plan a "
            "migration for."
        )
    else:
        selected_migration_asset = st.selectbox(
            "Select migration candidate",
            get_asset_names(assessed_assets),
            key="migration_asset",
        )

        item = get_selected_asset(
            assessed_assets, selected_migration_asset
        )

        impact = item["impact_chain"]

        flight_tab, scenario_tab = st.tabs([
            "Flight Plan",
            "Scenarios",
        ])

        with flight_tab:

            render_html(
                f"""
                <div class="metric-grid">
                    {metric_card(
                        f"Level {item['maturity']}",
                        "Current State",
                        item["maturity_label"],
                        "amber",
                    )}

                    {metric_card(
                        item["priority"],
                        "Priority",
                        "Migration backlog score",
                        "coral",
                    )}

                    {metric_card(
                        f"Level {impact['final_maturity']}",
                        "Projected State",
                        "Rubric-based impact projection",
                        "violet",
                    )}

                    {metric_card(
                        item["mosca"]["migrate_by"],
                        "Migrate By",
                        "Latest projected completion year",
                        "green",
                    )}
                </div>
                """
            )

            if item["mosca"]["urgent"]:
                render_html(
                    """
                    <div class="urgent-banner">
                        <strong>HNDL urgency:</strong>
                        the adjusted migration duration plus
                        retention period exceeds the remaining
                        time until the assumed CRQC year.
                    </div>
                    """
                )

            render_html(
                '<div class="section-label">'
                "Migration Flight Plan</div>"
            )

            flight_steps_html = [
                """
                <div class="flight-step">
                    <div class="flight-step-title">
                        Observe current state
                    </div>
                    <div class="flight-step-copy">
                        Measured CBOMKit and CryptoLyzer
                        evidence establishes the baseline.
                    </div>
                </div>
                """
            ]

            for step in impact["steps"]:
                flight_steps_html.append(
                    f"""
                    <div class="flight-step">
                        <div class="flight-step-title">
                            Step {escape(step["step"])} ·
                            {escape(step["dimension"])}
                        </div>
                        <div class="flight-step-copy">
                            {escape(step["recommendation"])}
                            <br>
                            Dimension:
                            Level {escape(step["from_level"])}
                            &rarr;
                            Level {escape(step["to_level"])}
                            <br>
                            Component maturity:
                            Level {escape(step["maturity_before"])}
                            &rarr;
                            Level {escape(step["maturity_after"])}
                        </div>
                    </div>
                    """
                )

            flight_steps_html.append(
                f"""
                <div class="flight-step">
                    <div class="flight-step-title">
                        Re-scan and confirm
                    </div>
                    <div class="flight-step-copy">
                        Generate new CBOMKit and CryptoLyzer
                        evidence. Projected maturity:
                        Level {escape(impact["final_maturity"])}.
                        This is a projection, not a measured
                        post-remediation result.
                    </div>
                </div>
                """
            )

            render_html(
                '<div class="flight-plan">'
                + "".join(flight_steps_html)
                + "</div>"
            )

            render_html(
                """
                <div class="info-banner">
                    Projected maturity changes are simulation
                    results. Maturity must be recalculated from
                    new measured evidence after remediation.
                </div>
                """
            )

        with scenario_tab:

            current_maturity = item["maturity"]
            projected_maturity = impact["final_maturity"]
            current_priority = item["priority"]

            projected_priority = round(
                item["algorithm_risk"]
                * item["payment_weight"]
                * (5 - projected_maturity),
                2,
            )

            scenario_1, scenario_2, scenario_3 = st.columns(3)

            with scenario_1:
                render_html(
                    f"""
                    <div class="panel">
                        <div class="badge-row">
                            {badge("Scenario A", BADGE_PROJECTED)}
                        </div>
                        <div class="panel-title">
                            Primitive-first
                        </div>
                        <div class="panel-copy">
                            Improve D1 first. Overall maturity
                            may remain constrained if D3
                            remains at the current level.
                        </div>
                    </div>
                    """
                )

            with scenario_2:
                render_html(
                    f"""
                    <div class="panel">
                        <div class="badge-row">
                            {badge("Scenario B", BADGE_PROJECTED)}
                        </div>
                        <div class="panel-title">
                            Protocol-first
                        </div>
                        <div class="panel-copy">
                            Improve D3 first. Overall maturity
                            may remain constrained if D1
                            remains at the current level.
                        </div>
                    </div>
                    """
                )

            with scenario_3:
                render_html(
                    f"""
                    <div class="panel">
                        <div class="badge-row">
                            {badge("Scenario C · Recommended", BADGE_NEUTRAL)}
                        </div>
                        <div class="panel-title">
                            Coordinated migration
                        </div>
                        <div class="panel-copy">
                            Address all current binding
                            constraints.
                            <br><br>
                            Maturity:
                            {escape(current_maturity)}
                            &rarr; {escape(projected_maturity)}
                            <br>
                            Priority:
                            {escape(current_priority)}
                            &rarr; {escape(projected_priority)}
                        </div>
                    </div>
                    """
                )

            comparison = pd.DataFrame([
                {
                    "Measure": "Maturity",
                    "Current": current_maturity,
                    "Projected": projected_maturity,
                },
                {
                    "Measure": "Priority",
                    "Current": current_priority,
                    "Projected": projected_priority,
                },
            ])

            st.dataframe(
                comparison,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "No synthetic performance benchmark values "
                "are used in these scenarios."
            )


# -------------------------------------------------------------------
# Validation Lab
# -------------------------------------------------------------------

elif page == PAGE_VALIDATION_LAB:

    section_hero(
        "Implementation assurance",
        "Validation Lab",
        (
            "Demonstrate that the assessment engine behaves "
            "consistently across unit, integration, mutation, "
            "and sensitivity validation."
        ),
    )

    validation_summary = load_validation_summary()

    if validation_summary is None:
        st.warning(
            "Validation summary unavailable. Generate it "
            "with: `python generate_validation_summary.py` "
            "(this dashboard never runs pytest automatically)."
        )
    else:
        render_html(
            f"""
            <div class="metric-grid">
                {metric_card(
                    validation_summary["passed"],
                    "Tests Passed",
                    f"Of {validation_summary['total_tests']} "
                    "total automated tests",
                    "green",
                )}

                {metric_card(
                    validation_summary["failed"],
                    "Failures",
                    "Failing validation cases",
                    "green"
                    if validation_summary["failed"] == 0
                    else "coral",
                )}

                {metric_card(
                    f"{validation_summary['duration_seconds']}s",
                    "Duration",
                    "Time to run the full suite",
                    "cyan",
                )}

                {metric_card(
                    len(validation_summary["category_counts"]),
                    "Test Modules",
                    "Distinct test files executed",
                    "violet",
                )}
            </div>
            """
        )

        st.caption(
            f"Generated: {validation_summary['generated_at']}"
        )

        category_rows = [
            {
                "Test Module": module_name,
                "Passed": counts.get("passed", 0),
                "Failed": (
                    counts.get("failed", 0)
                    + counts.get("error", 0)
                ),
                "Skipped": counts.get("skipped", 0),
            }
            for module_name, counts
            in validation_summary["category_counts"].items()
        ]

        st.dataframe(
            pd.DataFrame(category_rows),
            use_container_width=True,
            hide_index=True,
        )

    render_html(
        f"""
        <div class="badge-row">
            {badge("Validated · Test Suite", BADGE_VALIDATED)}
        </div>
        """
    )

    render_html(
        """
        <div class="info-banner">
            Validation confirms implementation behavior. It
            does not prove that an assessed payment system is
            PQC-ready.
        </div>
        """
    )


# -------------------------------------------------------------------
# Reports
# -------------------------------------------------------------------

elif page == PAGE_REPORTS:

    section_hero(
        "Audit and export",
        "Reports",
        (
            "Download the assessed portfolio, raw measured "
            "evidence, projected migration guidance, and "
            "machine-readable reports."
        ),
    )

    json_bytes = json.dumps(
        report, indent=2, ensure_ascii=False
    ).encode("utf-8")

    csv_bytes = build_csv_bytes(report)

    cbom_bytes = json.dumps(
        cbom_data, indent=2, ensure_ascii=False
    ).encode("utf-8")

    cryptolyzer_bytes = json.dumps(
        cryptolyzer_data, indent=2, ensure_ascii=False
    ).encode("utf-8")

    migration_plan_bytes = json.dumps(
        build_migration_plan(report),
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")

    validation_summary = load_validation_summary()

    download_1, download_2 = st.columns(2)

    with download_1:
        st.download_button(
            "Download Assessment JSON",
            json_bytes,
            file_name="assessment_report.json",
            mime="application/json",
            use_container_width=True,
        )

        st.download_button(
            "Download Original CBOM",
            cbom_bytes,
            file_name="cyclonedx_cbom.json",
            mime="application/json",
            use_container_width=True,
        )

        st.download_button(
            "Download Migration Plan",
            migration_plan_bytes,
            file_name="migration_plan.json",
            mime="application/json",
            use_container_width=True,
        )

    with download_2:
        st.download_button(
            "Download Portfolio CSV",
            csv_bytes,
            file_name="assessment_report.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.download_button(
            "Download CryptoLyzer Evidence",
            cryptolyzer_bytes,
            file_name="cryptolyzer_evidence.json",
            mime="application/json",
            use_container_width=True,
        )

        if validation_summary is not None:
            st.download_button(
                "Download Validation Summary",
                json.dumps(
                    validation_summary,
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8"),
                file_name="validation_summary.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.caption(
                "Validation summary unavailable — run "
                "`python generate_validation_summary.py` "
                "to generate it."
            )

    render_html(
        f"""
        <div class="panel">
            <div class="panel-title">
                Report evidence classification
            </div>
            <div class="badge-row">
                {badge(LABEL_MEASURED_CBOMKIT, BADGE_MEASURED)}
                {badge(LABEL_MEASURED_CRYPTOLYZER, BADGE_MEASURED)}
                {badge(
                    "Calculated · Assessment Engine",
                    BADGE_CALCULATED,
                )}
                {badge(
                    "Projected · Migration Guidance",
                    BADGE_PROJECTED,
                )}
                {badge("Validated · Test Suite", BADGE_VALIDATED)}
            </div>
        </div>
        """
    )
