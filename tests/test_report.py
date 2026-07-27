import csv
import json
from pathlib import Path

from report_exporter import (
    save_json_report,
    save_csv_report,
)

from report_generator import (
    generate_report,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

TEST_DATA = (
    PROJECT_ROOT
    / "test_data"
)

CBOM_FILE = (
    TEST_DATA
    / "cbom.json"
)

COMPONENT_MAPPING_FILE = (
    TEST_DATA
    / "component_mapping.json"
)

CRYPTOLYZER_FILE = (
    TEST_DATA
    / "cryptolyzer_evidence.json"
)


def generate_test_report():
    return generate_report(
        cbom_file=CBOM_FILE,
        component_mapping_file=(
            COMPONENT_MAPPING_FILE
        ),
        cryptolyzer_evidence_file=(
            CRYPTOLYZER_FILE
        ),
        base_migration_years=3,
        data_retention_years=7,
        crqc_year=2033,
        assessment_year=2026,
    )


def test_report_contains_one_algorithm_asset():
    report = generate_test_report()

    assert len(report) == 1
    assert report[0]["asset"] == "RSA-2048"


def test_report_component_mapping():
    report = generate_test_report()
    item = report[0]

    assert (
        item["component"]
        == "PKI Infrastructure"
    )

    assert item["component_mapped"] is True
    assert item["payment_weight"] == 0.8


def test_report_contains_cbom_evidence():
    report = generate_test_report()
    item = report[0]

    assert item["primitive"] == "pke"

    assert item["crypto_functions"] == [
        "keygen"
    ]

    assert item["parameter_set"] == "2048"

    assert item["oid"] == (
        "1.2.840.113549.1.1.1"
    )

    assert item["oid_location_count"] == 1


def test_report_contains_cryptolyzer_evidence():
    report = generate_test_report()

    protocol = report[0][
        "protocol_evidence"
    ]

    assert protocol["tls_version"] == "TLS1.2"
    assert protocol["hybrid"] is False
    assert protocol["source"] == "cryptolyzer"
    assert protocol["assessed"] is True
    assert protocol["component_match"] is True

    assert protocol["target"]["address"] == (
        "localhost"
    )

    assert protocol["target"]["port"] == 8443


def test_report_maturity_result():
    report = generate_test_report()
    item = report[0]

    assert item["dimensions"] == {
        "d1_coordination": 2,
        "d2_pervasiveness": 4,
        "d3_protocol": 2,
        "d4_material": None,
    }

    assert item["maturity"] == 2
    assert item["maturity_label"] == "Constrained"
    assert item["confidence"] == "Medium"


def test_report_binding_constraints():
    report = generate_test_report()
    item = report[0]

    assert item["binding_constraints"] == [
        "Migration Coordination Complexity",
        "Protocol Agility",
    ]


def test_report_priority():
    report = generate_test_report()
    item = report[0]

    assert item["algorithm_risk"] == 3
    assert item["priority"] == 7.2


def test_report_recommendations():
    report = generate_test_report()

    recommendations = report[0][
        "recommendations"
    ]

    assert len(recommendations) == 2

    assert (
        recommendations[0]["dimension"]
        == "Migration Coordination Complexity"
    )

    assert (
        "KEM-based construction"
        in recommendations[0]["recommendation"]
    )

    assert (
        recommendations[1]["dimension"]
        == "Protocol Agility"
    )


def test_report_impact_chain():
    report = generate_test_report()

    impact_chain = report[0][
        "impact_chain"
    ]

    assert impact_chain["initial_maturity"] == 2
    assert impact_chain["final_maturity"] == 3
    assert impact_chain["maturity_improvement"] == 1
    assert len(impact_chain["steps"]) == 2


def test_report_mosca_result():
    report = generate_test_report()

    mosca = report[0]["mosca"]

    assert mosca["assessment_year"] == 2026
    assert mosca["years_until_crqc_z"] == 7
    assert mosca["base_x_years"] == 3
    assert mosca["adjusted_x_years"] == 4.5
    assert mosca["data_retention_y"] == 7
    assert mosca["crqc_year"] == 2033
    assert mosca["migrate_by"] == 2028.5
    assert mosca["urgent"] is True


def test_json_report_export(tmp_path):
    report = generate_test_report()

    output_file = (
        tmp_path
        / "assessment_report.json"
    )

    saved_path = save_json_report(
        report,
        output_file
    )

    assert Path(saved_path).exists()

    with open(
        saved_path,
        "r",
        encoding="utf-8"
    ) as file:
        exported_report = json.load(
            file
        )

    assert len(exported_report) == 1

    assert (
        exported_report[0]["asset"]
        == "RSA-2048"
    )

    assert (
        exported_report[0]["maturity"]
        == 2
    )


def test_csv_report_export(tmp_path):
    report = generate_test_report()

    output_file = (
        tmp_path
        / "assessment_report.csv"
    )

    saved_path = save_csv_report(
        report,
        output_file
    )

    assert Path(saved_path).exists()

    with open(
        saved_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 1

    row = rows[0]

    assert row["asset"] == "RSA-2048"

    assert (
        row["component"]
        == "PKI Infrastructure"
    )

    assert row["tls_version"] == "TLS1.2"
    assert row["maturity"] == "2"
    assert row["confidence"] == "Medium"
    assert row["priority"] == "7.2"

    assert (
        row["projected_maturity"]
        == "3"
    )

    assert row["hndl_urgent"] == "True"


def test_report_is_sorted_by_priority():
    report = generate_test_report()

    priorities = [
        item["priority"]
        for item in report
    ]

    assert priorities == sorted(
        priorities,
        reverse=True
    )


# ── Helpers for synthetic single-asset fixtures ────────────────────────────
#
# These build minimal CycloneDX-shaped CBOM documents in a tmp_path so
# report-level edge cases (unmapped, ambiguous, mismatched CryptoLyzer
# component, fully unassessed assets) can be exercised end-to-end through
# generate_report() without touching the real test_data/ fixtures.

def _write_json(path, data):
    path.write_text(
        json.dumps(data),
        encoding="utf-8"
    )
    return path


def _single_asset_cbom(
    location,
    primitive="pke",
    oid="1.2.840.113549.1.1.1",
    material_type="private-key",
    material_size=2048,
):
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [
            {
                "type": "cryptographic-asset",
                "bom-ref": "material-ref",
                "name": "material@1",
                "evidence": {
                    "occurrences": [
                        {"location": location}
                    ]
                },
                "cryptoProperties": {
                    "assetType": "related-crypto-material",
                    "relatedCryptoMaterialProperties": {
                        "type": material_type,
                        "size": material_size,
                    },
                },
            },
            {
                "type": "cryptographic-asset",
                "bom-ref": "algorithm-ref",
                "name": "RSA-2048",
                "evidence": {
                    "occurrences": [
                        {"location": location}
                    ]
                },
                "cryptoProperties": {
                    "assetType": "algorithm",
                    "algorithmProperties": {
                        "primitive": primitive,
                        "parameterSetIdentifier": "2048",
                        "cryptoFunctions": ["keygen"],
                    },
                    "oid": oid,
                },
            },
        ],
        "dependencies": [
            {
                "ref": "material-ref",
                "dependsOn": ["algorithm-ref"],
            }
        ],
    }


def test_report_unmapped_asset_has_explicit_status(tmp_path):
    cbom_file = _write_json(
        tmp_path / "cbom.json",
        _single_asset_cbom("unknown/service.py"),
    )

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {"pki": "PKI Infrastructure"},
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        assessment_year=2026,
    )

    item = report[0]

    assert item["component"] == "Unmapped"
    assert item["component_mapped"] is False
    assert item["component_status"] == "unmapped"
    assert item["component_reason"]
    assert item["payment_weight"] == 0.0


