import csv
import json


def display_value(value):
    """
    Converts missing values into a readable report value.
    """

    if value is None:
        return "Not Assessed"

    return value


def save_json_report(
    report,
    output_file="assessment_report.json"
):
    """
    Saves the complete assessment report as JSON.

    JSON preserves:
    - dimensions
    - recommendations
    - projected impact chains
    - protocol evidence
    - Mosca results
    """

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    return output_file


def save_csv_report(
    report,
    output_file="assessment_report.csv"
):
    """
    Saves a flattened summary of the assessment report
    as CSV.

    Nested evidence, recommendations and impact-chain
    details remain available in the JSON report.
    """

    fieldnames = [
        "asset",
        "status",
        "component",
        "component_mapped",
        "component_status",
        "payment_weight",
        "primitive",
        "crypto_functions",
        "parameter_set",
        "oid",
        "oid_location_count",
        "tls_version",
        "hybrid",
        "protocol_source",
        "protocol_target",
        "d1_coordination",
        "d2_pervasiveness",
        "d3_protocol",
        "d4_material",
        "maturity",
        "maturity_label",
        "confidence",
        "binding_constraints",
        "algorithm_risk",
        "priority",
        "recommendations",
        "initial_maturity",
        "projected_maturity",
        "maturity_improvement",
        "assessment_year",
        "years_until_crqc",
        "base_x_years",
        "adjusted_x_years",
        "data_retention_years",
        "crqc_year",
        "migrate_by",
        "hndl_urgent",
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for item in report:

            dimensions = item.get(
                "dimensions",
                {}
            )

            protocol = item.get(
                "protocol_evidence",
                {}
            )

            mosca = item.get(
                "mosca",
                {}
            )

            # impact_chain is explicitly None (not omitted) for
            # excluded/Not Assessed assets, so "or {}" is required
            # here — item.get(..., {}) would not catch that case.
            impact_chain = item.get(
                "impact_chain"
            ) or {}

            target = protocol.get(
                "target"
            ) or {}

            protocol_address = target.get(
                "address"
            )

            protocol_port = target.get(
                "port"
            )

            if (
                protocol_address is not None
                and protocol_port is not None
            ):
                protocol_target = (
                    f"{protocol_address}:"
                    f"{protocol_port}"
                )
            else:
                protocol_target = (
                    "Not Assessed"
                )

            recommendations = item.get(
                "recommendations",
                []
            )

            recommendation_text = " | ".join(
                (
                    f"{recommendation['dimension']}: "
                    f"{recommendation['recommendation']}"
                )
                for recommendation
                in recommendations
            )

            binding_constraints = " | ".join(
                item.get(
                    "binding_constraints",
                    []
                )
            )

            crypto_functions = " | ".join(
                item.get(
                    "crypto_functions",
                    []
                )
            )

            writer.writerow({
                "asset":
                    item.get("asset"),

                "status":
                    item.get(
                        "status",
                        "Assessed"
                    ),

                "component":
                    item.get("component"),

                "component_mapped":
                    item.get(
                        "component_mapped"
                    ),

                "component_status":
                    item.get(
                        "component_status"
                    ),

                "payment_weight":
                    item.get(
                        "payment_weight"
                    ),

                "primitive":
                    display_value(
                        item.get("primitive")
                    ),

                "crypto_functions":
                    crypto_functions
                    or "Not Assessed",

                "parameter_set":
                    display_value(
                        item.get(
                            "parameter_set"
                        )
                    ),

                "oid":
                    display_value(
                        item.get("oid")
                    ),

                "oid_location_count":
                    item.get(
                        "oid_location_count"
                    ),

                "tls_version":
                    display_value(
                        protocol.get(
                            "tls_version"
                        )
                    ),

                "hybrid":
                    protocol.get(
                        "hybrid",
                        False
                    ),

                "protocol_source":
                    display_value(
                        protocol.get(
                            "source"
                        )
                    ),

                "protocol_target":
                    protocol_target,

                "d1_coordination":
                    display_value(
                        dimensions.get(
                            "d1_coordination"
                        )
                    ),

                "d2_pervasiveness":
                    display_value(
                        dimensions.get(
                            "d2_pervasiveness"
                        )
                    ),

                "d3_protocol":
                    display_value(
                        dimensions.get(
                            "d3_protocol"
                        )
                    ),

                "d4_material":
                    display_value(
                        dimensions.get(
                            "d4_material"
                        )
                    ),

                "maturity":
                    item.get("maturity"),

                "maturity_label":
                    item.get(
                        "maturity_label"
                    ),

                "confidence":
                    item.get("confidence"),

                "binding_constraints":
                    binding_constraints
                    or "None",

                "algorithm_risk":
                    item.get(
                        "algorithm_risk"
                    ),

                "priority":
                    item.get("priority"),

                "recommendations":
                    recommendation_text
                    or "No immediate recommendation",

                "initial_maturity":
                    impact_chain.get(
                        "initial_maturity"
                    ),

                "projected_maturity":
                    impact_chain.get(
                        "final_maturity"
                    ),

                "maturity_improvement":
                    impact_chain.get(
                        "maturity_improvement"
                    ),

                "assessment_year":
                    mosca.get(
                        "assessment_year"
                    ),

                "years_until_crqc":
                    mosca.get(
                        "years_until_crqc_z"
                    ),

                "base_x_years":
                    mosca.get(
                        "base_x_years"
                    ),

                "adjusted_x_years":
                    mosca.get(
                        "adjusted_x_years"
                    ),

                "data_retention_years":
                    mosca.get(
                        "data_retention_y"
                    ),

                "crqc_year":
                    mosca.get(
                        "crqc_year"
                    ),

                "migrate_by":
                    mosca.get(
                        "migrate_by"
                    ),

                "hndl_urgent":
                    mosca.get(
                        "urgent"
                    ),
            })

    return output_file