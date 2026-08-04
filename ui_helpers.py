"""
Shared presentation helpers for app.py.

Kept separate from the assessment engine (parsers.py, rules.py,
maturity_engine.py, report_generator.py, ...) so presentation
concerns never influence the validated scoring methodology.
"""

import base64
import html
import json
from functools import lru_cache
from textwrap import dedent
from typing import Any, Iterable, Optional


# -------------------------------------------------------------------
# Page / navigation constants
# -------------------------------------------------------------------

PAGE_COMMAND_CENTER = "Overview"
PAGE_EVIDENCE_VAULT = "Collect"
PAGE_MAP = "Map"
PAGE_MATURITY_EXPLORER = "Assess"
PAGE_PRIORITY_QUEUE = "Prioritise"
PAGE_MIGRATION_PLANNER = "Plan"
PAGE_VALIDATION_LAB = "Validate"

PAGES = (
    PAGE_COMMAND_CENTER,
    PAGE_EVIDENCE_VAULT,
    PAGE_MAP,
    PAGE_MATURITY_EXPLORER,
    PAGE_PRIORITY_QUEUE,
    PAGE_MIGRATION_PLANNER,
    PAGE_VALIDATION_LAB,
)

# Steps that carry a visible sequence number in the workflow stepper.
# Overview is the unnumbered landing/home state.
WORKFLOW_STEPS = (
    {"key": PAGE_COMMAND_CENTER, "number": None, "label": "Overview"},
    {"key": PAGE_EVIDENCE_VAULT, "number": 1, "label": "Collect"},
    {"key": PAGE_MAP, "number": 2, "label": "Map"},
    {"key": PAGE_MATURITY_EXPLORER, "number": 3, "label": "Assess"},
    {"key": PAGE_PRIORITY_QUEUE, "number": 4, "label": "Prioritise"},
    {"key": PAGE_MIGRATION_PLANNER, "number": 5, "label": "Plan"},
    {"key": PAGE_VALIDATION_LAB, "number": 6, "label": "Validate"},
)

NAV_STATE_KEY = "workspace_page"


# -------------------------------------------------------------------
# Framework branding constants
# -------------------------------------------------------------------

FRAMEWORK_NAME = "FCAF"
FRAMEWORK_FULL_NAME = "Financial Crypto Agility Assessment Framework"
FRAMEWORK_MISSION = (
    "Evidence-Driven Crypto Agility Assessment for "
    "Quantum-Safe Financial System Planning"
)
FRAMEWORK_POSITIONING = (
    "Domain-Independent Assessment Methodology",
    "Implemented & Validated Case Study: Payment Systems",
)
FRAMEWORK_TAGLINE = (
    "Domain-Independent Crypto Agility Assessment "
    "· Validated Payment Systems Case Study"
)
AUTHOR_NAME = "Saleh Ahmed Alrasheed"
MENTOR_NAME = "Vijayaraghavan Varadharajan"
ORG_NAME = "Infosys"

BUSINESS_CRITICALITY_LABEL = "Business Criticality Weight"

LOGO_PATH = "assets/infosys_logo.png"


