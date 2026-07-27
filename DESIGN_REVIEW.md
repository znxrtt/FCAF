# Design Review — Crypto Agility Command Center

## 1. Baseline

```
python -m pytest -q -p no:cacheprovider
130 passed in 0.49s
```

Matched the expected 130-test baseline exactly. No regex-based protocol
scanner existed anywhere in the repository prior to this review.

## 2. Critical defects found (baseline)

1. Line-join bug in `app.py`'s HTML compaction glued wrapped prose
   together ("...onlywhen the component matches").
2. Uploaded evidence temp files were created with `delete=False` and
   never removed — permanent leak per assessment run.
3. Malformed-but-valid JSON (e.g. a top-level array) raised an uncaught
   `AttributeError`, surfacing a raw traceback to the user.
4. No Reset Assessment control existed.
5. `years_until_crqc` was clamped to 0 for display even when the CRQC
   year had already passed, hiding how overdue migration already was.
6. Algorithm assets with zero assessable dimensions were silently
   dropped from the report (`continue`), indistinguishable from an
   asset that never existed.
7. A single occurrence path matching multiple markers with different
   component names silently resolved to the first dictionary entry
   instead of reporting an ambiguous state.

## 3. Security findings (baseline)

1. Evidence-derived values (CBOM tool name/version, timestamps, asset
   names, occurrence paths, relationship fields) were interpolated into
   `unsafe_allow_html=True` HTML with no escaping — a crafted CBOM value
   containing `<img onerror=...>` would execute in the analyst's browser.
2. No upload size cap, no JSON nesting-depth guard, no schema/type
   validation before use.
3. Internal tempfile paths could leak into error messages shown to the
   user.
4. `sonar-project.properties` contained a plaintext Sonar token
   committed to the file, not excluded by `.gitignore`.

## 4. Changes made

### Security (`sonar-project.properties`)
- Removed the plaintext `sonar.token` value entirely. Replaced with a
  comment directing the token to be supplied via `SONAR_TOKEN` or
  `-Dsonar.token=` at scan time. The token was not printed, copied, or
  placed in any other file. This repository is not a Git repository, so
  no history inspection was possible or needed — the token was removed
  from the only place it existed.

### Backend (methodology-preserving, additive only)
- **`parsers.py`**: added `resolve_component_for_path` /
  `resolve_component_for_asset`, which report an explicit
  `matched` / `unmapped` / `ambiguous` status instead of silently
  picking the first dictionary entry. The existing
  `get_component_for_path` / `get_component_for_asset` remain as thin
  backward-compatible wrappers (unchanged return contract, so all 130
  original tests and their assumptions still hold).
- **`report_generator.py`**:
  - Uses the new ambiguity-aware resolution; unmapped/ambiguous assets
    get an explicit `"Unmapped"`/`"Ambiguous"` component label,
    `component_status`, and `component_reason` field, and never receive
    a real payment weight or borrowed CryptoLyzer evidence.
  - Assets with zero assessable dimensions are now preserved as an
    explicit report entry (`status: "Not Assessed"`, `excluded_reason`,
    `maturity: None`, `priority: None`) instead of being dropped. No
    formula requiring a numeric maturity is ever invoked for them.
  - CRQC display now reports `years_until_crqc_z` (legacy, clamped to 0
    for backward compatibility), plus explicit `crqc_status`
    (`"upcoming"`/`"passed"`) and `years_overdue`, so an already-passed
    CRQC year is never presented as an ambiguous "0 years remaining."
    The urgency verdict (`rules.mosca_urgent`) already used the
    unclamped difference; the display fields now describe the same
    interpretation.
  - Report sort now handles `priority: None` (Not Assessed assets sort
    to the end instead of raising `TypeError`).
- **`cryptolyzer_parser.py`**: `detect_hybrid` no longer searches the
  whole serialized JSON document for marker words (which could
  false-positive on a hostname like `pqc-test.example.com`). It now
  only inspects a scoped set of negotiated-group/curve fields
  (`groups`, `curves`, `key_exchange_groups`, `negotiated_group`). The
  current raw CryptoLyzer fixture format (`versions` only) provides no
  such field, so hybrid correctly reports `False` rather than guessing.
  Documented in-code which CryptoLyzer analyzer output would be needed
  for real hybrid/PQC evidence.
- **`report_exporter.py`** / **`main.py`**: updated defensively so the
  new `status`/`component_status` fields export to CSV, and so
  `impact_chain: None` (for excluded assets) doesn't crash the None-unsafe
  `.get(..., {})` pattern.

