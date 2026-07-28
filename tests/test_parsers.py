from pathlib import Path

from parsers import (
    load_json,
    load_cbom,
    normalize_path,
    build_material_link_map,
    get_crypto_assets,
    build_oid_location_map,
    load_component_mapping,
    path_contains_marker,
    get_component_for_path,
    get_component_for_asset,
    resolve_component_for_path,
    resolve_component_for_asset,
    load_cryptolyzer_evidence,
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


# Generic JSON loading

def test_load_json_returns_dictionary():
    data = load_json(
        CBOM_FILE
    )

    assert isinstance(
        data,
        dict
    )


def test_load_cbom_returns_cyclonedx_document():
    cbom = load_cbom(
        CBOM_FILE
    )

    assert cbom["bomFormat"] == "CycloneDX"
    assert cbom["specVersion"] == "1.6"
    assert "components" in cbom
    assert "dependencies" in cbom


# Path normalization

def test_normalize_windows_path():
    path = (
        r"Payment_Simulation\PKI"
        r"\Certificate_Manager.py"
    )

    normalized = normalize_path(
        path
    )

    assert normalized == (
        "payment_simulation/pki/"
        "certificate_manager.py"
    )


def test_normalize_empty_path():
    assert normalize_path(
        None
    ) == ""


# Material dependency mapping

def test_build_material_link_map():
    cbom = load_cbom(
        CBOM_FILE
    )

    material_map = build_material_link_map(
        cbom
    )

    algorithm_component = next(
        component
        for component in cbom["components"]
        if (
            component
            .get("cryptoProperties", {})
            .get("assetType")
            == "algorithm"
        )
    )

    algorithm_ref = algorithm_component[
        "bom-ref"
    ]

    assert algorithm_ref in material_map

    assert (
        material_map[
            algorithm_ref
        ]["type"]
        == "private-key"
    )

    assert (
        material_map[
            algorithm_ref
        ]["size"]
        == 2048
    )


# Asset extraction

def test_get_crypto_assets_returns_components():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    assert isinstance(
        assets,
        list
    )

    assert len(assets) == 2


def test_algorithm_asset_is_extracted():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    algorithm_assets = [
        asset
        for asset in assets
        if asset["asset_type"] == "algorithm"
    ]

    assert len(
        algorithm_assets
    ) == 1

    rsa_asset = algorithm_assets[0]

    assert rsa_asset["name"] == "RSA-2048"
    assert rsa_asset["primitive"] == "pke"

    assert rsa_asset[
        "crypto_functions"
    ] == ["keygen"]

    assert rsa_asset[
        "parameter_set"
    ] == "2048"

    assert rsa_asset["oid"] == (
        "1.2.840.113549.1.1.1"
    )


def test_algorithm_receives_linked_material():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    rsa_asset = next(
        asset
        for asset in assets
        if asset["name"] == "RSA-2048"
    )

    assert (
        rsa_asset["material_type"]
        == "private-key"
    )

    assert (
        rsa_asset["material_size"]
        == 2048
    )


def test_algorithm_location_is_extracted():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    rsa_asset = next(
        asset
        for asset in assets
        if asset["name"] == "RSA-2048"
    )

    assert rsa_asset[
        "locations"
    ] == [
        (
            "payment_simulation/pki/"
            "certificate_manager.py"
        )
    ]


def test_additional_context_is_extracted():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    rsa_asset = next(
        asset
        for asset in assets
        if asset["name"] == "RSA-2048"
    )

    assert rsa_asset[
        "additional_context"
    ] == [
        "generate_private_key"
    ]


# OID location mapping

def test_oid_location_map():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    oid_map = build_oid_location_map(
        assets
    )

    rsa_oid = (
        "1.2.840.113549.1.1.1"
    )

    assert rsa_oid in oid_map

    assert len(
        oid_map[rsa_oid]
    ) == 1

    assert (
        "payment_simulation/pki/"
        "certificate_manager.py"
        in oid_map[rsa_oid]
    )


def test_oid_map_dedupes_same_normalized_location():
    # Two occurrences that normalize to the same file path
    # (differing only in case/separators) must count as one
    # distinct source location, not two.
    assets = [
        {
            "asset_type": "algorithm",
            "oid": "1.2.840.113549.1.1.1",
            "locations": [
                "payment_simulation/pki/key_manager.py",
                r"Payment_Simulation\PKI\Key_Manager.py",
            ],
        }
    ]

    oid_map = build_oid_location_map(assets)

    assert len(
        oid_map["1.2.840.113549.1.1.1"]
    ) == 1


def test_oid_map_excludes_material_assets():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    oid_map = build_oid_location_map(
        assets
    )

    assert len(oid_map) == 1


# Component mapping

def test_load_component_mapping():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    assert (
        mapping["pki"]
        == "PKI Infrastructure"
    )

    assert (
        mapping["vpn"]
        == "VPN Infrastructure"
    )


def test_path_contains_full_segment_marker():
    file_path = (
        "payment_simulation/pki/"
        "certificate_manager.py"
    )

    assert path_contains_marker(
        file_path,
        "pki"
    ) is True


def test_path_marker_does_not_match_partial_text():
    file_path = (
        "payment_simulation/"
        "pki_backup_service/"
        "manager.py"
    )

    assert path_contains_marker(
        file_path,
        "pki"
    ) is False


def test_get_component_for_path():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    component = get_component_for_path(
        (
            "payment_simulation/pki/"
            "certificate_manager.py"
        ),
        mapping
    )

    assert (
        component
        == "PKI Infrastructure"
    )


def test_get_component_for_asset():
    cbom = load_cbom(
        CBOM_FILE
    )

    assets = get_crypto_assets(
        cbom
    )

    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    rsa_asset = next(
        asset
        for asset in assets
        if asset["name"] == "RSA-2048"
    )

    component = get_component_for_asset(
        rsa_asset,
        mapping
    )

    assert (
        component
        == "PKI Infrastructure"
    )


def test_unmapped_asset_returns_none():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    asset = {
        "locations": [
            "unknown/service.py"
        ]
    }

    component = get_component_for_asset(
        asset,
        mapping
    )

    assert component is None


def test_asset_with_conflicting_components_returns_none():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    asset = {
        "locations": [
            (
                "payment_simulation/pki/"
                "certificate_manager.py"
            ),
            (
                "payment_simulation/vpn/"
                "tunnel_manager.py"
            ),
        ]
    }

    component = get_component_for_asset(
        asset,
        mapping
    )

    assert component is None


# Explicit ambiguous/unmapped resolution status

def test_resolve_component_for_path_matched():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    resolution = resolve_component_for_path(
        (
            "payment_simulation/pki/"
            "certificate_manager.py"
        ),
        mapping
    )

    assert resolution["status"] == "matched"
    assert resolution["component"] == "PKI Infrastructure"


def test_resolve_component_for_path_unmapped():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    resolution = resolve_component_for_path(
        "unknown/service.py",
        mapping
    )

    assert resolution["status"] == "unmapped"
    assert resolution["component"] is None


def test_single_path_matching_multiple_markers_is_ambiguous():
    # One individual path satisfies two markers that map to two
    # DIFFERENT components. The first dictionary entry must not
    # be silently chosen — this must report "ambiguous", not
    # silently resolve to whichever marker appears first.
    mapping = {
        "vpn": "VPN Infrastructure",
        "pki": "PKI Infrastructure",
    }

    resolution = resolve_component_for_path(
        "payment_simulation/vpn/pki/gateway.py",
        mapping
    )

    assert resolution["status"] == "ambiguous"
    assert resolution["component"] is None
    assert set(resolution["matched_markers"]) == {"vpn", "pki"}


def test_single_path_matching_markers_for_same_component_is_matched():
    # Two markers ("pki" and "certificate_authority") that both
    # resolve to the same component name are NOT ambiguous.
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    resolution = resolve_component_for_path(
        (
            "payment_simulation/certificate_authority/"
            "pki/manager.py"
        ),
        mapping
    )

    assert resolution["status"] == "matched"
    assert resolution["component"] == "PKI Infrastructure"


def test_resolve_component_for_asset_ambiguous_single_location():
    mapping = {
        "vpn": "VPN Infrastructure",
        "pki": "PKI Infrastructure",
    }

    asset = {
        "locations": [
            "payment_simulation/vpn/pki/gateway.py",
        ]
    }

    resolution = resolve_component_for_asset(
        asset,
        mapping
    )

    assert resolution["status"] == "ambiguous"
    assert resolution["component"] is None
    assert resolution["reason"]


def test_resolve_component_for_asset_ambiguous_across_locations():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    asset = {
        "locations": [
            (
                "payment_simulation/pki/"
                "certificate_manager.py"
            ),
            (
                "payment_simulation/vpn/"
                "tunnel_manager.py"
            ),
        ]
    }

    resolution = resolve_component_for_asset(
        asset,
        mapping
    )

    assert resolution["status"] == "ambiguous"
    assert resolution["component"] is None
    assert resolution["reason"]


def test_resolve_component_for_asset_unmapped_has_reason():
    mapping = load_component_mapping(
        COMPONENT_MAPPING_FILE
    )

    asset = {
        "locations": [
            "unknown/service.py"
        ]
    }

    resolution = resolve_component_for_asset(
        asset,
        mapping
    )

    assert resolution["status"] == "unmapped"
    assert resolution["component"] is None
    assert resolution["reason"]


# CryptoLyzer evidence

def test_load_cryptolyzer_evidence():
    evidence = load_cryptolyzer_evidence(
        CRYPTOLYZER_FILE
    )

    assert (
        evidence["component"]
        == "PKI Infrastructure"
    )

    assert (
        evidence["source"]
        == "cryptolyzer"
    )

    assert (
        evidence["tls_version"]
        == "TLS1.2"
    )

    assert evidence["hybrid"] is False
    assert evidence["assessed"] is True


def test_cryptolyzer_target():
    evidence = load_cryptolyzer_evidence(
        CRYPTOLYZER_FILE
    )

    target = evidence["target"]

    assert target["scheme"] == "tls"
    assert target["address"] == "localhost"
    assert target["ip"] == "127.0.0.1"
    assert target["port"] == 8443