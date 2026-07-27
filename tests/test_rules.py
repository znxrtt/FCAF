from rules import (
    coordination_score,
    pervasiveness_score,
    protocol_score,
    material_score,
    confidence,
    algorithm_risk,
    calculate_priority,
    get_payment_weight,
    level_label,
)


# D1: Migration Coordination Complexity

def test_d1_signature_returns_level_1():
    assert coordination_score("signature") == 1


def test_d1_pke_returns_level_2():
    assert coordination_score("pke") == 2


def test_d1_kem_and_keyagreement_return_level_3():
    assert coordination_score("kem") == 3
    assert coordination_score("keyagreement") == 3


def test_d1_hash_mac_kdf_return_level_4():
    assert coordination_score("hash") == 4
    assert coordination_score("mac") == 4
    assert coordination_score("kdf") == 4


def test_d1_unknown_primitive_is_not_assessed():
    assert coordination_score("unknown") is None
    assert coordination_score(None) is None


# D2: Implementation Pervasiveness

def test_d2_one_location_returns_level_4():
    assert pervasiveness_score(1) == 4


def test_d2_two_locations_returns_level_3():
    assert pervasiveness_score(2) == 3


def test_d2_three_to_four_locations_return_level_2():
    assert pervasiveness_score(3) == 2
    assert pervasiveness_score(4) == 2


def test_d2_five_or_more_locations_return_level_1():
    assert pervasiveness_score(5) == 1
    assert pervasiveness_score(10) == 1


def test_d2_missing_location_evidence_is_not_assessed():
    assert pervasiveness_score(0) is None
    assert pervasiveness_score(None) is None


# D3: Protocol Agility

def test_d3_legacy_tls_returns_level_1():
    assert protocol_score("TLS1.0") == 1
    assert protocol_score("TLS1.1") == 1


def test_d3_tls12_returns_level_2():
    assert protocol_score("TLS1.2") == 2


def test_d3_tls13_returns_level_3():
    assert protocol_score("TLS1.3") == 3


def test_d3_hybrid_returns_level_4():
    assert protocol_score(
        "TLS1.3",
        hybrid=True
    ) == 4


def test_d3_missing_or_unknown_evidence_is_not_assessed():
    assert protocol_score(None) is None
    assert protocol_score("UNKNOWN") is None


# D4: Persistent Crypto Material Evidence

def test_d4_certificate_returns_level_1():
    assert material_score(
        "certificate",
        "pke"
    ) == 1


def test_d4_private_key_signature_returns_level_2():
    assert material_score(
        "private-key",
        "signature"
    ) == 2


def test_d4_private_key_keyagreement_returns_level_3():
    assert material_score(
        "private-key",
        "keyagreement"
    ) == 3


def test_d4_private_key_kem_returns_level_3():
    assert material_score(
        "private-key",
        "kem"
    ) == 3


def test_d4_no_material_returns_level_4():
    assert material_score(
        None,
        "pke"
    ) == 4


def test_d4_private_key_pke_is_not_assessed():
    assert material_score(
        "private-key",
        "pke"
    ) is None


# Confidence

def test_confidence_levels():
    assert confidence(4) == "High"
    assert confidence(3) == "Medium"
    assert confidence(2) == "Low"
    assert confidence(1) == "Low"
    assert confidence(0) == "Low"


# Maturity labels

def test_maturity_level_labels():
    assert level_label(1) == "Rigid"
    assert level_label(2) == "Constrained"
    assert level_label(3) == "Adaptable"
    assert level_label(4) == "Agile"
    assert level_label(None) == "Unknown"


# Payment weights

def test_payment_weights():
    assert get_payment_weight(
        "Payment Gateway"
    ) == 1.0

    assert get_payment_weight(
        "PKI Infrastructure"
    ) == 0.8

    assert get_payment_weight(
        "Open Banking API"
    ) == 0.7

    assert get_payment_weight(
        "VPN Infrastructure"
    ) == 0.6

    assert get_payment_weight(
        "Internal Services"
    ) == 0.3


def test_unknown_component_uses_default_weight():
    assert get_payment_weight(
        "Unknown Component"
    ) == 0.3


# Algorithm risk

def test_high_risk_algorithms():
    assert algorithm_risk("SHA1") == 4
    assert algorithm_risk("SHA-1") == 4
    assert algorithm_risk("MD5") == 4


def test_quantum_vulnerable_asymmetric_algorithms():
    assert algorithm_risk("RSA-2048") == 3
    assert algorithm_risk("ECDH") == 3
    assert algorithm_risk("ECDSA") == 3


def test_default_algorithm_risk():
    assert algorithm_risk("AES-256") == 2
    assert algorithm_risk("SHA256") == 2
    assert algorithm_risk(None) == 2


# Priority calculation

def test_priority_calculation():
    priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=2
    )

    assert priority == 7.2


def test_priority_for_agile_asset():
    priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=4
    )

    assert priority == 2.4


def test_priority_for_unmapped_component():
    priority = calculate_priority(
        risk=3,
        weight=0.0,
        maturity=2
    )

    assert priority == 0.0