No existing test was changed to make it pass, no fixture was altered, and
no test was deleted. All fixes were verified by *adding* new tests.

### New tests (25 added, 179 total)
- `tests/test_parsers.py`: ambiguous single-path/multi-marker resolution,
  ambiguous cross-location resolution, unmapped-with-reason.
- `tests/test_report.py`: unmapped-asset full pipeline, ambiguous-component
  full pipeline, CryptoLyzer-component-mismatch full pipeline,
  fully-unassessed-asset preservation, Not-Assessed assets sort after
  assessed assets, CRQC upcoming/passed/reached-this-year display.
- `tests/test_cryptolyzer_parser.py` (new file — this module previously
  had no direct tests): version normalization, hybrid true-positive via
  scoped fields, hybrid false-positive guards (missing field, hostname
  containing "pqc"/"hybrid", unrelated metadata text), end-to-end
  `parse_cryptolyzer_output`.
- `tests/test_ui_helpers.py` (new file): HTML escaping (script tags,
  attribute breakout, non-string values), text-spacing preservation
  across wrapped lines, upload validation (valid/malformed/non-object/
  oversized/deeply-nested/missing-required-keys/UTF-16), validation
  summary loading (missing/malformed/incomplete/valid).

### `app.py` (rewritten) and new `ui_helpers.py`
- **Line-join fix**: `ui_helpers.compact_html` joins lines with a single
  space instead of no separator, so wrapped prose never glues words
  together, while collapsing all whitespace between tags (no Markdown
  code-block leakage). Verified with dedicated tests and live in the
  browser.
- **HTML escaping**: `ui_helpers.escape()` (stdlib `html.escape`) is used
  by every shared component (`badge`, `metric_card`, `dimension_card`)
  and at every remaining raw-HTML interpolation site (CBOM metadata,
  asset/component names, occurrence paths, target address/port, flight
  plan steps). No `st.markdown(..., unsafe_allow_html=True)` call
  interpolates an unescaped evidence value.
