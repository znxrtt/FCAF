# FCAF Verified Technical Facts

Audit-grade fact pack for the internal technical paper on the Financial Crypto Agility
Assessment Framework (FCAF). Every claim below is traced to a repository path and, where
applicable, a function/class/test name. Facts are ordered by the authority hierarchy
specified for this review: (1) current Python source, (2) current automated tests,
(3) current `assessment_report.csv`, (4) current `validation_summary.json`,
(5) `evidence_samples/*` case-study evidence, (6) existing documentation (lowest authority).

Repository root: `crypto-agility-review/` (paths below are relative to it unless stated
otherwise).

---

## 1. Repository Overview

- **Dashboard entry point**: `app.py` — a Streamlit application (`st.set_page_config(...)`,
  `app.py:62-67`). It imports `generate_report` from `report_generator.py` (`app.py:12`) and
  a large set of presentation helpers from `ui_helpers.py` (`app.py:13-55`). It is the only
  interactive/GUI surface in the repository.
- **CLI/batch entry point**: `main.py` — a plain-Python script (no `if __name__` guard; it
  runs top-level on import) that calls `generate_report()` against the fixed root-level
  evidence files `cbom.json`, `component_mapping.json`, `cryptolyzer_evidence.json`
  (`main.py:24-32`), then writes `assessment_report.json` and `assessment_report.csv` via
  `report_exporter.save_json_report` / `save_csv_report` (`main.py:54-62`), and prints a
  full per-asset report to stdout.
- **`app.py` vs `main.py`**: `app.py` is the evidence-upload-driven, session-based dashboard
  (accepts any uploaded CBOM/mapping/CryptoLyzer file via `st.file_uploader`, `app.py:1211-
  1227`); `main.py` is a fixed-file batch runner used to regenerate the root
  `assessment_report.json`/`.csv` from the root evidence files. They both call the same
  `generate_report()` engine in `report_generator.py`, so scoring logic is not duplicated,
  but each produces its CSV via a **different exporter** (see Section 11 — this is a
  documented discrepancy, not a duplication of the engine itself).
- **Core engine modules** (no Streamlit or CLI dependency):
  - `parsers.py` — CBOM/CryptoLyzer-adjacent loading, asset extraction, OID→location
    mapping, component-mapping resolution.
  - `cryptolyzer_parser.py` — CryptoLyzer raw-output parsing/normalization.
  - `rules.py` — D1–D4 scoring functions, confidence, algorithm risk, priority formula,
    Mosca/HNDL formulas, business-criticality weights (`PAYMENT_WEIGHTS`).
  - `maturity_engine.py` — `calculate_maturity()`, combines D1–D4 into a maturity level,
    binding constraints, confidence.
  - `recommendation_engine.py` — maps binding constraints to canned recommendation text.
  - `impact_chain.py` — simulates sequential application of recommendations to project a
    future maturity level.
  - `report_generator.py` — `generate_report()`, the single orchestration function used by
    both `main.py` and `app.py`.
  - `report_exporter.py` — `save_json_report()` / `save_csv_report()` (full-fidelity export,
    used only by `main.py`/tests).
  - `ui_helpers.py` — presentation-only constants/helpers (badges, HTML escaping, upload
    validation, `display_score`), explicitly documented as kept separate from the scoring
    engine (`ui_helpers.py:1-7`).
  - `generate_validation_summary.py` — a manually-run script that executes `pytest -v` and
    writes `validation_summary.json`; never invoked by `app.py` itself
    (`generate_validation_summary.py:1-10`, confirmed by `ui_helpers.load_validation_summary`
    doc-comment, `ui_helpers.py:496-506`).
- **Input evidence files actually consumed by the engine**: a CycloneDX 1.6 CBOM JSON
  (`load_cbom`, `parsers.py:13-14`), a component-mapping JSON (marker → component name,
  `load_component_mapping`, `parsers.py:238-247`), and a normalized CryptoLyzer evidence JSON
  (`load_cryptolyzer_evidence`, `parsers.py:510-516`). The case-study copies are
  `evidence_samples/cbom_multi_location.json`, `component_mapping.json`,
  `cryptolyzer_evidence.json` (root).
- **Generated output files**: `assessment_report.json`, `assessment_report.csv` (via
  `main.py`/`report_exporter.py`), and in-session CSV/plan downloads from `app.py`
  (`build_csv_bytes`, `build_migration_plan`, `app.py:1118-1161`). `validation_summary.json`
  is generated separately by `generate_validation_summary.py`.
- **Test configuration**: `pytest.ini` — `testpaths = tests`, `python_files = test_*.py`,
  `python_functions = test_*`, excludes `archive`, `old_code_archive`, `venv`, `.git`
  (`pytest.ini:1-5`).
- **Key external dependencies** (`requirements.txt`): `streamlit`, `pandas`, `altair`
  (dashboard/charting); `CryptoLyzer==1.3.0`, `CryptoParser==1.3.0`, `CryptoDataHub==1.3.0`,
  `cryptography==49.0.0`, `asn1crypto`, `certvalidator` (used by the standalone
  local-TLS-server/evidence-generation tooling under `local_test/`, not imported by the
  scoring engine itself); `pytest` is not pinned in the visible excerpt but is required to
  run `tests/`.
- Not part of this review's scope (per instructions, not used as case-study input): root
  `cbom.json`, `test_data/`, `.claude/worktrees/`, `__pycache__/`, `.pytest_cache/`.

---

## 2. End-to-End Implemented Data Flow

All stages below are driven from a single function, `generate_report()` in
`report_generator.py:169-530`, called identically by `main.py:43-53` and `app.py:1373-1381`.

| Stage | Source file / function | Input | Output | Classification |
|---|---|---|---|---|
| 1. Load CBOM | `parsers.load_cbom` (`parsers.py:13`) | CBOM file path | parsed JSON dict | Measured (raw evidence) |
| 2. Extract algorithm/material assets | `parsers.get_crypto_assets` (`parsers.py:106-199`) | CBOM dict | list of asset dicts (`primitive`, `oid`, `locations`, `material_type`, ...) | Measured |
| 3. Build OID→location map | `parsers.build_oid_location_map` (`parsers.py:202-235`) | asset list | `{oid: set(normalized_paths)}` | Measured/derived |
| 4. Load component mapping | `parsers.load_component_mapping` (`parsers.py:238`) | mapping file path | `{marker: component_name}` dict | Configuration input |
| 5. Load CryptoLyzer evidence | `parsers.load_cryptolyzer_evidence` (`parsers.py:510`) | evidence file path | parsed JSON dict | Measured |
| 6. Resolve component per asset | `parsers.resolve_component_for_asset` (`parsers.py:393-482`), wrapped by `report_generator._resolve_component` (`report_generator.py:40-65`) | asset locations + mapping | `matched` / `unmapped` / `ambiguous` status + component name | Calculated (deterministic path matching) |
| 7. Resolve business-criticality weight | `rules.get_payment_weight` (`rules.py:17-18`) | matched component name | float weight (0.0 if unmapped/ambiguous) | Configuration input |
| 8. Match CryptoLyzer evidence to asset | `report_generator.generate_report`, inline (`report_generator.py:258-298`) | resolved component + CryptoLyzer `component` field | `tls_version`, `hybrid`, `source`, `target` or all-None | Measured, conditionally withheld |
| 9. Score D1 | `rules.coordination_score` (`rules.py:48-58`) | `primitive` | 1–4 or `None` | Calculated |
| 10. Score D2 | `rules.pervasiveness_score` (`rules.py:73-86`) | OID location count | 1–4 or `None` | Calculated |
| 11. Score D3 | `rules.protocol_score` (`rules.py:100-123`) | `tls_version`, `hybrid` | 1–4 or `None` | Calculated |
| 12. Score D4 | `rules.material_score` (`rules.py:141-168`) | `material_type`, `primitive` | 1–4 or `None` | Calculated |
| 13. Combine into maturity | `maturity_engine.calculate_maturity` (`maturity_engine.py:11-90`) | D1–D4 | `maturity` = min of assessed dims, or `{"status": "Not Assessed"}` if none scored | Calculated |
| 14. Confidence | `rules.confidence` (`rules.py:179-184`) | count of assessed dimensions | "High"/"Medium"/"Low" | Calculated |
| 15. Binding constraints | inside `calculate_maturity` (`maturity_engine.py:75-79`) | assessed dims equal to maturity | list of dimension names | Calculated |
| 16. Algorithm risk | `rules.algorithm_risk` (`rules.py:191-215`) | asset name string | 2/3/4 | Calculated (name-pattern heuristic) |
| 17. Priority | `rules.calculate_priority` (`rules.py:222-223`) | risk, weight, maturity | `round(risk * weight * (5 - maturity), 2)` | Calculated |
| 18. Mosca adjusted migration time | `rules.adjusted_migration_time` (`rules.py:233-250`) | base years, maturity | `round(base * (1 + (4-L)/4), 2)` | Calculated (heuristic, explicitly documented "not empirically validated", `rules.py:227`) |
| 19. Mosca deadline | `rules.mosca_deadline` (`rules.py:253-265`) | CRQC year, adjusted X | `crqc_year - adjusted_x` | Calculated/projected |
| 20. Mosca/HNDL urgency | `rules.mosca_urgent` (`rules.py:268-297`) | retention years, adjusted X, CRQC year, assessment year | boolean | Calculated |
| 21. Recommendations | `recommendation_engine.get_recommendations` (`recommendation_engine.py:62-124`) | binding constraints + current level | list of `{dimension, current_level, target_level, recommendation}` | Prescriptive text, static lookup table |
| 22. Impact chain | `impact_chain.build_impact_chain` (`impact_chain.py:49-179`) | assessment + recommendations | simulated step-by-step maturity progression, `final_maturity` | **Projected**, not measured |
| 23. Assemble report row | `report_generator.generate_report` (`report_generator.py:381-516`) | all of the above | one dict per algorithm asset | Aggregated |
| 24. Sort by priority | `report_generator.generate_report` (`report_generator.py:522-528`) | report list | highest priority first; `Not Assessed` assets last | Presentation ordering |
| 25. Export | `report_exporter.save_json_report` / `save_csv_report` (`report_exporter.py:16-43`, `46-377`) — used by `main.py` only. `app.py` uses its own `build_csv_bytes`/`build_summary_rows` (`app.py:1079-1131`) for its in-browser CSV download. | report list | JSON/CSV files or in-memory bytes | Export |
| 26. Streamlit display | `app.py` (all `PAGE_*` branches, e.g. `app.py:1819` onward) | `st.session_state["assessment_report"]` | rendered dashboard pages | Presentation |

