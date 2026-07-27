from datetime import date

from report_generator import generate_report
from report_exporter import (
    save_json_report,
    save_csv_report,
)


def display_score(score):
    """
    Displays missing dimension evidence clearly instead
    of printing the Python value None.
    """

    if score is None:
        return "Not Assessed"

    return score


# Configuration

CBOM_FILE = "cbom.json"

COMPONENT_MAPPING_FILE = (
    "component_mapping.json"
)

CRYPTOLYZER_EVIDENCE_FILE = (
    "cryptolyzer_evidence.json"
)

BASE_MIGRATION_YEARS = 3
DATA_RETENTION_YEARS = 7
CRQC_YEAR = 2033
ASSESSMENT_YEAR = date.today().year

JSON_REPORT_FILE = "assessment_report.json"
CSV_REPORT_FILE = "assessment_report.csv"
# Run assessment

report = generate_report(
    cbom_file=CBOM_FILE,
    component_mapping_file=COMPONENT_MAPPING_FILE,
    cryptolyzer_evidence_file=(
        CRYPTOLYZER_EVIDENCE_FILE
    ),
    base_migration_years=BASE_MIGRATION_YEARS,
    data_retention_years=DATA_RETENTION_YEARS,
    crqc_year=CRQC_YEAR,
    assessment_year=ASSESSMENT_YEAR,
)
json_report_path = save_json_report(
    report,
    JSON_REPORT_FILE
)

csv_report_path = save_csv_report(
    report,
    CSV_REPORT_FILE
)


# Display summary

print(
    "\n=== PQC Crypto Agility Maturity Assessment ===\n"
)

print(
    "Component and protocol evidence are resolved "
    "separately for each asset."
)

print(
    f"Assessment Year : {ASSESSMENT_YEAR}"
)

print(
    f"CRQC Year       : {CRQC_YEAR}"
)

print(
    f"Mosca Base X    : "
    f"{BASE_MIGRATION_YEARS} years"
)

print(
    f"Data Retention  : "
    f"{DATA_RETENTION_YEARS} years"
)

print("=" * 70)


# Display each assessed algorithm asset

