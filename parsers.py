import json


def load_json(file_path):
    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def load_cbom(file_path):
    return load_json(file_path)


def normalize_path(path):
    return (
        (path or "")
        .replace("\\", "/")
        .lower()
        .strip()
    )


def build_material_link_map(cbom):
    """
    Links algorithm components to related crypto-material
    components through CycloneDX dependency relationships.

    Example:
        private-key dependsOn RSA-2048

    Output:
        RSA bom-ref -> private-key
    """

    components = cbom.get(
        "components",
        []
    )

    dependencies = cbom.get(
        "dependencies",
        []
    )

    material_assets = {}

    for component in components:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        if (
            crypto.get("assetType")
            != "related-crypto-material"
        ):
            continue

        material = crypto.get(
            "relatedCryptoMaterialProperties",
            {}
        )

        bom_ref = component.get(
            "bom-ref"
        )

        material_type = material.get(
            "type"
        )

        if bom_ref and material_type:
            material_assets[bom_ref] = {
                "type": material_type,
                "size": material.get("size"),
            }

    algorithm_material_map = {}

    for dependency in dependencies:
        material_ref = dependency.get(
            "ref"
        )

        material_details = material_assets.get(
            material_ref
        )

        if not material_details:
            continue

        for algorithm_ref in dependency.get(
            "dependsOn",
            []
        ):
            algorithm_material_map[
                algorithm_ref
            ] = material_details

    return algorithm_material_map


def get_crypto_assets(cbom):
    """
    Extracts algorithm and crypto-material evidence from
    CycloneDX CBOM components.
    """

    components = cbom.get(
        "components",
        []
    )

    material_map = build_material_link_map(
        cbom
    )

    assets = []

    for component in components:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        algorithm = crypto.get(
            "algorithmProperties",
            {}
        )

        occurrences = (
            component
            .get("evidence", {})
            .get("occurrences", [])
        )

        bom_ref = component.get(
            "bom-ref"
        )

        linked_material = material_map.get(
            bom_ref,
            {}
        )

        assets.append({
            "bom_ref":
                bom_ref,

            "name":
                component.get("name"),

            "asset_type":
                crypto.get("assetType"),

            "primitive":
                algorithm.get("primitive"),

            "crypto_functions":
                algorithm.get(
                    "cryptoFunctions",
                    []
                ),

            "parameter_set":
                algorithm.get(
                    "parameterSetIdentifier"
                ),

            "oid":
                crypto.get("oid"),

            "material_type":
                linked_material.get("type"),

            "material_size":
                linked_material.get("size"),

            "locations": [
                occurrence.get("location")
                for occurrence in occurrences
                if occurrence.get("location")
            ],

            "additional_context": [
                occurrence.get(
                    "additionalContext"
                )
                for occurrence in occurrences
                if occurrence.get(
                    "additionalContext"
                )
            ],
        })

    return assets


def build_oid_location_map(assets):
    """
    Maps each algorithm OID to all distinct source-code
    locations where that OID was detected.

    Used for D2: Implementation Pervasiveness.
    """

    oid_map = {}

    for asset in assets:
        if asset.get("asset_type") != "algorithm":
            continue

        oid = asset.get("oid")

        if not oid:
            continue

        oid_map.setdefault(
            oid,
            set()
        )

        for location in asset.get(
            "locations",
            []
        ):
            if location:
                oid_map[oid].add(
                    normalize_path(location)
                )

    return oid_map


def load_component_mapping(file_path):
    """
    Loads path marker to payment-component mapping.

    Example:
        "pki" -> "PKI Infrastructure"
        "vpn" -> "VPN Infrastructure"
    """

    return load_json(file_path)


def path_contains_marker(
    file_path,
    path_marker
):
    """
    Checks whether a configured marker exists as a full
    path segment rather than as an arbitrary substring.
    """

    normalized_path = normalize_path(
        file_path
    )

    normalized_marker = normalize_path(
        path_marker
    ).strip("/")

    path_segments = [
        segment
        for segment in normalized_path.split("/")
        if segment
    ]

    marker_segments = [
        segment
        for segment in normalized_marker.split("/")
        if segment
    ]

    if not marker_segments:
        return False

    marker_length = len(
        marker_segments
    )

    for index in range(
        len(path_segments)
        - marker_length
        + 1
    ):
        if (
            path_segments[
                index:index + marker_length
            ]
            == marker_segments
        ):
            return True

    return False


