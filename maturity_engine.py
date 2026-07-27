from rules import (
    coordination_score,
    pervasiveness_score,
    protocol_score,
    material_score,
    confidence,
    level_label,
)


def calculate_maturity(
    asset,
    oid_location_count,
    tls_version="TLS1.2",
    hybrid=False
):
    """
    Scores a single CBOM asset against the four dimensions
    and returns the component maturity level.

    Parameters
    ----------
    asset              : dict from parsers.get_crypto_assets()
    oid_location_count : int — number of distinct file locations
                         this asset's OID appears in across the
                         whole CBOM (built by parsers.build_oid_location_map)
    tls_version        : str  e.g. "TLS1.2", "TLS1.3"
    hybrid             : bool — True if PQC-capable cipher detected

    Returns
    -------
    dict with d1, d2, d3, d4, maturity, confidence
    or {"status": "Not Assessed"} if no dimensions can be scored.
    """

    # D1: Migration Coordination Complexity
    d1 = coordination_score(asset.get("primitive"))

    # D2: Implementation Pervasiveness
    # Uses OID occurrence count across the full CBOM,
    # not only this asset's own locations.
    d2 = pervasiveness_score(oid_location_count)

    # D3: Protocol Agility
    d3 = protocol_score(tls_version, hybrid)

    # D4: Persistent Crypto Material Evidence
    d4 = material_score(
        asset.get("material_type"),
        asset.get("primitive")
    )

    # Collect only scored dimensions (None = Not Assessed)
    dimension_names = {
    "Migration Coordination Complexity": d1,
    "Implementation Pervasiveness": d2,
    "Protocol Agility": d3,
    "Persistent Crypto Material Evidence": d4,
}
    

    assessed = {
        k: v
        for k, v in dimension_names.items()
        if v is not None
    }

    if not assessed:
        return {"status": "Not Assessed"}

    maturity = min(
        assessed.values()
    )

    binding = [
        name
        for name, score in assessed.items()
        if score == maturity
    ]

    return {
        "d1": d1,
        "d2": d2,
        "d3": d3,
        "d4": d4,
        "maturity": maturity,
        "maturity_label": level_label(maturity),
        "binding_constraints": binding,
        "confidence": confidence(len(assessed)),
    }