Only algorithm-type components (`asset_type == "algorithm"`) receive a maturity assessment;
related-crypto-material components are linked to algorithms via CycloneDX `dependencies`
and folded into D4 evidence, never scored standalone (`report_generator.py:234-235`,
`parsers.py:26-103`).

---

## 3. CBOM Parser and Evidence Model

- **CBOM shape consumed**: CycloneDX `components[]` with
  `cryptoProperties.assetType` of either `"algorithm"` or `"related-crypto-material"`
  (`parsers.py:106-199`, `parsers.py:26-60`). `evidence_samples/cbom_multi_location.json`
  declares `"bomFormat": "CycloneDX"`, `"specVersion": "1.6"`.
- **Algorithm component identification**: `crypto.get("assetType")` — only components whose
  `assetType == "algorithm"` are scored (`report_generator.py:234-235`); components whose
  `assetType == "related-crypto-material"` are only used to build the OID/material link map.
- **OID extraction**: `crypto.get("oid")` directly off `cryptoProperties.oid`
  (`parsers.py:173-174`).
- **Primitive/crypto-function extraction**: `algorithm.get("primitive")` and
  `algorithm.get("cryptoFunctions", [])` from `cryptoProperties.algorithmProperties`
  (`parsers.py:159-166`). `parameterSetIdentifier` is also captured (`parsers.py:168-171`)
  but not used by any D1–D4 rule directly.
- **Source-location extraction**: `component["evidence"]["occurrences"][*]["location"]`
  (`parsers.py:134-138`, `182-186`); `additionalContext` is captured too but only surfaced
  for display (`parsers.py:188-196`), not scored.
- **Related crypto-material linking**: `parsers.build_material_link_map`
  (`parsers.py:26-103`) walks the top-level CycloneDX `dependencies[]` array; a
  `related-crypto-material` component that a `dependencies` entry `dependsOn` links to an
  algorithm component transfers its `type`/`size` onto that algorithm's `material_type`/
  `material_size` fields (`parsers.py:144-147`, `176-181`). This is a `dependsOn`-direction
  walk, not a general graph traversal — it only handles the one-hop
  material→algorithm edge actually present in the sample CBOMs.
- **Fields that may become `Not Assessed`**: `d1` when `primitive` is unmapped or missing
  (`rules.coordination_score` returns `None`, `rules.py:58`); `d2` when `oid_location_count`
  is 0 (`rules.pervasiveness_score`, `rules.py:74-75`); `d3` when no `tls_version` is
  available (`rules.protocol_score`, `rules.py:105-106`); `d4` when `material_type`/
  `primitive` fall outside the four defined combinations (`rules.material_score` returns
  `None` at `rules.py:168`, distinct from the explicit "no material = Level 4" case at
  `rules.py:145-146`). If **all four** dimensions are `None`, `calculate_maturity` returns
  `{"status": "Not Assessed"}` (`maturity_engine.py:68-69`), and `report_generator` preserves
  that asset with `maturity: None`, `priority: None` rather than dropping it
  (`report_generator._build_excluded_entry`, `report_generator.py:99-166`; verified by
  `tests/test_report.py::test_report_fully_unassessed_asset_is_preserved_without_maturity`
  and `tests/test_maturity.py::test_all_dimensions_missing_returns_not_assessed`).
- **Normalization/dedup behavior**: `parsers.normalize_path` lower-cases, forward-slashes,
  and strips a file path before it is used as a dictionary key (`parsers.py:17-23`). The
  OID→location map is a `set`, so duplicate occurrence entries pointing at the same
  normalized path collapse to one distinct location and do not inflate the D2 count
  (`parsers.py:221-234`; exercised by `tests/test_parsers.py::test_oid_map_dedupes_same_normalized_location`
  and by `tests/test_mutations.py::test_duplicate_locations_do_not_change_d2`).

---

## 4. CryptoLyzer Processing

- **Expected raw input format**: a JSON document with a top-level `target` object
  (`scheme`, `address`, `ip`, `port`) and a `versions` array of raw version tokens
  (e.g. `"tls1_2"`) (`cryptolyzer_parser.py:154-196`). `load_cryptolyzer_output` tolerates
  `utf-8-sig` and `utf-16` encodings, documented as an artifact of PowerShell-redirected
  output (`cryptolyzer_parser.py:43-74`).
- **Normalized evidence format actually consumed by the engine** (distinct from the raw
  format above): `{"component": ..., "source": "cryptolyzer", "target": {...},
  "tls_version": "TLS1.2", "hybrid": false, "assessed": true}` — this is the *output* of
  `parse_cryptolyzer_output` (`cryptolyzer_parser.py:154-196`) and the actual shape of
  `cryptolyzer_evidence.json`.
- **Runtime-to-component matching**: `report_generator.generate_report` compares the
  resolved CBOM component name to `cryptolyzer_evidence.get("component")`; evidence is
  applied only if they match **and** the CBOM asset's own component resolution status is
  `"matched"` (`report_generator.py:258-268`). An unmapped or ambiguous CBOM asset can never
  match, by construction (comment at `report_generator.py:256-257`). Verified by
  `tests/test_report.py::test_report_cryptolyzer_component_mismatch_withholds_d3`.
- **TLS version normalization**: `cryptolyzer_parser.normalize_version` maps raw tokens
  (`ssl2`, `ssl3`, `tls1`, `tls1_0`, `tls1_1`, `tls1_2`, `tls1_3`) to display strings
  (`SSL2.0`...`TLS1.3`) (`cryptolyzer_parser.py:4-12`, `77-88`); `highest_tls_version` then
  picks the max-ranked version if the scan reported several (`cryptolyzer_parser.py:124-151`).
- **Hybrid/PQC capability representation**: `detect_hybrid` looks **only** inside four
  scoped fields — `groups`, `curves`, `key_exchange_groups`, `negotiated_group`
  (`HYBRID_EVIDENCE_FIELDS`, `cryptolyzer_parser.py:35-40`) — for marker substrings
  `kyber`, `mlkem`, `ml-kem`, `x25519kyber`, `hybrid`, `pqc` (`HYBRID_MARKERS`,
  `cryptolyzer_parser.py:15-22`). It deliberately does **not** scan the whole document, to
  avoid false positives from unrelated text such as a hostname containing "pqc"
  (`cryptolyzer_parser.py:91-103`; verified by
  `tests/test_cryptolyzer_parser.py::test_hybrid_false_positive_guard_hostname` and
  `::test_hybrid_false_positive_guard_unrelated_metadata`). The code explicitly documents
  that CryptoLyzer's TLS-versions analyzer (the only one reflected in the current raw
  fixture format) **cannot by itself** report hybrid/PQC capability — that would require the
  curve/group analyzer output (`cryptolyzer_parser.py:24-34`).
- **Unmatched runtime evidence handling**: if the CBOM asset's resolved component doesn't
  match the CryptoLyzer evidence's `component` field, `tls_version`/`hybrid`/`source`/
  `target` are all forced to `None`/`False` (`report_generator.py:294-298`) — D3 is withheld
  rather than borrowed from a mismatched component.
- **How D3 becomes `Not Assessed`**: `rules.protocol_score` returns `None` whenever
  `tls_version is None` (`rules.py:105-106`), which happens either because no CryptoLyzer
  evidence file was supplied, because `assessed` is `False`, or because of the
  component-mismatch withholding above.
- **Validation/authorization assumptions**: `parsers.load_cryptolyzer_evidence` docstring
  states it loads evidence "generated from an authorized CryptoLyzer endpoint scan"
  (`parsers.py:511-513`) — this is a documentation-level assumption; the code itself performs
  no authorization check, only JSON structural validation (`ui_helpers.validate_uploaded_json`,
  required key `"component"`, `app.py:1360-1363`).

---

## 5. D1–D4 Implementation

All four functions live in `rules.py` and are composed by `maturity_engine.calculate_maturity`
(`maturity_engine.py:11-90`).

### D1 — Migration Coordination Complexity
- **Question answered**: how many distinct parties must coordinate to complete a migration.
- **Evidence field**: `algorithmProperties.primitive` (`parsers.py:159-160` → `asset["primitive"]`).
- **Implementation**: `rules.coordination_score` (`rules.py:48-58`).
- **Thresholds**: `signature`→1, `pke`→2, `kem`/`keyagreement`→3, `hash`/`mac`/`kdf`→4;
  anything else→`None` (Not Assessed).
- **Tests**: `tests/test_rules.py::test_d1_signature_returns_level_1`,
  `::test_d1_pke_returns_level_2`, `::test_d1_kem_and_keyagreement_return_level_3`,
  `::test_d1_hash_mac_kdf_return_level_4`, `::test_d1_unknown_primitive_is_not_assessed`.

### D2 — Implementation Pervasiveness (deep dive per review request)
- **Question answered**: how scattered a specific algorithm OID is across the observed
  codebase — a proxy for cryptographic modularity.