def resolve_component_for_path(
    file_path,
    component_mapping
):
    """
    Resolves one file path to a payment component, reporting
    an explicit status rather than silently picking a match.

    A single path can legitimately match several markers that
    all resolve to the *same* component name (e.g. "pki" and
    "certificate_authority" both mapping to "PKI Infrastructure").
    That case is still "matched". A path that satisfies markers
    belonging to *different* component names is "ambiguous" and
    must not silently resolve to whichever marker happened to be
    first in the mapping dictionary.

    Returns
    -------
    dict with:
        status           : "matched" | "unmapped" | "ambiguous"
        component        : component name, or None
        matched_markers  : path markers that matched this path
    """

    components_by_marker = {}

    for path_marker, component_name in (
        component_mapping.items()
    ):
        if path_contains_marker(
            file_path,
            path_marker
        ):
            components_by_marker.setdefault(
                component_name,
                []
            ).append(path_marker)

    if not components_by_marker:
        return {
            "status": "unmapped",
            "component": None,
            "matched_markers": [],
        }

    if len(components_by_marker) > 1:
        return {
            "status": "ambiguous",
            "component": None,
            "matched_markers": sorted(
                marker
                for markers in components_by_marker.values()
                for marker in markers
            ),
        }

    (component_name, matched_markers), = (
        components_by_marker.items()
    )

    return {
        "status": "matched",
        "component": component_name,
        "matched_markers": matched_markers,
    }


def get_component_for_path(
    file_path,
    component_mapping
):
    """
    Resolves one file path to a payment component.

    Returns the component name only when resolution is
    unambiguous. Returns None for both "unmapped" and
    "ambiguous" outcomes — callers needing to distinguish
    those two cases should use resolve_component_for_path().
    """

    resolution = resolve_component_for_path(
        file_path,
        component_mapping
    )

    if resolution["status"] == "matched":
        return resolution["component"]

    return None


def resolve_component_for_asset(
    asset,
    component_mapping
):
    """
    Resolves the payment component for a CBOM asset using
    the asset occurrence locations, reporting an explicit
    status and reason rather than silently choosing one
    component.

    Returns
    -------
    dict with:
        status     : "matched" | "unmapped" | "ambiguous"
        component  : component name, or None
        reason     : human-readable explanation, or None
    """

    locations = asset.get(
        "locations",
        []
    )

    if not locations:
        return {
            "status": "unmapped",
            "component": None,
            "reason": (
                "The asset has no CBOM occurrence locations "
                "to resolve a component from."
            ),
        }

    per_location = [
        resolve_component_for_path(
            location,
            component_mapping
        )
        for location in locations
    ]

    if any(
        resolution["status"] == "ambiguous"
        for resolution in per_location
    ):
        return {
            "status": "ambiguous",
            "component": None,
            "reason": (
                "At least one occurrence location matches "
                "multiple configured component markers that "
                "resolve to different components."
            ),
        }

    matched_components = {
        resolution["component"]
        for resolution in per_location
        if resolution["status"] == "matched"
    }

    if not matched_components:
        return {
            "status": "unmapped",
            "component": None,
            "reason": (
                "No configured component marker matched any "
                "occurrence location for this asset."
            ),
        }

    if len(matched_components) > 1:
        return {
            "status": "ambiguous",
            "component": None,
            "reason": (
                "Occurrence locations resolve to more than one "
                "distinct payment component: "
                + ", ".join(sorted(matched_components))
                + "."
            ),
        }

    (component_name,) = matched_components

    return {
        "status": "matched",
        "component": component_name,
        "reason": None,
    }


def get_component_for_asset(
    asset,
    component_mapping
):
    """
    Resolves the payment component for a CBOM asset using
    the asset occurrence locations.

    Returns the component name only when resolution is
    unambiguous. Returns None for both "unmapped" and
    "ambiguous" outcomes — callers needing to distinguish
    those two cases should use resolve_component_for_asset().
    """

    resolution = resolve_component_for_asset(
        asset,
        component_mapping
    )

    if resolution["status"] == "matched":
        return resolution["component"]

    return None


def load_cryptolyzer_evidence(file_path):
    """
    Loads normalized runtime protocol evidence generated
    from an authorized CryptoLyzer endpoint scan.
    """

    return load_json(file_path)


