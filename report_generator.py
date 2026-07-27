from datetime import date

from impact_chain import build_impact_chain

from parsers import (
    load_cbom,
    get_crypto_assets,
    build_oid_location_map,
    load_component_mapping,
    resolve_component_for_asset,
    load_cryptolyzer_evidence,
)

from maturity_engine import calculate_maturity

from rules import (
    algorithm_risk,
    calculate_priority,
    get_payment_weight,
    adjusted_migration_time,
    mosca_deadline,
    mosca_urgent,
    confidence,
)

from recommendation_engine import get_recommendations


# Component names used for statuses that are not a real payment
# component match. Kept distinct from any real PAYMENT_WEIGHTS key.
UNMAPPED_COMPONENT_LABEL = "Unmapped"
AMBIGUOUS_COMPONENT_LABEL = "Ambiguous"

NOT_ASSESSED_REASON = (
    "No CBOM or CryptoLyzer evidence could be scored against any "
    "of the four assessment dimensions (D1-D4)."
)


def _resolve_component(asset, component_mapping):
    """
    Resolves the payment component for an asset and returns the
    display name, mapped flag, status and reason together, so the
    "Unmapped" and "Ambiguous" outcomes are never confused with a
    silently-chosen real component.
    """

    resolution = resolve_component_for_asset(
        asset,
        component_mapping
    )

    if resolution["status"] == "matched":
        component_name = resolution["component"]
    elif resolution["status"] == "ambiguous":
        component_name = AMBIGUOUS_COMPONENT_LABEL
    else:
        component_name = UNMAPPED_COMPONENT_LABEL

    return {
        "component_name": component_name,
        "component_mapped": resolution["status"] == "matched",
        "component_status": resolution["status"],
        "component_reason": resolution["reason"],
    }


def _crqc_timing(crqc_year, assessment_year):
    """
    Computes CRQC timing fields using one consistent design:

    - years_until_crqc_z stays non-negative for backward
      compatibility with existing consumers of this field.
    - crqc_status and years_overdue make an already-passed CRQC
      year explicit instead of silently showing "0 years" with
      no context.

    The urgency verdict itself (rules.mosca_urgent) already uses
    the unclamped difference internally; these fields describe the
    same underlying interpretation for display purposes.
    """

    raw_years_until_crqc = crqc_year - assessment_year

    if raw_years_until_crqc <= 0:
        return {
            "years_until_crqc_z": 0,
            "crqc_status": "passed",
            "years_overdue": -raw_years_until_crqc,
        }

    return {
        "years_until_crqc_z": raw_years_until_crqc,
        "crqc_status": "upcoming",
        "years_overdue": 0,
    }


def _build_excluded_entry(
    asset,
    oid,
    oid_location_count,
    component_resolution,
    payment_weight,
    crqc_timing,
    assessment_year,
    crqc_year,
    data_retention_years,
):
    """
    Preserves an algorithm asset that has zero assessable
    dimensions instead of silently dropping it from the report.

    No numerical maturity or priority is fabricated: both remain
    None, and no formula that requires a numerical maturity is
    invoked for this asset.
    """

    return {
        "asset": asset.get("name"),
        "primitive": asset.get("primitive"),
        "crypto_functions": asset.get("crypto_functions", []),
        "parameter_set": asset.get("parameter_set"),
        "oid": oid,
        "locations": asset.get("locations", []),
        "oid_location_count": oid_location_count,
        "component": component_resolution["component_name"],
        "component_mapped": component_resolution["component_mapped"],
        "component_status": component_resolution["component_status"],
        "component_reason": component_resolution["component_reason"],
        "payment_weight": payment_weight,
        "protocol_evidence": {
            "tls_version": None,
            "hybrid": False,
            "source": None,
            "target": None,
            "component_match": False,
            "assessed": False,
        },
        "algorithm_risk": algorithm_risk(asset.get("name")),
        "status": "Not Assessed",
        "excluded_reason": NOT_ASSESSED_REASON,
        "maturity": None,
        "maturity_label": "Not Assessed",
        "confidence": confidence(0),
        "binding_constraints": [],
        "recommendations": [],
        "impact_chain": None,
        "priority": None,
        "dimensions": {
            "d1_coordination": None,
            "d2_pervasiveness": None,
            "d3_protocol": None,
            "d4_material": None,
        },
        "mosca": {
            "assessment_year": assessment_year,
            "base_x_years": None,
            "adjusted_x_years": None,
            "data_retention_y": data_retention_years,
            "crqc_year": crqc_year,
            "migrate_by": None,
            "urgent": None,
            **crqc_timing,
        },
    }


