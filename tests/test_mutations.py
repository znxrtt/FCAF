import copy
from pathlib import Path

from maturity_engine import calculate_maturity
from parsers import (
    load_cbom,
    get_crypto_assets,
    build_oid_location_map,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

CBOM_FILE = (
    PROJECT_ROOT
    / "test_data"
    / "cbom.json"
)


def get_algorithm_asset(cbom):
    assets = get_crypto_assets(cbom)

    return next(
        asset
        for asset in assets
        if asset.get("asset_type") == "algorithm"
    )


def assess_asset(
    asset,
    location_count,
    tls_version="TLS1.2",
    hybrid=False,
):
    return calculate_maturity(
        asset=asset,
        oid_location_count=location_count,
        tls_version=tls_version,
        hybrid=hybrid,
    )


# D1 mutation:
# Change primitive from PKE to signature.

def test_mutating_pke_to_signature_lowers_d1():
    original_cbom = load_cbom(
        CBOM_FILE
    )

    mutated_cbom = copy.deepcopy(
        original_cbom
    )

    original_asset = get_algorithm_asset(
        original_cbom
    )

    for component in mutated_cbom["components"]:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        if crypto.get("assetType") == "algorithm":
            crypto[
                "algorithmProperties"
            ]["primitive"] = "signature"

    mutated_asset = get_algorithm_asset(
        mutated_cbom
    )

    original_result = assess_asset(
        original_asset,
        location_count=1,
    )

    mutated_result = assess_asset(
        mutated_asset,
        location_count=1,
    )

    assert original_result["d1"] == 2
    assert mutated_result["d1"] == 1


# D1 mutation:
# Change primitive from PKE to KEM.

def test_mutating_pke_to_kem_improves_d1():
    original_cbom = load_cbom(
        CBOM_FILE
    )

    mutated_cbom = copy.deepcopy(
        original_cbom
    )

    original_asset = get_algorithm_asset(
        original_cbom
    )

    for component in mutated_cbom["components"]:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        if crypto.get("assetType") == "algorithm":
            crypto[
                "algorithmProperties"
            ]["primitive"] = "kem"

    mutated_asset = get_algorithm_asset(
        mutated_cbom
    )

    original_result = assess_asset(
        original_asset,
        location_count=1,
    )

    mutated_result = assess_asset(
        mutated_asset,
        location_count=1,
    )

    assert original_result["d1"] == 2
    assert mutated_result["d1"] == 3


# D2 mutation:
# Add occurrences for the same OID in five files.

def test_mutating_one_location_to_five_lowers_d2():
    original_cbom = load_cbom(
        CBOM_FILE
    )

    mutated_cbom = copy.deepcopy(
        original_cbom
    )

    for component in mutated_cbom["components"]:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        if crypto.get("assetType") == "algorithm":
            component["evidence"]["occurrences"] = [
                {"location": "service/file1.py"},
                {"location": "service/file2.py"},
                {"location": "service/file3.py"},
                {"location": "service/file4.py"},
                {"location": "service/file5.py"},
            ]

    original_assets = get_crypto_assets(
        original_cbom
    )

    mutated_assets = get_crypto_assets(
        mutated_cbom
    )

    original_oid_map = build_oid_location_map(
        original_assets
    )

    mutated_oid_map = build_oid_location_map(
        mutated_assets
    )

    original_asset = next(
        asset
        for asset in original_assets
        if asset.get("asset_type") == "algorithm"
    )

    mutated_asset = next(
        asset
        for asset in mutated_assets
        if asset.get("asset_type") == "algorithm"
    )

    oid = original_asset["oid"]

    original_count = len(
        original_oid_map[oid]
    )

    mutated_count = len(
        mutated_oid_map[oid]
    )

    original_result = assess_asset(
        original_asset,
        location_count=original_count,
    )

    mutated_result = assess_asset(
        mutated_asset,
        location_count=mutated_count,
    )

    assert original_count == 1
    assert mutated_count == 5

    assert original_result["d2"] == 4
    assert mutated_result["d2"] == 1


# D2 mutation:
# Duplicate occurrences in the same file must not increase
# pervasiveness because D2 counts distinct locations.

def test_duplicate_locations_do_not_change_d2():
    cbom = load_cbom(
        CBOM_FILE
    )

    mutated_cbom = copy.deepcopy(
        cbom
    )

    for component in mutated_cbom["components"]:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        if crypto.get("assetType") == "algorithm":
            component["evidence"]["occurrences"] = [
                {"location": "service/crypto.py"},
                {"location": "service/crypto.py"},
                {"location": "service/crypto.py"},
            ]

    assets = get_crypto_assets(
        mutated_cbom
    )

    oid_map = build_oid_location_map(
        assets
    )

    asset = next(
        item
        for item in assets
        if item.get("asset_type") == "algorithm"
    )

    location_count = len(
        oid_map[asset["oid"]]
    )

    result = assess_asset(
        asset,
        location_count=location_count,
    )

    assert location_count == 1
    assert result["d2"] == 4


# D3 mutation:
# Change runtime protocol evidence from TLS 1.2 to TLS 1.3.

def test_mutating_tls12_to_tls13_improves_d3():
    cbom = load_cbom(
        CBOM_FILE
    )

    asset = get_algorithm_asset(
        cbom
    )

    tls12_result = assess_asset(
        asset,
        location_count=1,
        tls_version="TLS1.2",
    )

    tls13_result = assess_asset(
        asset,
        location_count=1,
        tls_version="TLS1.3",
    )

    assert tls12_result["d3"] == 2
    assert tls13_result["d3"] == 3


# D3 mutation:
# Hybrid runtime evidence must return Level 4.

def test_adding_hybrid_evidence_improves_d3_to_level_4():
    cbom = load_cbom(
        CBOM_FILE
    )

    asset = get_algorithm_asset(
        cbom
    )

    result = assess_asset(
        asset,
        location_count=1,
        tls_version="TLS1.3",
        hybrid=True,
    )

    assert result["d3"] == 4


# D3 mutation:
# Removing runtime evidence makes D3 Not Assessed.

def test_removing_protocol_evidence_makes_d3_not_assessed():
    cbom = load_cbom(
        CBOM_FILE
    )

    asset = get_algorithm_asset(
        cbom
    )

    result = assess_asset(
        asset,
        location_count=1,
        tls_version=None,
        hybrid=False,
    )

    assert result["d3"] is None


# D4 mutation:
# Change linked material from private-key to certificate.

def test_mutating_material_to_certificate_sets_d4_level_1():
    original_cbom = load_cbom(
        CBOM_FILE
    )

    mutated_cbom = copy.deepcopy(
        original_cbom
    )

    for component in mutated_cbom["components"]:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        if (
            crypto.get("assetType")
            == "related-crypto-material"
        ):
            crypto[
                "relatedCryptoMaterialProperties"
            ]["type"] = "certificate"

    mutated_asset = get_algorithm_asset(
        mutated_cbom
    )

    result = assess_asset(
        mutated_asset,
        location_count=1,
    )

    assert mutated_asset["material_type"] == "certificate"
    assert result["d4"] == 1


# Overall maturity mutation:
# Adding a certificate should introduce a Level 1 blocker.

def test_certificate_mutation_lowers_overall_maturity():
    original_cbom = load_cbom(
        CBOM_FILE
    )

    mutated_cbom = copy.deepcopy(
        original_cbom
    )

    original_asset = get_algorithm_asset(
        original_cbom
    )

    for component in mutated_cbom["components"]:
        crypto = component.get(
            "cryptoProperties",
            {}
        )

        if (
            crypto.get("assetType")
            == "related-crypto-material"
        ):
            crypto[
                "relatedCryptoMaterialProperties"
            ]["type"] = "certificate"

    mutated_asset = get_algorithm_asset(
        mutated_cbom
    )

    original_result = assess_asset(
        original_asset,
        location_count=1,
    )

    mutated_result = assess_asset(
        mutated_asset,
        location_count=1,
    )

    assert original_result["maturity"] == 2
    assert mutated_result["maturity"] == 1

    assert (
        "Persistent Crypto Material Evidence"
        in mutated_result["binding_constraints"]
    )