- **Evidence fields**: `evidence.occurrences[*].location` for every CBOM component sharing
  the same `algorithmProperties`-level `oid` (not just the current asset's own occurrences).
- **Location counting**: `parsers.build_oid_location_map` (`parsers.py:202-235`) iterates
  **every** `asset_type == "algorithm"` component, groups by `oid`, and adds each
  `normalize_path(location)` into a **`set`** per OID — so duplicate occurrences of the same
  normalized path collapse to one, and locations are deduplicated *per OID*, not per
  individual component record. `report_generator.py:300-312` then reads
  `len(oid_location_map.get(oid, set()))` as `oid_location_count`.
- **Implementation**: `rules.pervasiveness_score(location_count)` (`rules.py:73-86`).
- **Current thresholds** (in-code comment, `rules.py:68-71`): `>=5` locations → Level 1
  (most scattered/worst); `3–4` locations → Level 2; exactly `2` → Level 3; exactly `1` →
  Level 4 (most localized/best). `0`/`None` → `None` (Not Assessed).
- **Why RSA-2048 scores D2 = 2 in the current case study**: in
  `evidence_samples/cbom_multi_location.json`, the algorithm component `RSA-2048`
  (`oid` = `1.2.840.113549.1.1.1`) is the `dependsOn` target of three separate
  `related-crypto-material` components whose own occurrences are at
  `payment_simulation/pki/key_manager.py`, `payment_simulation/pki/certificate_manager.py`,
  and `payment_simulation/pki/key_rotation_service.py`. `RSA-2048`'s own component record
  also lists all three as `evidence.occurrences` directly (see the file's `RSA-2048`
  component). `build_oid_location_map` therefore yields
  `oid_location_map["1.2.840.113549.1.1.1"] = {".../key_manager.py",
  ".../certificate_manager.py", ".../key_rotation_service.py"}`, i.e. 3 distinct locations
  → `pervasiveness_score(3) == 2` (falls in the "3–4 locations" band). This is verified
  end-to-end by `tests/test_d2_multi_location_integration.py::test_rsa_oid_found_in_three_distinct_source_files`
  (asserts `len(oid_map[RSA_OID]) == 3`) and
  `::test_rsa_pervasiveness_is_level_2` (asserts `pervasiveness_score(3) == 2`), plus the
  unit-level boundary tests `tests/test_rules.py::test_d2_three_to_four_locations_return_level_2`.
  The root `cbom.json` (excluded from this review's case study per instructions) instead
  gives `RSA-2048` a single occurrence, which would yield `pervasiveness_score(1) == 4` — this
  is the origin of the stale "RSA D2 = 4" value; see Section 15.
- **Boundary-band history**: `rules.py` was changed by commit `8b414c6` ("Add multi-location
  RSA evidence for D2") to correct the comment/threshold from "Level 2: 3–5 locations" to
  "Level 2: 3–4 locations" so Level 1 (`>=5`) and Level 2 no longer overlapped at exactly 5.
  Location counting itself (`pervasiveness_score`) was not changed in that commit; only the
  band boundary documentation/consistency and the new multi-location fixture were added.
- **CycloneDX `dependencies` explicitly not used for D2**: the in-code comment states this
  directly (`rules.py:66`) — pervasiveness is about *occurrence locations*, not dependency
  graph relationships (dependency edges are instead used for D4 material linking).
- **Tests**: `tests/test_rules.py::test_d2_one_location_returns_level_4`,
  `::test_d2_two_locations_returns_level_3`, `::test_d2_three_to_four_locations_return_level_2`,
  `::test_d2_five_or_more_locations_return_level_1`,
  `::test_d2_missing_location_evidence_is_not_assessed`,
  `::test_d2_pervasiveness_boundary_values`;
  `tests/test_parsers.py::test_oid_location_map`, `::test_oid_map_dedupes_same_normalized_location`,
  `::test_oid_map_excludes_material_assets`;
  `tests/test_mutations.py::test_mutating_one_location_to_five_lowers_d2`,
  `::test_duplicate_locations_do_not_change_d2`;
  `tests/test_d2_multi_location_integration.py` (all 3 tests).

### D3 — Protocol Agility
- **Question answered**: can the endpoint negotiate algorithms dynamically at the protocol
  layer.
- **Evidence fields**: CryptoLyzer-derived `tls_version`, `hybrid`.
- **Implementation**: `rules.protocol_score(tls_version, hybrid)` (`rules.py:100-123`).
- **Thresholds**: `hybrid=True` → 4 (regardless of TLS version); `TLS1.3` (non-hybrid) → 3;
  `TLS1.2` → 2; `TLS1.0`/`TLS1.1` → 1; `tls_version is None` → `None` (Not Assessed).
- **Tests**: `tests/test_rules.py::test_d3_legacy_tls_returns_level_1`,
  `::test_d3_tls12_returns_level_2`, `::test_d3_tls13_returns_level_3`,
  `::test_d3_hybrid_returns_level_4`, `::test_d3_missing_or_unknown_evidence_is_not_assessed`.

### D4 — Persistent Crypto Material Evidence
- **Question answered**: does the asset carry long-lived cryptographic material that binds
  the system to a legacy lifecycle.
- **Evidence fields**: `relatedCryptoMaterialProperties.type` (linked via CycloneDX
  `dependencies`) and `algorithmProperties.primitive`.
- **Implementation**: `rules.material_score(material_type, primitive)` (`rules.py:141-168`).
- **Thresholds**: no material at all → 4 (`material_type is None`, `rules.py:145-146` —
  the code comment explicitly flags this as "absence of detected persisted material — does
  not prove ephemerality", `rules.py:138-139`); `certificate` → 1;
  `private-key` + `signature` → 2; `private-key` + (`kem` or `keyagreement`) → 3;
  any other `material_type`/`primitive` combination (e.g. `private-key` + `pke`) → `None`
  (Not Assessed — the rubric does not define that combination, `rules.py:166-168`).
- **Tests**: `tests/test_rules.py::test_d4_certificate_returns_level_1`,
  `::test_d4_private_key_signature_returns_level_2`,
  `::test_d4_private_key_keyagreement_returns_level_3`,
  `::test_d4_private_key_kem_returns_level_3`, `::test_d4_no_material_returns_level_4`,
  `::test_d4_private_key_pke_is_not_assessed`.

### Returned result format
`calculate_maturity` returns `{"d1", "d2", "d3", "d4", "maturity", "maturity_label",
"binding_constraints", "confidence"}`, or `{"status": "Not Assessed"}` if no dimension
scored (`maturity_engine.py:81-90`).

---

## 6. Maturity, Binding Constraints, and Confidence

- **Maturity formula**: `maturity = min(assessed_dimension_values)`, where "assessed" means
  the dimension's raw score is not `None` (`maturity_engine.py:62-73`). `None`-valued
  dimensions are excluded from the `min()` call entirely — **they are never coerced to 0**.
  This was explicitly verified against `tests/test_maturity.py::test_not_assessed_dimensions_are_excluded`
  (D1=2 only assessed dimension → `maturity == 2`, not penalized toward 0) and
  `::test_single_dimension_still_becomes_binding_constraint`.
- **All-dimensions-`Not Assessed` case**: `calculate_maturity` returns
  `{"status": "Not Assessed"}` (no `maturity` key at all) — `report_generator` then builds a
  distinct "excluded entry" (`report_generator._build_excluded_entry`,
  `report_generator.py:99-166`) with `maturity: None`, `priority: None`,
  `confidence: confidence(0) == "Low"`, `binding_constraints: []`. No numeric maturity or
  priority is fabricated for these assets, and they sort to the end of the report
  (`report_generator.py:518-528`). Verified by
  `tests/test_maturity.py::test_all_dimensions_missing_returns_not_assessed` and
  `tests/test_report.py::test_report_fully_unassessed_asset_is_preserved_without_maturity`.
- **Confidence thresholds** (`rules.confidence`, `rules.py:179-184`): 4 assessed dimensions →
  "High"; 3 → "Medium"; ≤2 → "Low". Confidence is explicitly documented and tested as **not**
  feeding into the numeric maturity or priority calculations
  (`tests/test_sensitivity.py::test_confidence_is_not_part_of_priority_formula`).
- **Binding-constraint selection**: `binding = [name for name, score in assessed.items() if
  score == maturity]` (`maturity_engine.py:75-79`) — i.e. **every** assessed dimension tied
  at the current minimum is listed as a binding constraint, with no special case for what
  that minimum value is.
- **Level-4 (Agile) behavior — specific risk investigated for SHA-256**: when an asset's
  minimum assessed dimension is 4 (the best/highest level, e.g. SHA-256: D1=4, D2=4, D3=Not
  Assessed, D4=4 → `maturity=4`), the same `score == maturity` rule lists **all** dimensions
  equal to 4 (here D1, D2, D4) as `binding_constraints`. This is confirmed, reproducible
  behavior of the current code — not a hypothetical: `assessment_report.csv`'s SHA-256 row
  has `Maturity=4`, and by construction of `maturity_engine.py:75-79` its binding-constraints
  list is `["Migration Coordination Complexity", "Implementation Pervasiveness", "Persistent
  Crypto Material Evidence"]` (D1, D2, D4 — the three assessed dimensions, all equal to 4).
  Downstream, `recommendation_engine.RECOMMENDATIONS` only defines recommendation text for
  levels 1–3 per dimension (`recommendation_engine.py:1-59`); `get_recommendations` looks up
  `RECOMMENDATIONS.get(dimension, {}).get(current_level)`, which returns `None` for
  `current_level == 4` and is skipped (`recommendation_engine.py:105-112`). This exact
  scenario is unit-tested: `tests/test_recommendations.py::test_level_4_constraint_does_not_generate_recommendation`
  and `::test_no_binding_constraints_returns_empty_list` confirm that a Level-4 binding
  constraint produces **zero** recommendation text. So: the raw `binding_constraints` list
  *would* label D1/D2/D4 as "binding" for a Level-4 asset, but no remediation text is ever
  attached to them, and `impact_chain.build_impact_chain` cannot act on a recommendation that
  doesn't exist, so SHA-256's impact chain has zero steps and `final_maturity == initial_maturity == 4`.
  **Risk**: if the paper (or a future dashboard change) surfaces the raw
  `binding_constraints` list for a Level-4 asset without qualification, a reader could
  misread "binding constraint" as "this is holding the asset back," when at Level 4 there is
  no higher level to reach and nothing is actually constraining further improvement.
  **Recommended neutral wording for the paper**: describe Level-4 entries in
  `binding_constraints` as "the dimensions that determine the asset's current (already
  highest-observed) maturity level," not as "limiting factors" or "constraints to remediate."
  Reserve "constraint to remediate" language for assets whose maturity is below 4.
- This behavior is implemented but not directly covered by a maturity-engine-level unit test
  using `maturity=4` binding-constraint output (the closest coverage is at the
  recommendation-engine level, per above) — see Section 18.

---

## 7. Business-Context Mapping

- **Mapping file structure**: flat JSON `{"<path marker>": "<component name>"}`
  (`component_mapping.json`): `payment_gateway`→"Payment Gateway", `pki`→"PKI
  Infrastructure", `open_banking`→"Open Banking API", `vpn`→"VPN Infrastructure",
  `internal`→"Internal Services", `certificate_authority`→"PKI Infrastructure" (two markers
  can map to the same component name).
- **Path-matching logic**: `parsers.path_contains_marker` (`parsers.py:250-299`) normalizes
  both the file path and the marker, splits each into `/`-delimited segments, and requires
  the marker's segment sequence to appear as a **contiguous full-segment run** inside the
  path's segments — i.e. `pki` matches `.../pki/key_manager.py` but not `.../apki/...` or
  `.../pkifoo/...` (guarded by
  `tests/test_parsers.py::test_path_marker_does_not_match_partial_text`).
  `resolve_component_for_path` (`parsers.py:302-366`) collects every marker that matched,
  grouped by the component name it resolves to; if only one distinct component name results,
  status is `"matched"`; if the path matched markers belonging to two or more different
  component names, status is `"ambiguous"` (never silently resolved to whichever marker
  came first); if nothing matched, status is `"unmapped"`.
  `resolve_component_for_asset` (`parsers.py:393-482`) applies this to every occurrence
  location of an asset and requires all locations to agree on exactly one component,
  otherwise the asset itself is `"ambiguous"`.
- **Current component types** (case-study, from `component_mapping.json` values / used in
  `assessment_report.csv`): "Payment Gateway", "PKI Infrastructure", "Open Banking API",
  "VPN Infrastructure", "Internal Services" — five configured names; three of them
  ("Payment Gateway", "PKI Infrastructure", "VPN Infrastructure") actually appear across the
  5 assessed assets in the current report.
- **Current criticality weights**: `rules.PAYMENT_WEIGHTS` (`rules.py:8-14`) — Payment
  Gateway 1.0, PKI Infrastructure 0.8, Open Banking API 0.7, VPN Infrastructure 0.6,
  Internal Services 0.3; default (unknown component) 0.3
  (`rules.get_payment_weight`, `rules.py:17-18`; comment attributes this scale to "PCI-DSS
  v4.0.1 Requirement 4 scope classification", `rules.py:4`).
- **Handling of unmapped/ambiguous paths**: `report_generator._resolve_component` maps
  `"unmapped"`→display name `"Unmapped"`, `"ambiguous"`→`"Ambiguous"`
  (`report_generator.py:31-32`, `53-58`), and **both** receive `payment_weight = 0.0`, never
  a real component's weight (`report_generator.py:248-252`), so an unmapped/ambiguous asset
  cannot silently inherit business-criticality weighting. Verified by
  `tests/test_report.py::test_report_unmapped_asset_has_explicit_status` and
  `::test_report_ambiguous_component_has_explicit_status` (both assert `payment_weight == 0.0`).
- **Payment-specific naming that remains in code — confirmed, not renamed**:
  - `rules.py:8`: `PAYMENT_WEIGHTS = {...}` (dict name).
  - `rules.py:17`: `def get_payment_weight(component):` (function name).
  - `report_generator.py:19, 104, 131, 245, 252, 332, 351, 421-422`: the field key
    `"payment_weight"` is used throughout the report row schema (both the excluded-entry and
    the assessed-entry builders).
  - `report_exporter.py:64, 212-215`: CSV column name `payment_weight`.
  - `app.py:2623, 2828, 2883, 3070`: dashboard code reads `item["payment_weight"]` directly.
  - `main.py:120-122`: prints `f"Business Criticality Weight: {item['payment_weight']}"` —
    i.e. the **UI label** has been generalized to "Business Criticality Weight"
    (also `ui_helpers.BUSINESS_CRITICALITY_LABEL = "Business Criticality Weight"`,
    `ui_helpers.py:76`), but the **underlying field name and function/dict names remain
    payment-specific** (`payment_weight`, `PAYMENT_WEIGHTS`, `get_payment_weight`).
  - Tests reference the same payment-specific names directly:
    `tests/test_rules.py::test_payment_weights`, `::test_unknown_component_uses_default_weight`;
    `tests/test_sensitivity.py::test_payment_weight_does_not_change_maturity`,
    `::test_increasing_payment_weight_increases_priority`,
    `::test_decreasing_payment_weight_decreases_priority`,
    `::test_zero_payment_weight_produces_zero_priority`,
    `::test_payment_weight_can_change_backlog_order`; `tests/test_report.py:75, 399, 430`.
  - **Conclusion for the paper**: the UI-facing label was generalized to "Business
    Criticality Weight," and the dashboard scope banner explicitly states the assessment
    methodology is "Domain-Independent" with Payment Systems as the validated case study
    (`app.py:1520-1573`, `ui_helpers.FRAMEWORK_POSITIONING`, `ui_helpers.py:64-67`). However,
    the underlying implementation (dict name, function name, field key, CSV column, and test
    names) is **not** domain-generalized — it is still literally named after "payment." Do
    **not** claim the codebase has been fully renamed/generalized; state precisely that the
    *presentation layer* uses domain-neutral language while the *data model* retains
    payment-specific identifiers.
- **Which parts are generic vs payment-profile-specific**: D1–D4 scoring (`rules.py`
  coordination/pervasiveness/protocol/material functions), maturity combination
  (`maturity_engine.py`), and confidence (`rules.confidence`) take no component/business
  input at all — they operate purely on CBOM/CryptoLyzer evidence, which supports the
  domain-independence claim for the *scoring methodology*. `PAYMENT_WEIGHTS`,
  `component_mapping.json`, and Mosca's default `crqc_year`/`base_migration_years`/
  `data_retention_years` are the domain/profile-specific configuration surface, and they
  only affect `priority` and Mosca timing, never D1–D4/maturity/confidence — this separation
  is real and verified by `tests/test_sensitivity.py::test_payment_weight_does_not_change_maturity`
  and `::test_base_migration_time_does_not_change_maturity`.

---

## 8. Migration Priority Model

- **Formula**: `rules.calculate_priority(risk, weight, maturity)` (`rules.py:222-223`):

  ```
  priority = round(risk * weight * (5 - maturity), 2)
  ```

- **Algorithm risk source**: `rules.algorithm_risk(algorithm_name_string)`
  (`rules.py:191-215`) — a **name-substring heuristic**, not evidence-derived: normalizes the
  asset's display name (uppercase, strips `-`/`_`/spaces) and returns 4 if it contains
  `SHA1` or `MD5`; 3 if it contains `RSA`, `ECDH`, or `ECDSA`; else 2 (default, "Low"). This
  runs against `asset.get("name")`/`item["asset"]` — the CBOM component's display name
  string — not against `primitive`, `oid`, or any structured cryptographic evidence field.
- **Criticality-weight source**: `rules.get_payment_weight(component)` (see Section 7);
  0.0 for unmapped/ambiguous components (Section 7).
- **Readiness-gap term**: `(5 - maturity)` — not a separately named "readiness gap" variable
  in code, but functionally that role; ranges from 4 (maturity=1, worst) to 1 (maturity=4,
  best).
- **Treatment of maturity Level 4**: still produces a strictly positive priority
  (`5 - 4 = 1`, never 0), so a fully "Agile" asset is deprioritized but never silently
  dropped from ranking. `Not Assessed` assets have `priority = None` (never computed,
  never defaulted to 0) and sort after all scored assets (`report_generator.py:518-528`).
- **Rounding**: `round(..., 2)` (Python banker's rounding) at `rules.py:223`.
- **Missing-mapping behavior**: unmapped/ambiguous components get `weight = 0.0`
  (Section 7), which forces `priority = 0.0` regardless of risk/maturity
  (`tests/test_rules.py::test_priority_for_unmapped_component`).
- **Worked calculation — ECDSA-secp256r1-SHA-256 (Payment Gateway)**: name normalizes to
  `ECDSASECP256R1SHA256`, contains `ECDSA` → `risk = 3`. Component = "Payment Gateway" →
  `weight = 1.0`. `maturity = 1` (D1=1 is the binding constraint). `priority = round(3 * 1.0
  * (5 - 1), 2) = round(12.0, 2) = 12.0` — matches `assessment_report.csv` row 1
  exactly.
- **Worked calculation — RSA-2048 (PKI Infrastructure)**: name contains `RSA` → `risk = 3`.
  Component = "PKI Infrastructure" → `weight = 0.8`. `maturity = 2`.
  `priority = round(3 * 0.8 * (5 - 2), 2) = round(7.2, 2) = 7.2` — matches
  `assessment_report.csv` row 2 exactly, and matches
  `tests/test_report.py::test_report_priority` (`assert item["priority"] == 7.2`) run
  against `test_data/`'s single-asset RSA fixture.
- **All 5 case-study priority values reproduced from source**: EC-secp256r1 (name contains
  neither `RSA` nor `ECDH`/`ECDSA` → `risk = 2` default; weight 0.8; maturity 2 →
  `2*0.8*3 = 4.8`); FFDH (`risk = 2` default; weight 0.6 [VPN Infrastructure]; maturity 2 →
  `2*0.6*3 = 3.6`); SHA-256 (`risk = 2` default — note "SHA256" does **not** contain the
  substring `SHA1`; weight 1.0 [Payment Gateway]; maturity 4 → `2*1.0*1 = 2.0`). All five
  match `assessment_report.csv` exactly.

---

## 9. Mosca and HNDL Planning

- **Adjusted-X formula**: `rules.adjusted_migration_time(base_years, maturity_level)`
  (`rules.py:233-250`):

  ```
  factor = 1 + (4 - maturity_level) / 4
  adjusted_x = round(base_years * factor, 2)
  ```

  Explicitly labeled in-code as a "Heuristic prototype — not empirically validated"
  (`rules.py:227-229`).
- **Migrate-by deadline**: `rules.mosca_deadline(crqc_year, adjusted_x)` (`rules.py:253-265`)
  → `round(crqc_year - adjusted_x, 2)`.
- **HNDL urgency (Mosca inequality X+Y>Z)**: `rules.mosca_urgent` (`rules.py:268-297`) —
  `years_until_crqc = crqc_year - assessment_year`; if `years_until_crqc <= 0`, always
  urgent; otherwise urgent iff `adjusted_x + data_retention_years > years_until_crqc`
  (strict `>`, confirmed non-urgent at exact equality by
  `tests/test_mosca.py::test_mosca_exact_boundary_is_not_urgent`).
- **Defaults**: `ui_helpers.DEFAULT_CRQC_YEAR = 2033`, `DEFAULT_BASE_MIGRATION_YEARS = 3.0`,
  `DEFAULT_DATA_RETENTION_YEARS = 7.0` (`ui_helpers.py:118-120`); `main.py` hardcodes the
  same values (`main.py:34-36`: `BASE_MIGRATION_YEARS = 3`, `DATA_RETENTION_YEARS = 7`,
  `CRQC_YEAR = 2033`) and derives `ASSESSMENT_YEAR = date.today().year` at run time
  (`main.py:37`).
- **User-configurable inputs (dashboard)**: `app.py` sidebar exposes `assessment_year`,
  `crqc_year`, `base_migration_years`, `data_retention_years` as `st.number_input` controls,
  pre-filled with the `ui_helpers` defaults (`app.py:1246-1280`), all passed through to
  `generate_report()` (`app.py:1373-1381`).
- **Output rounding**: `round(..., 2)` in both `adjusted_migration_time` and
  `mosca_deadline` (`rules.py:247-249, 262-264`).
- **Worked verification of all 5 case-study migrate-by values** (base=3, CRQC year=2033,
  consistent with `main.py` defaults and `docs/technical_paper/validation` generation
  timestamp of 2026-08-11):
  - ECDSA, maturity 1: `factor = 1 + 3/4 = 1.75`; `adjusted_x = 3*1.75 = 5.25`;
    `migrate_by = 2033 - 5.25 = 2027.75`. Matches CSV exactly.
  - RSA-2048 / EC-secp256r1 / FFDH, maturity 2: `factor = 1 + 2/4 = 1.5`;
    `adjusted_x = 3*1.5 = 4.5`; `migrate_by = 2033 - 4.5 = 2028.5`. Matches CSV for all
    three rows exactly, and matches `tests/test_report.py::test_report_mosca_result`
    (`adjusted_x_years == 4.5`, `migrate_by == 2028.5`).
  - SHA-256, maturity 4: `factor = 1 + 0/4 = 1.0`; `adjusted_x = 3*1.0 = 3.0`;
    `migrate_by = 2033 - 3.0 = 2030.0`. Matches CSV exactly.
- **HNDL alert condition for all 5 assets**: with `assessment_year = 2026` (matching the
  `validation_summary.json`/`assessment_report.csv` generation timestamp of
  `2026-08-11T08:55:25+00:00`) and `crqc_year = 2033`, `years_until_crqc = 7`, and
  `data_retention_years = 7`; every asset's `adjusted_x + 7 > 7` (since `adjusted_x >= 3`
  for all five assets), so all five are `Urgent`, matching the "HNDL" column in
  `assessment_report.csv`.
- **Classification**: every Mosca/HNDL output is an **assumption-based planning
  projection**, not a measurement — it depends entirely on a user/operator-supplied CRQC
  year and retention period, both of which are estimates about the future, and on a
  heuristic multiplier explicitly marked as not empirically validated.
- **No proposal/code/test discrepancy found** in the Mosca formula itself: `rules.py`,
  `tests/test_mosca.py`, and `tests/test_report.py::test_report_mosca_result` all agree on
  the formula, defaults, and worked values above.

---

## 10. Recommendation and Impact-Chain Logic

- **Recommendation selection**: `recommendation_engine.get_recommendations(assessment)`
  (`recommendation_engine.py:62-124`) iterates **only** over `assessment["binding_constraints"]`
  — i.e. recommendations are generated **per binding dimension only**, never for a
  non-binding dimension that happens to also be low. For each binding dimension it looks up
  `RECOMMENDATIONS[dimension][current_level]` in a static table
  (`recommendation_engine.py:1-59`) that only defines text for levels 1–3; a Level-4 binding
  dimension or an unrecognized dimension name yields no recommendation
  (`recommendation_engine.py:105-112`; verified by
  `tests/test_recommendations.py::test_level_4_constraint_does_not_generate_recommendation`,
  `::test_unknown_dimension_is_ignored`). `target_level = min(current_level + 1, 4)`
  (`recommendation_engine.py:117-120`) — always a one-level-at-a-time increment.
- **Combining multiple recommendations**: when multiple dimensions are tied at the binding
  minimum, one recommendation object is appended per tied dimension, in the same order as
  `binding_constraints` (`recommendation_engine.py:99-122`); there is no synthesis/merging
  into a single combined narrative — the list is presented in full (verified by
  `tests/test_recommendations.py::test_tied_binding_constraints_generate_multiple_recommendations`).
- **No-recommendation case**: an empty `recommendations` list, displayed in `main.py` as
  `"No immediate recommendation."` (`main.py:277-279`) and in `app.py`'s executive panel as
  `"No immediate recommendation."` (`app.py:2049`).
- **Impact-chain simulation**: `impact_chain.build_impact_chain(assessment, recommendations)`
  (`impact_chain.py:49-179`) copies the D1–D4 scores, then applies each recommendation
  **sequentially in list order**, raising only the specific dimension's score to its
  `target_level` (never re-deriving it from evidence), and recomputes
  `calculate_current_maturity` (min of assessed) and `find_binding_constraints` after each
  step (`impact_chain.py:82-151`). It explicitly does **not** mutate the original
  `assessment`/`scores` dict passed in (verified by
  `tests/test_impact_chain.py::test_impact_chain_does_not_modify_original_assessment`).
  A single-dimension bump does not necessarily raise overall maturity immediately if another
  dimension remains at the same minimum — verified by
  `tests/test_impact_chain.py::test_first_remediation_does_not_immediately_raise_maturity`
  and `::test_second_remediation_raises_maturity`.
- **Projected maturity**: `final_maturity` = `calculate_current_maturity` of the scores dict
  after every recommendation has been applied in sequence (`impact_chain.py:153-166`). This
  is a **simulated, hypothetical outcome** — the code never re-runs D1–D4 scoring against
  new evidence; it simply assumes each recommendation, if implemented, would move that one
  dimension's score to `target_level`. It is explicitly labeled `LABEL_PROJECTED_IMPACT =
  "Projected · Impact Chain"` in the UI (`ui_helpers.py:111`) and the dashboard states
  "New CBOMKit and CryptoLyzer evidence is required to confirm any projected maturity
  improvement." (`app.py:2066-2071`).
- **Evidence needed to confirm a projected improvement**: a fresh CBOM/CryptoLyzer scan of
  the same asset after remediation, re-run through the same D1–D4 rules — the codebase
  contains no automated re-scan/confirmation mechanism; this is a manual, out-of-band step.

---

## 11. Reporting and Dashboard

- **`assessment_report.json`/`.csv` generation (full-fidelity path)**: `main.py` calls
  `report_exporter.save_json_report` / `save_csv_report` (`main.py:54-62`,
  `report_exporter.py:16-43`, `46-377`). The CSV column set here is the **full** schema:
  `asset, status, component, component_mapped, component_status, payment_weight, primitive,
  crypto_functions, parameter_set, oid, oid_location_count, tls_version, hybrid,
  protocol_source, protocol_target, d1_coordination, d2_pervasiveness, d3_protocol,
  d4_material, maturity, maturity_label, confidence, binding_constraints, algorithm_risk,
  priority, recommendations, initial_maturity, projected_maturity, maturity_improvement,
  assessment_year, years_until_crqc, base_x_years, adjusted_x_years, data_retention_years,
  crqc_year, migrate_by, hndl_urgent` (`report_exporter.py:58-96`).
- **The actual current root `assessment_report.csv` does NOT use this schema.** Its header
  row is `Status,Asset,Component,Primitive,TLS,D1,D2,D3,D4,Maturity,Label,Confidence,
  Priority,Projected,Migrate By,HNDL` — this exactly matches `app.py`'s
  `build_summary_rows`/`build_csv_bytes` (`app.py:1079-1131`), the Streamlit dashboard's
  in-browser "download CSV" function, not `report_exporter.save_csv_report`. This is a
  factual, verifiable discrepancy: **two different CSV-export code paths exist with two
  different column sets**, and the file currently checked into the repository root (and
  duplicated identically at `docs/technical_paper/results/assessment_report.csv`) was
  produced by the dashboard's abbreviated exporter, not by `main.py`/`report_exporter.py`'s
  full-fidelity exporter. The paper should cite `app.py:1079-1131` (`build_summary_rows`,
  `build_csv_bytes`) as the actual generator of the current `assessment_report.csv`, and
  note that a second, more detailed exporter (`report_exporter.save_csv_report`) exists and
  is covered by its own tests (`tests/test_report.py::test_csv_report_export`) but is not
  what produced the file currently in the repository.
- **`validation_summary.json` generation**: `generate_validation_summary.py` runs
  `pytest -v -p no:cacheprovider --tb=no` as a subprocess, parses `PASSED/FAILED/ERROR/
  SKIPPED` tokens per test-node line, aggregates per-file counts, and writes the JSON
  (`generate_validation_summary.py:23-113`). This is an explicit, manual step — `app.py`
  never invokes pytest itself (comment at `generate_validation_summary.py:4-6`, confirmed by
  `ui_helpers.load_validation_summary`, which only reads the file and returns `None` if
  absent/malformed, `ui_helpers.py:496-523`).
- **What the dashboard displays**: Command Center (`PAGE_COMMAND_CENTER`) shows aggregate
  metrics (assets assessed, components mapped, average maturity, average projected
  maturity, highest priority, HNDL alert count — all computed live in `app.py:1769-1812`
  from the in-session `report`), the sortable migration-portfolio table
  (`build_summary_rows`), and a highest-priority spotlight panel. Collect/Map/Assess/
  Prioritise/Plan/Validate pages (the `WORKFLOW_STEPS`, `ui_helpers.py:41-49`) walk through
  raw CBOM inspection, business-context mapping, D1–D4 dimension cards, the priority
  formula, the migration plan/impact chain, and the pytest-derived validation summary,
  respectively.
- **Measured/Calculated/Projected/Validated separation**: the dashboard uses an explicit
  badge vocabulary (`BADGE_MEASURED`, `BADGE_CALCULATED`, `BADGE_PROJECTED`,
  `BADGE_VALIDATED`, `ui_helpers.py:101-111`) attached to specific UI elements (e.g.
  `dimension_card` always shows "Calculated · D_" for the score and states the evidence
  source separately, `ui_helpers.py:331-355`). This labeling is applied **consistently but
  manually** at each call site in `app.py` — there is no single automated classifier that
  guarantees every numeric value on every page carries the correct badge; it is a
  convention enforced by code review/tests (e.g. `tests/test_ui_helpers.py::test_badge_escapes_label`
  tests the badge-rendering mechanism, not badge *correctness* per value). The separation is
  real and appears deliberate throughout the reviewed code, but the paper should not claim
  it is automatically/structurally guaranteed — it is a maintained convention.
- **Export functions**: `report_exporter.save_json_report`/`save_csv_report`
  (full-fidelity, used by `main.py` and directly tested by `tests/test_report.py`);
  `app.py.build_csv_bytes`/`build_migration_plan` (in-session, abbreviated/derived,
  presentation-only per its own docstring, `app.py:1133-1139`).

---

## 12. Current Case-Study Results

Source: `assessment_report.csv` (root), byte-identical to
`docs/technical_paper/results/assessment_report.csv` (verified via `diff`). Generated
2026-08-11 (per matching timestamp in `validation_summary.json` and
`docs/technical_paper/validation/validation_status.txt`).

| Status | Asset | Component | Primitive | TLS | D1 | D2 | D3 | D4 | Maturity | Label | Confidence | Priority | Projected | Migrate By | HNDL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Assessed | ECDSA-secp256r1-SHA-256 | Payment Gateway | signature | Not Assessed | 1 | 4 | Not Assessed | 2 | 1 (Rigid) | Medium | 12.0 | 2 | 2027.75 | Urgent |
| Assessed | RSA-2048 | PKI Infrastructure | pke | TLS1.2 | 2 | 2 | 2 | Not Assessed | 2 (Constrained) | Medium | 7.2 | 3 | 2028.5 | Urgent |
| Assessed | EC-secp256r1 | PKI Infrastructure | pke | TLS1.2 | 2 | 4 | 2 | Not Assessed | 2 (Constrained) | Medium | 4.8 | 3 | 2028.5 | Urgent |
| Assessed | FFDH | VPN Infrastructure | pke | Not Assessed | 2 | 4 | Not Assessed | Not Assessed | 2 (Constrained) | Low | 3.6 | 3 | 2028.5 | Urgent |
| Assessed | SHA-256 | Payment Gateway | hash | Not Assessed | 4 | 4 | Not Assessed | 4 | 4 (Agile) | Medium | 2.0 | 4 | 2030.0 | Urgent |

**All figures above match the given expected values exactly** — verified against source
code in Sections 5, 8, 9 (independent recomputation, not a copy of the CSV).

Independently recomputed aggregate figures:
- **Asset count**: 5 (all rows `Status = Assessed`; no `Not Assessed` rows in the current
  case-study run).
- **Component-type count**: 3 distinct component names in use (Payment Gateway, PKI
  Infrastructure, VPN Infrastructure) out of 5 configured component types in
  `component_mapping.json` (Open Banking API and Internal Services are configured but not
  represented by any asset in this CBOM). "3 component types" refers to types-in-use, not a
  count of individual mapped components — do not conflate the two.
- **Average current maturity**: `(1 + 2 + 2 + 2 + 4) / 5 = 11 / 5 = 2.2`. Matches claim.
- **Average projected maturity**: `(2 + 3 + 3 + 3 + 4) / 5 = 15 / 5 = 3.0`. Matches claim.
- **Highest priority**: 12.0 (ECDSA-secp256r1-SHA-256, Payment Gateway) — the same asset
  `app.py`'s Command Center would surface via `max(assessed_assets, key=lambda item:
  item["priority"])` (`app.py:1976-1979`).
- **HNDL alert count**: 5 of 5 assessed assets are `Urgent` (see Section 9 for why every
  asset trips the inequality under the current default assumptions).

Per-asset interpretation (without overstating results):
- **ECDSA-secp256r1-SHA-256**: lowest maturity (Level 1, "Rigid") and highest priority
  (12.0) in the portfolio. D2=4 (highly localized — good) and D4=2 (identity signing key —
  moderate) are not the constraint; D1=1 (signature primitive requires signer+all-verifiers
  coordination) is the sole binding constraint. D3 is `Not Assessed` because no matching
  CryptoLyzer runtime evidence was supplied for "Payment Gateway" in this evidence set —
  this is a coverage gap, not a "TLS is bad" finding.
- **RSA-2048 / EC-secp256r1 (PKI Infrastructure)**: both Level 2 ("Constrained"), both bound
  by D1 (pke → 2) and D3 (TLS1.2 → 2) jointly (tied minimum); RSA additionally has D2=2
  (3-location spread) while EC has D2=4 (single location) — RSA's lower business-weight-
  adjusted priority difference versus EC (7.2 vs 4.8) comes entirely from
  `algorithm_risk("RSA-2048") == 3` vs `algorithm_risk("EC-secp256r1") == 2` (RSA name
  contains "RSA"; EC's name does not match the RSA/ECDH/ECDSA substrings), not from a
  maturity difference. D4 is `Not Assessed` for both (their linked material's `private-key`+
  `pke` combination is outside the D4 rubric, per Section 5).
- **FFDH (VPN Infrastructure)**: Level 2, Low confidence (only D1 and D2 assessed — D3 and
  D4 both `Not Assessed`), lowest priority of the four PQC-vulnerable assets (3.6) mainly
  because VPN Infrastructure carries the lowest configured business weight (0.6) among the
  components actually present.
  **Not** because it is inherently less risky as an algorithm.
- **SHA-256 (Payment Gateway)**: Level 4 ("Agile"), lowest priority (2.0) of the five. Its
  `binding_constraints` list (D1, D2, D4 — see Section 6) should not be read as "these are
  problems"; they are simply the (already-maximal) dimensions that determine its ceiling
  maturity. SHA-256 is a hash function and is not itself broken by Shor's/quantum attacks
  the way RSA/ECDSA are, but is still tracked in this portfolio because the framework scores
  every algorithm component present in the CBOM, not only asymmetric ones.

---

## 13. Automated Validation

Source: `validation_summary.json` (root), byte-identical to
`docs/technical_paper/results/validation_summary.json`; cross-checked against
`docs/technical_paper/validation/pytest_results.txt` (a raw `pytest -v` transcript showing
the same 184 node IDs, all `PASSED`, ending "184 passed in 0.67s" — a slightly different
duration than the JSON's `2.38s`/the other transcript's `0.48s`/`0.44s`, which is expected
run-to-run variance for a fast, non-deterministic-timing suite, not a discrepancy in pass/
fail counts).

| Test file | Passed | Failed | Skipped | Primary behavior validated |
|---|---|---|---|---|
| `tests/test_cryptolyzer_parser.py` | 10 | 0 | 0 | Version normalization, hybrid detection (true/false-positive guards), end-to-end raw-output parsing |
| `tests/test_d2_multi_location_integration.py` | 3 | 0 | 0 | RSA-2048's real 3-location spread in the case-study CBOM, component resolution, resulting D2=2 |
| `tests/test_impact_chain.py` | 11 | 0 | 0 | Sequential recommendation application, binding-constraint recomputation, non-mutation of input |
| `tests/test_maturity.py` | 10 | 0 | 0 | D1–D4 combination into maturity/confidence/binding constraints; Not-Assessed exclusion and all-missing case |
| `tests/test_mosca.py` | 12 | 0 | 0 | Adjusted migration time, deadline, HNDL urgency inequality and boundary/edge cases |
| `tests/test_mutations.py` | 9 | 0 | 0 | Score sensitivity to single evidence changes (primitive, location count, TLS version, hybrid, material type) |
| `tests/test_parsers.py` | 29 | 0 | 0 | CBOM loading, asset extraction, path normalization/matching, component resolution, CryptoLyzer evidence loading |
| `tests/test_recommendations.py` | 9 | 0 | 0 | Recommendation lookup per binding constraint, tied constraints, Level-4/unknown-dimension no-op cases |
| `tests/test_report.py` | 21 | 0 | 0 | Full `generate_report()` pipeline, exports, unmapped/ambiguous/mismatched/fully-unassessed edge cases, CRQC timing display |
| `tests/test_rules.py` | 32 | 0 | 0 | Every D1–D4 threshold, confidence levels, maturity labels, payment weights, algorithm risk, priority formula |
| `tests/test_sensitivity.py` | 14 | 0 | 0 | Priority/Mosca sensitivity to weight, risk, maturity, confidence independence |
| `tests/test_ui_helpers.py` | 24 | 0 | 0 | HTML escaping, upload validation (size/nesting/encoding/schema), validation-summary loading |
| **Total** | **184** | **0** | **0** | |

Sum check: `10+3+11+10+12+9+29+9+21+32+14+24 = 184`. Matches `validation_summary.json`'s
`total_tests: 184` and `passed: 184` exactly — no discrepancy found.

**Explicit caveat for the paper**: 184 passing unit/integration tests validate that the
*implemented formulas and code paths behave as specified against synthetic and fixture
evidence* (deterministic function outputs, edge-case handling, non-mutation, export
correctness). They do **not** constitute empirical evidence that the Mosca timeline
assumptions are accurate, that the five-asset case study generalizes to a production
financial estate, or that any assessed system is actually "post-quantum ready." Passing
tests validate internal consistency of the engine, not real-world crypto-agility outcomes.

---

## 14. Implemented Limitations

These are limitations of the code and evidence as they exist today, not hypothetical
future risks:

- **Synthetic case-study evidence**: `evidence_samples/cbom_multi_location.json` is a
  hand-authored CBOM describing a simulated `payment_simulation/` codebase
  (`payment_simulation/pki/`, `.../vpn/`, `.../payment_gateway/`,
  `.../certificate_authority/`), not evidence pulled from a real production system.
- **Five-asset portfolio**: the entire current case study covers exactly 5 algorithm assets
  across 3 in-use component types (Section 12) — far below what a real financial
  institution's cryptographic estate would contain.
- **Manual business-context mapping**: `component_mapping.json` is a small, hand-maintained
  flat file (6 marker entries); there is no automated discovery of new path markers, and a
  newly introduced source path with no matching marker silently becomes `"Unmapped"`
  (weight 0.0), which could under-prioritize a genuinely critical but unmapped asset.
- **D2 as a pervasiveness proxy**: file-location count is a structural proxy for
  "modularity," not a direct measure of how hard a migration would actually be — two
  distinct files could be trivial thin wrappers around one shared call, or one file could
  contain a deeply entangled implementation; the metric cannot distinguish these.
- **Runtime evidence coverage**: only one CryptoLyzer evidence record is present in this
  case study (`cryptolyzer_evidence.json`, targeting "PKI Infrastructure" on port 8443), so
  D3 is `Not Assessed` for every asset not resolved to that exact component
  (`ECDSA.../Payment Gateway`, `FFDH/VPN Infrastructure`, `SHA-256/Payment Gateway` all show
  `TLS: Not Assessed` in Section 12) — this is a coverage gap in the supplied evidence, not
  a framework defect.
- **D4 evidence limitations**: D4 depends on a CycloneDX `dependencies` edge existing
  between a `related-crypto-material` component and the algorithm component; if that edge is
  absent or the `material_type`/`primitive` pair isn't one of the three explicitly defined
  combinations, D4 becomes `Not Assessed` (as it does for RSA-2048, EC-secp256r1, and FFDH
  in the current case study — all have `private-key` + `pke`, which `rules.material_score`
  does not define, `rules.py:166-168`).
- **Business-weight review requirement**: `PAYMENT_WEIGHTS` are fixed constants in source
  code (`rules.py:8-14`), not configurable from the dashboard; changing them requires a code
  change and redeploy, and the values themselves are a judgment call ("informed by PCI-DSS
  v4.0.1 Requirement 4 scope classification," `rules.py:4`) that should be periodically
  reviewed by the business/risk owner, not treated as empirically derived.
- **Mosca heuristic assumptions**: the adjusted-migration-time multiplier
  (`1 + (4-L)/4`) and the CRQC-year/retention-period inputs are explicitly labeled a
  "heuristic prototype — not empirically validated" in the source comment (`rules.py:227`);
  the paper must not present `migrate_by` years as forecasts with empirical grounding.
- **No second-domain validation implemented**: the codebase's "domain-independent"
  positioning (Section 7) is an architectural property of the scoring functions (they take
  no domain-specific input), but there is no second case study (e.g. healthcare, government)
  actually implemented or run through the engine in this repository to empirically
  demonstrate that independence beyond the payment-systems case.
- **No Finacle (or other named commercial system) integration exists in this repository.**
  There is no code, configuration, or evidence file referencing Finacle or any specific core
  banking product. Any statement in the paper about applicability to a named commercial
  system must be flagged as a proposed future direction, not an implemented or validated
  capability.
- **No empirical post-remediation rescan**: `impact_chain.py`'s projected maturity (Section
  10) is a pure simulation over the recommendation table; the repository contains no
  mechanism to re-run a CBOM/CryptoLyzer scan after a recommendation is implemented and
  compare the *actual* resulting D1–D4 scores to the projection. Confirming any projected
  improvement is an unimplemented, manual, future step.

---

## 15. Conflicts and Stale Information

| # | Stale value | Current value | Authoritative source | Where the stale value appears | Approved paper wording |
|---|---|---|---|---|---|
| 1 | 179 total tests, "130-test baseline... expanded to 179" | **184** total tests, 0 failed, 0 skipped | `validation_summary.json` (auth. #4) + current `tests/` files (auth. #2) | `DESIGN_REVIEW.md:97, 201, 212, 245` (dated review of an earlier state of the repo, before the current test suite was extended) | "The current, final automated validation run collects 184 tests (0 failed, 0 skipped), per `validation_summary.json` generated 2026-08-11. An earlier design-review pass (`DESIGN_REVIEW.md`) recorded 179 tests against a prior state of the suite; that number is superseded and must not be cited as current." |
| 2 | RSA-2048 D2 = 4 (pervasiveness "Level 4," i.e. highly localized/single location) | **RSA-2048 D2 = 2** (3 distinct locations) | `evidence_samples/cbom_multi_location.json` (auth. #5) + `rules.pervasiveness_score` (auth. #1) + `assessment_report.csv` (auth. #3) | The root `cbom.json` (explicitly excluded from this case study) gives RSA-2048 a single occurrence location, which would compute to D2=4 under the current rules; `docs/technical_paper/evidence/EVIDENCE_MANIFEST.txt:38` itself flags "Any report showing RSA D2 = 4 is stale" | "The authoritative case-study CBOM (`evidence_samples/cbom_multi_location.json`) places RSA-2048's private-key generation and use across three distinct source files (`payment_simulation/pki/key_manager.py`, `certificate_manager.py`, `key_rotation_service.py`), giving D2 = 2 under `rules.pervasiveness_score`. A single-location value of D2 = 4, if seen in any older artifact (including the excluded root `cbom.json`), reflects a different, non-authoritative evidence file and must not be cited." |
| 3 | "RSA appears in three locations" (as a general claim) | **Still true and unchanged**: RSA-2048 has 3 distinct occurrence locations in the authoritative CBOM | `evidence_samples/cbom_multi_location.json`; `tests/test_d2_multi_location_integration.py::test_rsa_oid_found_in_three_distinct_source_files` | N/A — this is not actually a stale claim; it is the *location count* that is correct and unchanged. What was stale (see row 2) is the **D2 score** attributed to that count, not the count itself. | "RSA-2048's 3-location evidence is correct and current; do not confuse it with the stale D2=4 score claim above — 3 locations correctly yields D2=2, not D2=4, under the current threshold table (`rules.py:68-71`)." |
| 4 | "Business Criticality Weight" as if it were the underlying field/model name | The **field name in code remains `payment_weight`** (`rules.PAYMENT_WEIGHTS`, `rules.get_payment_weight`, `report_generator.py`'s `payment_weight` key, `report_exporter.py`'s `payment_weight` CSV column); "Business Criticality Weight" is only the **display label** (`ui_helpers.BUSINESS_CRITICALITY_LABEL`, used in `app.py` and `main.py`'s print statement) | Current source code (auth. #1); current tests (auth. #2) reference `payment_weight`/`get_payment_weight` directly | N/A (not a doc conflict — a genuine naming/positioning tension inside the current codebase itself) | "The dashboard presents this value under the domain-neutral label 'Business Criticality Weight,' but the underlying data model, function names, and CSV column (`payment_weight`, `PAYMENT_WEIGHTS`, `get_payment_weight`) remain payment-specific. The paper should describe the *presentation layer* as domain-neutral and the *implementation* as not yet fully generalized, quoting the exact identifiers where precision matters." |
| 5 | None found in current tracked docs conflating "component count" with "component-type count" | Current case study: 5 assets, **3 component types in use** (of 5 configured), not "3 components" | `assessment_report.csv` (auth. #3); `component_mapping.json` (auth. #6, configuration) | `docs/technical_paper/evidence/EVIDENCE_MANIFEST.txt:26` already states "Component types: 3" correctly | "Report '3 component types' (Payment Gateway, PKI Infrastructure, VPN Infrastructure) represented across 5 assessed assets, out of 5 component types configured in `component_mapping.json`. Do not say '3 components' — that would misstate asset count." |
| 6 | Projected maturity presented without qualification | Projected maturity (`impact_chain.final_maturity`) is a **simulated outcome of applying recommendations**, never a re-measured value | `impact_chain.py:153-179` (auth. #1); UI badge `LABEL_PROJECTED_IMPACT` (`ui_helpers.py:111`) | Risk applies to *any* future prose that quotes "Projected maturity: 3" without the word "projected"/"simulated" attached — no specific current tracked file was found stating this as measured | "Projected maturity values (e.g. RSA-2048's projected Level 3) are simulated outcomes of the recommendation/impact-chain logic, not re-measured CBOM/CryptoLyzer results. Always pair the number with 'projected' or 'simulated,' never present it as an achieved or confirmed maturity." |

No instance of "179" or "RSA D2=4" was found inside any currently-tracked file under
`docs/technical_paper/` or `docs/validation/` — those directories already carry the
corrected, current values (184 tests; RSA D2=2), including an explicit self-correcting note
in `EVIDENCE_MANIFEST.txt`. The stale "179" figure was located specifically in
`DESIGN_REVIEW.md` (a dated design-review artifact describing an earlier snapshot of the
repository, predating the `8b414c6`/`799decb`/`327fc54` commits that added the
multi-location D2 fixture, rebranded to FCAF, and updated the validation summary to 184).
The stale "RSA D2=4" value does not appear as prose in any tracked doc; it is only
*reproducible* by running the engine against the excluded root `cbom.json`, which has a
single RSA-2048 occurrence.

---

## 16. Paper-Ready Fact Table

| Claim | Verified value | Source file and function | Evidence type | Confidence | Approved wording |
|---|---|---|---|---|---|
| Framework name | "Financial Crypto Agility Assessment Framework (FCAF)" | `ui_helpers.FRAMEWORK_NAME`, `FRAMEWORK_FULL_NAME` (`ui_helpers.py:58-59`) | Configuration constant | High | Use verbatim. |
| Positioning: scope vs methodology vs case study | Framework Scope = "Financial Systems"; Methodology = "Domain-Independent D1-D4 Assessment"; Validated case study = "Payment Systems" | `app.py:1520-1573` (`ASSESSMENT_SCOPE_ITEMS`), `ui_helpers.FRAMEWORK_POSITIONING` (`ui_helpers.py:64-67`) | UI copy, matches actual code separation (Section 7) | High | Use verbatim; the D1-D4/maturity/confidence code paths genuinely take no domain input (Section 7), supporting this claim for the *scoring methodology* specifically. |
| Payment-specific naming remains in code | `PAYMENT_WEIGHTS`, `get_payment_weight`, `payment_weight` field/CSV column | `rules.py:8,17`; `report_generator.py:19,131,421-422`; `report_exporter.py:64` | Source code | High | State explicitly with exact identifiers (Section 7); do not claim full renaming. |
| D2 formula/thresholds | `>=5`→1, `3-4`→2, `2`→3, `1`→4, else Not Assessed | `rules.pervasiveness_score` (`rules.py:73-86`) | Source code + `tests/test_rules.py` (6 tests) | High | Use verbatim. |
| RSA-2048 D2 = 2 (current, authoritative) | 3 distinct locations → Level 2 | `evidence_samples/cbom_multi_location.json`; `tests/test_d2_multi_location_integration.py` | Case-study evidence + integration test | High | "RSA-2048 shows Implementation Pervasiveness Level 2 (3 source locations) in the authoritative case study." |
| Priority formula | `round(risk * weight * (5 - maturity), 2)` | `rules.calculate_priority` (`rules.py:222-223`) | Source code + `tests/test_rules.py::test_priority_calculation` | High | Use verbatim; show worked examples from Section 8. |
| Mosca adjusted-X formula | `round(base * (1 + (4-L)/4), 2)` | `rules.adjusted_migration_time` (`rules.py:233-250`) | Source code, explicitly labeled unvalidated heuristic | High (as a code fact); Low (as an empirical claim) | "A heuristic, not empirically validated, per the source code's own comment." |
| 184 tests, 0 failed, 0 skipped | Confirmed by direct file counts and pytest transcript | `validation_summary.json`; `docs/technical_paper/validation/pytest_results.txt` | Test run output | High | Use verbatim; note it validates code correctness, not production readiness (Section 13). |
| 5 assets / 3 component types / avg maturity 2.2 / avg projected 3.0 / 5 HNDL alerts | All independently recomputed and confirmed | `assessment_report.csv`; recomputation in Section 12 | Report output + independent recalculation | High | Use verbatim with the per-asset caveats in Section 12. |
| Level-4 dimensions can appear as "binding constraints" | Confirmed for SHA-256 (D1, D2, D4 all = 4 = maturity) | `maturity_engine.py:75-79`; `assessment_report.csv` SHA-256 row; `tests/test_recommendations.py::test_level_4_constraint_does_not_generate_recommendation` | Source code + case-study data + test | High | Use the neutral wording given in Section 6; never call these "constraints to remediate." |
| Not Assessed is never treated as 0 | Confirmed — `None` values are excluded from `min()`, not coerced | `maturity_engine.py:62-73`; `rules.calculate_priority`/`report_generator.py` never invoked with a `None` maturity | Source code + `tests/test_maturity.py::test_not_assessed_dimensions_are_excluded` | High | State explicitly as a design guarantee, with citation. |
| Two different CSV exporters exist; current file matches the dashboard's abbreviated one | Confirmed via header-column comparison | `app.py:1079-1131` vs `report_exporter.py:58-96` | Source code comparison | High | Disclose both exporters and state which one produced the current file (Section 11). |
| Stale "179 tests" / stale "RSA D2=4" | Both superseded | `DESIGN_REVIEW.md`; root `cbom.json` (excluded) | Documentation / non-authoritative evidence | High (as a "this is stale" finding) | Use the wording in Section 15's table. |

---

## 17. Recommended Figures and Tables

No graphics are generated here — recommendations only, for the paper author to produce from
existing outputs.

1. **Pipeline flow diagram** — Sections 1–2's stage table rendered as a left-to-right
   flowchart (CBOM → parsers.py → rules.py D1-D4 → maturity_engine.py → priority/Mosca →
   recommendation_engine.py/impact_chain.py → report_generator.py → exporters/dashboard).
   *Caption*: "Implemented FCAF assessment pipeline, with each stage labeled by its
   evidence classification (Measured / Calculated / Projected)."
2. **Case-study results table** — the Section 12 table, formatted as a paper table.
   *Caption*: "Current case-study assessment results for five algorithm assets across three
   payment-system component types (source: `assessment_report.csv`, generated 2026-08-11)."
3. **D2 pervasiveness worked example diagram** — a small diagram showing RSA-2048's three
   source-code occurrence paths converging into one OID-keyed location set, then into
   `pervasiveness_score(3) = 2`. *Caption*: "Implementation Pervasiveness (D2) is computed
   from the count of distinct normalized source-file locations sharing an algorithm's OID,
   not from CycloneDX dependency edges."
4. **Priority-formula bar chart** — the 5 case-study assets' `risk`, `weight`, `(5-maturity)`
   factors and resulting `priority`, as a stacked/grouped bar chart. *Caption*: "Migration
   priority decomposition for the current case-study portfolio; higher bars indicate
   higher-priority migration candidates under the current business-criticality weighting."
5. **Mosca/HNDL timeline chart** — a horizontal timeline from the assessment year (2026)
   through each asset's `migrate_by` year to the assumed CRQC year (2033). *Caption*:
   "Illustrative, assumption-based migration deadlines under the current default CRQC year
   (2033), base migration time (3 years), and data-retention period (7 years); not an
   empirically validated forecast."
6. **Validation summary table** — the Section 13 per-file test table.
   *Caption*: "Automated validation coverage by test module (184/184 passing,
   `validation_summary.json`, generated 2026-08-11)."
7. **Dashboard screenshots** (would need to be captured by running `streamlit run app.py`):
   (a) the Assessment Scope panel (`app.py:1532-1573`) showing the domain-independence
   positioning statement; (b) a D1–D4 dimension-card row from the Assess page showing the
   dual Measured/Calculated badge pattern; (c) the Command Center executive metrics panel.
   *Captions should state these are illustrative UI captures of the reviewed dashboard
   version, not new data.*

---

## 18. Remaining Verification Items

Items that could not be fully confirmed from source/tests/current data within this review's
scope, or that depend on runtime behavior not exercised by a located test:

1. **No maturity-engine-level unit test directly asserts the Level-4 binding-constraint
   list for a fully-Level-4 asset.** The behavior is confirmed correct by inspection of
   `maturity_engine.py:75-79` and by the *recommendation-engine*-level test
   `tests/test_recommendations.py::test_level_4_constraint_does_not_generate_recommendation`
   (which supplies a hand-built assessment dict, not one produced by `calculate_maturity`
   itself), and by manually recomputing SHA-256's binding constraints from
   `assessment_report.csv`. A direct `tests/test_maturity.py` case built from
   `calculate_maturity()` output with all-assessed-dimensions-at-4 was not found. Recommend
   the paper author (or a follow-up change) add this test rather than relying solely on the
   cross-module inference made in Section 6.
2. **Exact production dependency versions actually required to run the scoring engine**
   (as opposed to the full `requirements.txt`, which also includes tooling for the
   `local_test/` TLS-server/evidence-generation scripts and Streamlit/Altair for the
   dashboard) were not separately isolated — `requirements.txt` was read only in part (an
   encoding artifact truncated visual inspection of the full pinned-version list). This does
   not affect any scoring/behavior claim above, only completeness of a "dependencies" list
   if the paper wants one.
3. **Whether `main.py`'s `report_exporter.save_csv_report` output has ever been checked into
   the repository under any filename** was not found — only the dashboard's abbreviated
   `build_csv_bytes` output (`assessment_report.csv`) exists in the tree. If the paper wants
   to show the full-fidelity CSV schema as a table, it will need to be regenerated by running
   `python main.py`, which was not done as part of this fact-finding pass (out of scope: this
   task was read-only/no source or generated-artifact modification).
4. **Whether any other file in the repository (outside the explicitly reviewed list) contains
   the stale "179" or "RSA D2=4" values** was checked only via targeted grep across
   `docs/` and `DESIGN_REVIEW.md`; a full-repository grep across every file (including
   `.claude/worktrees/`, `test_data/`, and other explicitly out-of-scope directories) was not
   performed, per the task's exclusion list.
5. **The precise Python/pytest/Streamlit version pins used to produce the current
   `validation_summary.json`** are visible in `docs/technical_paper/validation/
   validation_environment.txt`'s companion transcript (`Python 3.14.6, pytest-9.1.1,
   pluggy-1.6.0, platform win32`, seen in `docs/validation/validation_results.txt`) but this
   was not cross-checked against `requirements.txt`'s pinned versions line-by-line; minor
   version drift between the documented validation environment and `requirements.txt` is
   possible and was not exhaustively ruled out.