- **Upload validation**: `ui_helpers.validate_uploaded_json` enforces a
  5&nbsp;MB per-file cap (matching a new `.streamlit/config.toml`
  `maxUploadSize = 5` so the uploader's own UI hint is accurate), decodes
  UTF-8/UTF-8-BOM/UTF-16 safely, parses JSON with a friendly line/column
  error instead of a raw traceback, rejects documents nested beyond 40
  levels (iterative depth check, no unbounded recursion), rejects
  non-object top-level JSON, and checks required keys
  (`components` for the CBOM, `component` for CryptoLyzer evidence).
- **Temp-file cleanup**: `temp_evidence_files()` is a context manager
  that always removes every temp file in a `finally` block, whether or
  not `generate_report` raises. No temp path is ever shown to the user.
- **Friendlier error handling**: malformed-but-valid JSON, wrong types,
  and missing keys all now produce one user-safe message
  ("Confirm the files match the expected... formats") instead of
  interpolating the raw exception (which could include a filesystem
  path or the AttributeError's internal repr).
- **Reset Assessment**: a dedicated sidebar button clears
  `assessment_report`/`cbom_data`/`component_mapping_data`/
  `cryptolyzer_data` from session state and reruns — verified live to
  return the app to the empty state without touching the already-
  selected upload widgets.
- **Evidence persists across navigation**: confirmed live — after
  running an assessment, navigating through all seven pages continues
  to read from `st.session_state`, never re-prompting for upload.
- **Navigation**: replaced the CSS-hacked `st.radio` (`:has(input:checked)`
  selectors tied to Streamlit's internal radiogroup DOM) with native
  `st.button(type="primary"/"secondary")` per page, driven by
  `st.session_state["workspace_page"]`. This uses Streamlit's own
  documented button/type API instead of undocumented internal DOM
  structure, and visually shows a clear active/hover state with no
  circular selectors.
- **Page consolidation (implemented as approved)**: 9 pages → 7 —
  *Command Center, Evidence Vault, Maturity Explorer, Priority Queue,
  Migration Planner, Validation Lab, Reports*. Scenario Lab is now a
  "Scenarios" tab inside Migration Planner (renamed from Migration
  Advisor); Evidence Monitor's coverage/status/re-scan-checklist content
  is now a "Coverage & Re-scan" tab inside Evidence Vault. No
  functionality was removed — the "Not Assessed" reasons table was added
  to this tab as a new, more precise replacement for the vaguer prior
  "Not Assessed" metric.
- **D1–D4 dual classification**: each Maturity Explorer dimension card
  now shows both `CALCULATED · D1` (the score itself) and a distinct
  `Evidence: MEASURED · ...` line naming the underlying measured source,
  exactly matching the requested format.
- **Badge misuse fixed**: "HNDL · Monitor" and "Recommended" no longer
  reuse the `VALIDATED` badge; both now use a new neutral/slate
  `badge-neutral` class, visually distinct from genuinely test-backed
  validated content.
- **Validation Lab**: no longer hardcodes "130 tests." It loads
  `validation_summary.json` via `ui_helpers.load_validation_summary`,
  which validates required keys and returns `None` for anything
  missing/malformed — the UI then shows "Validation summary
  unavailable" with the exact regeneration command, rather than a stale
  or fabricated count. `generate_validation_summary.py` is a new,
  explicit, manually-run script (never invoked by the dashboard) that
  runs pytest once, parses per-file pass/fail counts, and writes the
  summary. The required disclaimer sentence is unchanged and always
  shown regardless of summary availability.
- **Reports**: added "Download Migration Plan" (a presentation-only
  derivation of already-calculated `recommendations`/`impact_chain`
  fields already in the report — no new methodology) and
  "Download Validation Summary" (shown only when a summary is
  available).
- **Code quality**: centralized page-name/badge-type/default-setting
  constants, HTML escaping, and the compact-HTML renderer in
  `ui_helpers.py`; added focused type hints there; removed the global
  `st.markdown` monkey-patch in favor of one explicit `render_html()`
  call site convention throughout `app.py`.

## 5. Manual verification (Streamlit, port 8502)

Ran `python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502`
and drove it in a real browser:
- Empty state renders with correct badges (including a live
  `VALIDATED · 179 / 179` badge from the generated summary) and no
  glued-together words.
- Uploaded the three `test_data/` fixtures (CBOM, component mapping,
  CryptoLyzer evidence) and ran "Analyze evidence" — assessment
  completed for 1 algorithm asset, matching the CLI/test behavior.
- Inspected all seven pages: Command Center (metrics, evidence
  pipeline, highest-priority panel), Evidence Vault (all six tabs
  including the merged Coverage & Re-scan tab), Maturity Explorer
  (dual-classified D1–D4 cards, Not Assessed D4 explanation), Priority
  Queue (transparent formula), Migration Planner (Flight Plan +
  Scenarios tabs, neutral "Recommended" badge), Validation Lab (live
  179/179 summary, per-module table, required disclaimer), Reports
  (all six downloads, evidence classification badges).
- Reset Assessment returned the app to the empty state and preserved
  the already-selected upload widgets.
- No console errors; only pre-existing Streamlit deprecation notices
  (`use_container_width`) and a resolved pyarrow dtype warning
  (mixed int/"Not Assessed" string columns now cast to `str` for
  DataFrame display).

## 6. Known limitations

- `use_container_width` is deprecated in the installed Streamlit
  version (superseded by `width=`); left as-is since it still functions
  correctly and changing it is a cosmetic/version-currency concern
  outside this review's scope.
- `test_data/cbom.json` only covers one of the five
  `payment_simulation/` files (the PKI asset). This was flagged in the
  baseline report as a data-coverage gap; per instructions,
  `test_data/` was not modified.
- The recommendation text remains dimension-generic (not tied to the
  specific detected algorithm/OID) — a real but non-critical limitation
  noted in the baseline report; changing this would touch
  `recommendation_engine.py`'s content, which was out of scope for this
  pass.
- Sidebar navigation buttons style via `[data-testid="stButton"]`
  attribute selectors rather than Streamlit's newer `st.navigation`/
  `st.page_link` API, to avoid a larger multi-page-app restructure;
  this is materially more durable than the previous `:has(input:checked)`
  radiogroup hack but is still coupled to Streamlit's `data-testid`
  contract.

## 7. Confirmations

- Original 130-test baseline preserved and expanded to **179 passing
  tests** (`python -m pytest -q -p no:cacheprovider`).
- No regex-based protocol scanning was reintroduced anywhere in the
  repository (verified by repo-wide search before and after changes).
- No production or company evidence was added; only synthetic fixtures
  already present in `test_data/`/`payment_simulation/` were used for
  manual UI verification, and neither directory was modified.
- No existing test was deleted or altered to force a pass.

## 8. Running the reviewed dashboard

```
python -m pip install -r requirements.txt   # if not already installed
python generate_validation_summary.py       # optional: populates Validation Lab
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

Upload `test_data/cbom.json`, `test_data/component_mapping.json`, and
`test_data/cryptolyzer_evidence.json` from the sidebar, then click
"Analyze evidence."