def test_report_ambiguous_component_has_explicit_status(tmp_path):
    cbom_file = _write_json(
        tmp_path / "cbom.json",
        _single_asset_cbom(
            "payment_simulation/vpn/pki/gateway.py"
        ),
    )

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {
            "vpn": "VPN Infrastructure",
            "pki": "PKI Infrastructure",
        },
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        assessment_year=2026,
    )

    item = report[0]

    assert item["component"] == "Ambiguous"
    assert item["component_mapped"] is False
    assert item["component_status"] == "ambiguous"
    assert item["component_reason"]
    assert item["payment_weight"] == 0.0


def test_report_cryptolyzer_component_mismatch_withholds_d3(tmp_path):
    cbom_file = _write_json(
        tmp_path / "cbom.json",
        _single_asset_cbom(
            "payment_simulation/pki/certificate_manager.py"
        ),
    )

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {"pki": "PKI Infrastructure"},
    )

    cryptolyzer_file = _write_json(
        tmp_path / "cryptolyzer.json",
        {
            "component": "VPN Infrastructure",
            "source": "cryptolyzer",
            "tls_version": "TLS1.3",
            "hybrid": True,
            "assessed": True,
            "target": {"address": "localhost", "port": 8443},
        },
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        cryptolyzer_evidence_file=cryptolyzer_file,
        assessment_year=2026,
    )

    item = report[0]

    assert item["component"] == "PKI Infrastructure"

    protocol = item["protocol_evidence"]

    assert protocol["component_match"] is False
    assert protocol["tls_version"] is None
    assert protocol["hybrid"] is False
    assert protocol["source"] is None

    # D3 must be withheld (Not Assessed), not silently borrowed
    # from the mismatched component's evidence.
    assert item["dimensions"]["d3_protocol"] is None


