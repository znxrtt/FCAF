from pathlib import Path

from rules import pervasiveness_score
from parsers import (
    load_cbom,
    get_crypto_assets,
    build_oid_location_map,
    load_component_mapping,
    resolve_component_for_asset,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

CBOM_FILE = (
    PROJECT_ROOT
    / "evidence_samples"
    / "cbom_multi_location.json"
)

COMPONENT_MAPPING_FILE = (
    PROJECT_ROOT
    / "component_mapping.json"
)

RSA_OID = "1.2.840.113549.1.1.1"


def test_rsa_oid_found_in_three_distinct_source_files():
    cbom = load_cbom(CBOM_FILE)
    assets = get_crypto_assets(cbom)

    oid_map = build_oid_location_map(assets)

    assert len(oid_map[RSA_OID]) == 3


def test_rsa_locations_resolve_to_pki_infrastructure():
    cbom = load_cbom(CBOM_FILE)
    assets = get_crypto_assets(cbom)

    mapping = load_component_mapping(COMPONENT_MAPPING_FILE)

    rsa_asset = next(
        asset
        for asset in assets
        if asset.get("oid") == RSA_OID
    )

    assert len(rsa_asset["locations"]) == 3

    resolution = resolve_component_for_asset(
        rsa_asset,
        mapping
    )

    assert resolution["status"] == "matched"
    assert resolution["component"] == "PKI Infrastructure"


def test_rsa_pervasiveness_is_level_2():
    cbom = load_cbom(CBOM_FILE)
    assets = get_crypto_assets(cbom)

    oid_map = build_oid_location_map(assets)

    location_count = len(oid_map[RSA_OID])

    assert pervasiveness_score(location_count) == 2