@lru_cache(maxsize=1)
def _load_logo_data_uri(path: str = LOGO_PATH) -> Optional[str]:
    """Reads and base64-encodes the local logo file for inline
    embedding in rendered HTML. Returns None (never raises) for
    any missing or unreadable file, so the header can fall back
    to a text badge instead of breaking the dashboard."""

    try:
        with open(path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode("ascii")
    except OSError:
        return None

    return f"data:image/png;base64,{encoded}"


# -------------------------------------------------------------------
# Evidence classification constants
# -------------------------------------------------------------------

BADGE_MEASURED = "measured"
BADGE_CALCULATED = "calculated"
BADGE_PROJECTED = "projected"
BADGE_VALIDATED = "validated"
BADGE_URGENT = "urgent"
BADGE_NEUTRAL = "neutral"

LABEL_MEASURED_CBOMKIT = "Measured · CBOMKit"
LABEL_MEASURED_CRYPTOLYZER = "Measured · CryptoLyzer"
LABEL_CALCULATED_MATURITY = "Calculated · Maturity"
LABEL_PROJECTED_IMPACT = "Projected · Impact Chain"


# -------------------------------------------------------------------
# Assessment default settings
# -------------------------------------------------------------------

DEFAULT_CRQC_YEAR = 2033
DEFAULT_BASE_MIGRATION_YEARS = 3.0
DEFAULT_DATA_RETENTION_YEARS = 7.0


# -------------------------------------------------------------------
# Upload / JSON validation limits
# -------------------------------------------------------------------

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB per evidence file
MAX_JSON_DEPTH = 40


class EvidenceValidationError(ValueError):
    """Raised for any evidence upload that fails validation.

    Always carries a user-safe message with no internal paths or
    raw exception internals, so callers can show it directly.
    """


def _decode_json_bytes(raw_bytes: bytes) -> Any:
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise EvidenceValidationError(
            "The file is not valid UTF-8 or UTF-16 text."
        )

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise EvidenceValidationError(
            f"The file is not valid JSON (line {error.lineno}, "
            f"column {error.colno})."
        ) from error


def _json_depth(value: Any, limit: int) -> int:
    """
    Iteratively computes the maximum nesting depth of a decoded
    JSON value, bailing out as soon as `limit` is exceeded so a
    maliciously deep document cannot cause runaway recursion.
    """

    stack = [(value, 1)]
    deepest = 0

    while stack:
        current, depth = stack.pop()

        if depth > limit:
            return depth

        deepest = max(deepest, depth)

        if isinstance(current, dict):
            stack.extend(
                (item, depth + 1)
                for item in current.values()
            )
        elif isinstance(current, list):
            stack.extend(
                (item, depth + 1)
                for item in current
            )

    return deepest


def validate_uploaded_json(
    uploaded_file,
    max_bytes: int = MAX_UPLOAD_BYTES,
    max_depth: int = MAX_JSON_DEPTH,
    required_keys: Optional[Iterable[str]] = None,
) -> Any:
    """
    Validates an uploaded Streamlit file before it is trusted as
    evidence: enforces a size cap, decodes safely, parses JSON
    with a friendly error on malformed input, rejects excessively
    nested documents, and confirms the top-level shape is a JSON
    object with any required keys present.

    Never executes, imports, or evaluates the uploaded content.
    """

    raw_bytes = uploaded_file.getvalue()

    if len(raw_bytes) > max_bytes:
        raise EvidenceValidationError(
            f"'{uploaded_file.name}' is "
            f"{len(raw_bytes) / (1024 * 1024):.1f} MB, which "
            f"exceeds the {max_bytes / (1024 * 1024):.0f} MB "
            "upload limit."
        )

    data = _decode_json_bytes(raw_bytes)

    if _json_depth(data, max_depth) > max_depth:
        raise EvidenceValidationError(
            f"'{uploaded_file.name}' is nested more than "
            f"{max_depth} levels deep and was rejected."
        )

    if not isinstance(data, dict):
        raise EvidenceValidationError(
            f"'{uploaded_file.name}' must contain a JSON object "
            "at the top level."
        )

    if required_keys:
        missing = [
            key
            for key in required_keys
            if key not in data
        ]

        if missing:
            raise EvidenceValidationError(
                f"'{uploaded_file.name}' is missing required "
                f"field(s): {', '.join(missing)}."
            )

    return data


# -------------------------------------------------------------------
# Safe HTML rendering
# -------------------------------------------------------------------

def escape(value: Any) -> str:
    """
    Escapes any evidence-derived value before it is placed inside
    an HTML string rendered with unsafe_allow_html=True.

    None becomes an empty string; every other value is converted
    to str() first so numbers/lists/etc. are always safe to embed.
    """

    if value is None:
        return ""

    return html.escape(str(value), quote=True)


def escape_join(values: Iterable[Any], separator: str = ", ") -> str:
    return separator.join(
        escape(value)
        for value in values
    )


def compact_html(content: str) -> str:
    """
    Collapses a hand-indented, multi-line HTML template into a
    single line so Streamlit's Markdown renderer never mistakes
    the leading whitespace for a fenced code block.

    Unlike a naive strip-and-join, this preserves a single space
    between text that wraps across source lines (e.g. prose
    inside a <div>), so words are never glued together, while
    still fully collapsing whitespace between tags.
    """

    lines = [
        line.strip()
        for line in dedent(content).splitlines()
    ]

    lines = [line for line in lines if line]

    return " ".join(lines)


def render_html(content: str, container=None) -> None:
    """Renders pre-built, already-escaped HTML safely and compactly."""

    import streamlit as st

    target = container or st

    target.markdown(
        compact_html(content),
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# Reusable presentation components
# -------------------------------------------------------------------

def badge(label: str, badge_type: str) -> str:
    return (
        f'<span class="badge badge-{escape(badge_type)}">'
        f'{escape(label)}'
        f'</span>'
    )


def metric_card(value: Any, title: str, note: str, accent: str) -> str:
    return (
        f'<div class="metric-card accent-{escape(accent)}">'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-title">{escape(title)}</div>'
        f'<div class="metric-note">{escape(note)}</div>'
        f'</div>'
    )


def dimension_card(
    dimension_id: str,
    dimension_label: str,
    score_display: str,
    evidence_source: str,
) -> str:
    """
    Renders a D1–D4 dimension card that shows both classifications
    at once: the score itself is CALCULATED, and the evidence it
    was calculated from is MEASURED (or stated plainly when
    unavailable, never implied).
    """

    return (
        '<div class="dimension-card">'
        f'<div class="dimension-name">{escape(dimension_label)}</div>'
        '<div class="badge-row dimension-badge-row">'
        f'{badge("Calculated · " + dimension_id, BADGE_CALCULATED)}'
        '</div>'
        f'<div class="dimension-score">{escape(score_display)}</div>'
        '<div class="dimension-source">'
        f'Evidence: {escape(evidence_source)}'
        '</div>'
        '</div>'
    )


def display_score(score: Any) -> Any:
    if score is None:
        return "Not Assessed"

    return score


def render_header(status_label: str) -> None:
    """Renders the executive branding header (logo, framework name,
    author/mentor/org, assessment status).

    Uses the real Infosys logo (assets/infosys_logo.png) when it can
    be read; falls back to a text badge otherwise so the dashboard
    never breaks on a missing asset."""

    logo_data_uri = _load_logo_data_uri()

    logo_html = (
        f'<img class="brand-logo-img" src="{logo_data_uri}" '
        f'alt="{escape(ORG_NAME)} logo">'
        if logo_data_uri
        else f'<div class="brand-logo-badge">{escape(ORG_NAME.upper())}</div>'
    )

    positioning_html = "<br>".join(
        escape(line) for line in FRAMEWORK_POSITIONING
    )

    render_html(
        f"""
        <div class="brand-header">
            {logo_html}
            <div class="brand-main">
                <div class="brand-title">
                    {escape(FRAMEWORK_FULL_NAME)}
                    ({escape(FRAMEWORK_NAME)})
                </div>
                <div class="brand-subtitle">
                    {escape(FRAMEWORK_MISSION)}
                </div>
                <div class="brand-subline">
                    {positioning_html}
                </div>
            </div>
            <div class="brand-meta">
                <div class="brand-meta-item">
                    <span class="brand-meta-label">Author</span>
                    <span class="brand-meta-value">
                        {escape(AUTHOR_NAME)}
                    </span>
                </div>
                <div class="brand-meta-item">
                    <span class="brand-meta-label">Mentor</span>
                    <span class="brand-meta-value">
                        {escape(MENTOR_NAME)}
                    </span>
                </div>
                <div class="brand-meta-item">
                    <span class="brand-meta-label">Organization</span>
                    <span class="brand-meta-value">
                        {escape(ORG_NAME)}
                    </span>
                </div>
                <div class="brand-meta-item">
                    <span class="brand-meta-label">Status</span>
                    <span class="brand-meta-value">
                        {escape(status_label)}
                    </span>
                </div>
            </div>
        </div>
        """
    )


def render_stepper(steps: Iterable[dict], current_key: str) -> None:
    """Renders the read-only visual step-track (numbered pills with
    connecting line). Actual navigation is driven separately by real
    st.button controls, since raw HTML cannot trigger Streamlit
    callbacks."""

    current_index = next(
        (
            index
            for index, step in enumerate(steps)
            if step["key"] == current_key
        ),
        0,
    )

    pill_items = []

    for index, step in enumerate(steps):
        if index < current_index:
            state = "completed"
        elif index == current_index:
            state = "active"
        else:
            state = "upcoming"

        number_html = (
            f'<span class="step-pill-number">{step["number"]}</span>'
            if step["number"] is not None
            else '<span class="step-pill-number">&#9670;</span>'
        )

        pill_items.append(
            f'<div class="step-pill {state}">'
            f"{number_html}"
            f'<span class="step-pill-label">'
            f'{escape(step["label"])}'
            f"</span>"
            f"</div>"
        )

    render_html(
        f"""
        <div class="stepper-track">
            {''.join(pill_items)}
        </div>
        """
    )


# -------------------------------------------------------------------
# Validation summary loading
# -------------------------------------------------------------------

VALIDATION_SUMMARY_REQUIRED_KEYS = (
    "generated_at",
    "total_tests",
    "passed",
    "failed",
    "duration_seconds",
    "category_counts",
)


def load_validation_summary(path: str = "validation_summary.json"):
    """
    Loads and validates validation_summary.json, generated by
    running `python generate_validation_summary.py` — never by
    the dashboard itself.

    Returns None (rather than raising) for any missing, malformed,
    or structurally invalid file, so the caller can show
    "Validation summary unavailable" instead of a stale or
    hardcoded test count.
    """

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    if any(key not in data for key in VALIDATION_SUMMARY_REQUIRED_KEYS):
        return None

    if not isinstance(data.get("category_counts"), dict):
        return None

    return data