def test_report_fully_unassessed_asset_is_preserved_without_maturity(
    tmp_path
):
    # oid=None so D2 cannot be inferred from occurrence count;
    # primitive is outside the D1 rubric; material_type +
    # primitive is a combination the D4 rubric does not define.
    # The asset still has a real occurrence location, so component
    # mapping (independent of maturity scoring) is still resolved.
    cbom_file = _write_json(
        tmp_path / "cbom.json",
        _single_asset_cbom(
            "payment_simulation/pki/certificate_manager.py",
            primitive="unknown-primitive",
            material_type="private-key",
            oid=None,
        ),
    )

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {"pki": "PKI Infrastructure"},
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        assessment_year=2026,
    )

    assert len(report) == 1

    item = report[0]

    assert item["status"] == "Not Assessed"
    assert item["excluded_reason"]
    assert item["maturity"] is None
    assert item["maturity_label"] == "Not Assessed"
    assert item["priority"] is None
    assert item["impact_chain"] is None
    assert item["binding_constraints"] == []
    assert item["recommendations"] == []
    assert item["dimensions"] == {
        "d1_coordination": None,
        "d2_pervasiveness": None,
        "d3_protocol": None,
        "d4_material": None,
    }

    # Component/payment-context evidence is still preserved even
    # though the asset could not be scored on any dimension.
    assert item["component"] == "PKI Infrastructure"
    assert item["component_mapped"] is True


def test_report_sorts_not_assessed_assets_after_assessed_assets(tmp_path):
    cbom = _single_asset_cbom(
        "payment_simulation/pki/certificate_manager.py"
    )

    # Add a second, fully-unassessable algorithm asset with no
    # usable evidence at all: unmapped primitive (D1 None), no
    # oid (D2 None), no CryptoLyzer evidence (D3 None), and a
    # related-material/primitive combination the D4 rubric does
    # not define (D4 None).
    cbom["components"].append({
        "type": "cryptographic-asset",
        "bom-ref": "second-material-ref",
        "name": "second-material@1",
        "evidence": {"occurrences": []},
        "cryptoProperties": {
            "assetType": "related-crypto-material",
            "relatedCryptoMaterialProperties": {
                "type": "private-key",
                "size": 2048,
            },
        },
    })

    cbom["components"].append({
        "type": "cryptographic-asset",
        "bom-ref": "second-algorithm-ref",
        "name": "Unknown-Algorithm",
        "evidence": {"occurrences": []},
        "cryptoProperties": {
            "assetType": "algorithm",
            "algorithmProperties": {
                "primitive": "unknown-primitive",
            },
        },
    })

    cbom["dependencies"].append({
        "ref": "second-material-ref",
        "dependsOn": ["second-algorithm-ref"],
    })

    cbom_file = _write_json(tmp_path / "cbom.json", cbom)

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {"pki": "PKI Infrastructure"},
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        assessment_year=2026,
    )

    assert len(report) == 2
    assert report[0]["status"] == "Assessed"
    assert report[1]["status"] == "Not Assessed"


# ── CRQC year timing/display ────────────────────────────────────────────────

def test_mosca_years_until_crqc_upcoming(tmp_path):
    cbom_file = _write_json(
        tmp_path / "cbom.json",
        _single_asset_cbom(
            "payment_simulation/pki/certificate_manager.py"
        ),
    )

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {"pki": "PKI Infrastructure"},
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        crqc_year=2033,
        assessment_year=2026,
    )

    mosca = report[0]["mosca"]

    assert mosca["years_until_crqc_z"] == 7
    assert mosca["crqc_status"] == "upcoming"
    assert mosca["years_overdue"] == 0


def test_mosca_years_until_crqc_already_passed_shows_overdue(tmp_path):
    cbom_file = _write_json(
        tmp_path / "cbom.json",
        _single_asset_cbom(
            "payment_simulation/pki/certificate_manager.py"
        ),
    )

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {"pki": "PKI Infrastructure"},
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        crqc_year=2024,
        assessment_year=2026,
    )

    mosca = report[0]["mosca"]

    # CRQC year already passed two years ago — the display must
    # not present an ambiguous clamped "0 years" with no context.
    assert mosca["years_until_crqc_z"] == 0
    assert mosca["crqc_status"] == "passed"
    assert mosca["years_overdue"] == 2
    assert mosca["urgent"] is True


def test_mosca_years_until_crqc_reached_exactly_this_year(tmp_path):
    cbom_file = _write_json(
        tmp_path / "cbom.json",
        _single_asset_cbom(
            "payment_simulation/pki/certificate_manager.py"
        ),
    )

    mapping_file = _write_json(
        tmp_path / "mapping.json",
        {"pki": "PKI Infrastructure"},
    )

    report = generate_report(
        cbom_file=cbom_file,
        component_mapping_file=mapping_file,
        crqc_year=2026,
        assessment_year=2026,
    )

    mosca = report[0]["mosca"]

    assert mosca["years_until_crqc_z"] == 0
    assert mosca["crqc_status"] == "passed"
    assert mosca["years_overdue"] == 0
    assert mosca["urgent"] is True