for item in report:

    mosca = item["mosca"]
    dimensions = item["dimensions"]
    protocol = item["protocol_evidence"]

    print(
        f"\nAsset           : {item['asset']}"
    )

    print(
        f"Component       : {item['component']}"
    )

    print(
        f"Component Mapped: "
        f"{item['component_mapped']}"
    )

    print(
        f"Payment Weight  : "
        f"{item['payment_weight']}"
    )

    print(
        f"TLS             : "
        f"{protocol['tls_version'] or 'Not Assessed'}"
    )

    print(
        f"Hybrid          : "
        f"{protocol['hybrid']}"
    )

    print(
        f"Protocol Source : "
        f"{protocol['source'] or 'Not Assessed'}"
    )

    protocol_target = protocol.get(
        "target"
    )

    if protocol_target:
        target_address = (
            protocol_target.get("address")
            or "Unknown"
        )

        target_port = (
            protocol_target.get("port")
            or "Unknown"
        )

        print(
            f"Protocol Target : "
            f"{target_address}:{target_port}"
        )
    else:
        print(
            "Protocol Target : Not Assessed"
        )

    print(
        f"Primitive       : "
        f"{item.get('primitive') or 'Not Assessed'}"
    )

    crypto_functions = item.get(
        "crypto_functions",
        []
    )

    print(
        f"Crypto Functions: "
        f"{crypto_functions or 'Not Assessed'}"
    )

    print(
        f"OID             : "
        f"{item.get('oid') or 'Not Assessed'}"
    )

    print(
        f"Locations       : "
        f"{item['oid_location_count']} "
        f"distinct file(s)"
    )

    print(
        f"Maturity        : "
        f"Level {item['maturity']} - "
        f"{item['maturity_label']}"
    )

    print(
        f"Confidence      : "
        f"{item['confidence']}"
    )

    print("Binding Constraints:")

    binding_constraints = item.get(
        "binding_constraints",
        []
    )

    if binding_constraints:
        for constraint in binding_constraints:
            print(
                f"  - {constraint}"
            )
    else:
        print(
            "  - None"
        )

    print(
        f"Algorithm Risk  : "
        f"{item['algorithm_risk']}"
    )

    print(
        f"Priority Score  : "
        f"{item['priority']}"
    )

    print("\nDimensions:")

    print(
        "  D1 Coordination  : "
        f"{display_score(dimensions['d1_coordination'])}"
    )

    print(
        "  D2 Pervasiveness : "
        f"{display_score(dimensions['d2_pervasiveness'])}"
    )

    print(
        "  D3 Protocol      : "
        f"{display_score(dimensions['d3_protocol'])}"
    )

    print(
        "  D4 Material      : "
        f"{display_score(dimensions['d4_material'])}"
    )

    print("\nRecommendations:")

    recommendations = item.get(
        "recommendations",
        []
    )

    if recommendations:
        for recommendation in recommendations:

            print(
                "  - "
                f"[{recommendation['dimension']}]"
            )

            print(
                "    "
                f"Level "
                f"{recommendation['current_level']} "
                f"-> Level "
                f"{recommendation['target_level']}"
            )

            print(
                "    "
                f"{recommendation['recommendation']}"
            )
    else:
        print(
            "  - No immediate recommendation."
        )

    print("\nProjected Impact Chain:")

    # impact_chain is explicitly None for excluded/Not Assessed
    # assets, so "or {}" is required here.
    impact_chain = item.get(
        "impact_chain"
    ) or {}

    impact_steps = impact_chain.get(
        "steps",
        []
    )

    if impact_steps:
        print(
            "  Initial maturity: "
            f"Level "
            f"{impact_chain['initial_maturity']}"
        )

        for step in impact_steps:

            print(
                f"\n  Step {step['step']}: "
                f"{step['dimension']}"
            )

            print(
                "    Dimension level: "
                f"{step['from_level']} "
                f"-> {step['to_level']}"
            )

            if step["maturity_changed"]:
                print(
                    "    Component maturity: "
                    f"Level "
                    f"{step['maturity_before']} "
                    f"-> Level "
                    f"{step['maturity_after']}"
                )
            else:
                print(
                    "    Component maturity remains: "
                    f"Level "
                    f"{step['maturity_after']}"
                )

            remaining_constraints = step.get(
                "remaining_binding_constraints",
                []
            )

            if remaining_constraints:
                print(
                    "    Remaining binding constraints:"
                )

                for constraint in remaining_constraints:
                    print(
                        f"      - {constraint}"
                    )
            else:
                print(
                    "    Remaining binding constraints: "
                    "None"
                )

        print(
            "\n  Final projected maturity: "
            f"Level "
            f"{impact_chain['final_maturity']}"
        )

        print(
            "  Projected maturity improvement: "
            f"{impact_chain['maturity_improvement']}"
        )

    else:
        print(
            "  - No projected impact chain available."
        )

    print("\nMosca Analysis:")

    print(
        f"  Assessment Year : "
        f"{mosca['assessment_year']}"
    )

    print(
        f"  Years to CRQC   : "
        f"{mosca['years_until_crqc_z']}"
    )

    print(
        f"  Base X          : "
        f"{mosca['base_x_years']} years"
    )

    print(
        f"  Adjusted X      : "
        f"{mosca['adjusted_x_years']} years"
    )

    print(
        f"  Data Retention  : "
        f"{mosca['data_retention_y']} years"
    )

    print(
        f"  Migrate By      : "
        f"{mosca['migrate_by']}"
    )

    print(
        f"  HNDL Urgent     : "
        f"{mosca['urgent']}"
    )

    print("-" * 70)


# Handle empty report

if not report:
    print(
        "No algorithm assets were found "
        "or assessed in the CBOM."
    )
else:
    print("\nGenerated Reports:")

    print(
        f"  JSON : {json_report_path}"
    )

    print(
        f"  CSV  : {csv_report_path}"
    )