def generate_report(
    cbom_file,
    component_mapping_file,
    cryptolyzer_evidence_file=None,
    base_migration_years=3,
    data_retention_years=7,
    crqc_year=2033,
    assessment_year=None,
):
    """
    Generates a maturity assessment for every algorithm
    asset found in the supplied CycloneDX CBOM.

    Each algorithm asset is independently mapped to:

    - a payment component
    - a payment-context weight
    - matching CryptoLyzer runtime evidence
    - four maturity dimensions
    - binding constraints
    - recommendations
    - a projected impact chain
    - priority and Mosca/HNDL results
    """

    cbom = load_cbom(
        cbom_file
    )

    assets = get_crypto_assets(
        cbom
    )

    oid_location_map = build_oid_location_map(
        assets
    )

    component_mapping = load_component_mapping(
        component_mapping_file
    )

    if cryptolyzer_evidence_file:
        cryptolyzer_evidence = (
            load_cryptolyzer_evidence(
                cryptolyzer_evidence_file
            )
        )
    else:
        cryptolyzer_evidence = {}

    if assessment_year is None:
        assessment_year = date.today().year

    crqc_timing = _crqc_timing(
        crqc_year,
        assessment_year
    )

    report = []

    for asset in assets:

        # Only algorithm assets receive maturity assessments.
        # Related material assets are linked to algorithms through
        # the CycloneDX dependency relationships in parsers.py.
        if asset.get("asset_type") != "algorithm":
            continue

        component_resolution = _resolve_component(
            asset,
            component_mapping
        )

        component_name = component_resolution["component_name"]

        if component_resolution["component_mapped"]:
            payment_weight = get_payment_weight(
                component_name
            )
        else:
            # Unmapped and ambiguous components never receive a
            # real payment-context weight — that would silently
            # imply a component match that was never established.
            payment_weight = 0.0

        # CryptoLyzer evidence is used only if its manually
        # assigned component matches the current CBOM asset's
        # resolved component. Unmapped/ambiguous assets can never
        # match, since component_name is not a real component name.
        cryptolyzer_matches_component = (
            component_resolution["component_mapped"]
            and cryptolyzer_evidence.get("component") == component_name
        )

        cryptolyzer_is_assessed = (
            cryptolyzer_evidence.get(
                "assessed",
                False
            )
        )

        if (
            cryptolyzer_matches_component
            and cryptolyzer_is_assessed
        ):
            tls_version = (
                cryptolyzer_evidence.get(
                    "tls_version"
                )
            )

            hybrid = (
                cryptolyzer_evidence.get(
                    "hybrid",
                    False
                )
            )

            protocol_source = "cryptolyzer"

            protocol_target = (
                cryptolyzer_evidence.get(
                    "target"
                )
            )
        else:
            tls_version = None
            hybrid = False
            protocol_source = None
            protocol_target = None

        oid = asset.get(
            "oid"
        )

        if oid:
            oid_location_count = len(
                oid_location_map.get(
                    oid,
                    set()
                )
            )
        else:
            oid_location_count = 0

        assessment = calculate_maturity(
            asset=asset,
            oid_location_count=oid_location_count,
            tls_version=tls_version,
            hybrid=hybrid,
        )

        if assessment.get("status") == "Not Assessed":
            # Preserve the asset instead of silently dropping it:
            # it exists in evidence but could not be scored on any
            # dimension. No numerical maturity or priority is
            # fabricated for it.
            report.append(
                _build_excluded_entry(
                    asset=asset,
                    oid=oid,
                    oid_location_count=oid_location_count,
                    component_resolution=component_resolution,
                    payment_weight=payment_weight,
                    crqc_timing=crqc_timing,
                    assessment_year=assessment_year,
                    crqc_year=crqc_year,
                    data_retention_years=data_retention_years,
                )
            )
            continue

        maturity = assessment[
            "maturity"
        ]

        risk = algorithm_risk(
            asset.get("name")
        )

        priority = calculate_priority(
            risk,
            payment_weight,
            maturity
        )

        recommendations = get_recommendations(
            assessment
        )

        impact_chain = build_impact_chain(
            assessment,
            recommendations
        )

        adjusted_x = adjusted_migration_time(
            base_migration_years,
            maturity
        )

        deadline = mosca_deadline(
            crqc_year,
            adjusted_x
        )

        urgent = mosca_urgent(
            data_retention_years=data_retention_years,
            adjusted_x=adjusted_x,
            crqc_year=crqc_year,
            assessment_year=assessment_year,
        )

        report.append({
            "asset":
                asset.get("name"),

            "primitive":
                asset.get("primitive"),

            "crypto_functions":
                asset.get(
                    "crypto_functions",
                    []
                ),

            "parameter_set":
                asset.get("parameter_set"),

            "oid":
                oid,

            "locations":
                asset.get(
                    "locations",
                    []
                ),

            "oid_location_count":
                oid_location_count,

            "component":
                component_name,

            "component_mapped":
                component_resolution["component_mapped"],

            "component_status":
                component_resolution["component_status"],

            "component_reason":
                component_resolution["component_reason"],

            "payment_weight":
                payment_weight,

            "protocol_evidence": {
                "tls_version":
                    tls_version,

                "hybrid":
                    hybrid,

                "source":
                    protocol_source,

                "target":
                    protocol_target,

                "component_match":
                    cryptolyzer_matches_component,

                "assessed": (
                    tls_version is not None
                    or hybrid
                ),
            },

            "algorithm_risk":
                risk,

            "status":
                "Assessed",

            "excluded_reason":
                None,

            "maturity":
                maturity,

            "maturity_label":
                assessment["maturity_label"],

            "confidence":
                assessment["confidence"],

            "binding_constraints":
                assessment[
                    "binding_constraints"
                ],

            "recommendations":
                recommendations,

            "impact_chain":
                impact_chain,

            "priority":
                priority,

            "dimensions": {
                "d1_coordination":
                    assessment["d1"],

                "d2_pervasiveness":
                    assessment["d2"],

                "d3_protocol":
                    assessment["d3"],

                "d4_material":
                    assessment["d4"],
            },

            "mosca": {
                "assessment_year":
                    assessment_year,

                "base_x_years":
                    base_migration_years,

                "adjusted_x_years":
                    adjusted_x,

                "data_retention_y":
                    data_retention_years,

                "crqc_year":
                    crqc_year,

                "migrate_by":
                    deadline,

                "urgent":
                    urgent,

                **crqc_timing,
            },
        })

    # Highest-priority assets appear first. Excluded ("Not
    # Assessed") assets have no numerical priority and are sorted
    # to the end rather than raising a TypeError against numeric
    # priorities.
    report.sort(
        key=lambda item: (
            item["priority"] is not None,
            item["priority"] or 0,
        ),
        reverse=True
    )

    return report