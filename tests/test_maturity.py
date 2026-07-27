from maturity_engine import calculate_maturity


def make_asset(
    primitive=None,
    material_type=None
):
    return {
        "primitive": primitive,
        "material_type": material_type,
    }


def test_current_rsa_example():
    asset = make_asset(
        primitive="pke",
        material_type="private-key"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.2",
        hybrid=False,
    )

    assert result["d1"] == 2
    assert result["d2"] == 4
    assert result["d3"] == 2
    assert result["d4"] is None

    assert result["maturity"] == 2
    assert result["maturity_label"] == "Constrained"
    assert result["confidence"] == "Medium"

    assert result["binding_constraints"] == [
        "Migration Coordination Complexity",
        "Protocol Agility",
    ]


def test_minimum_rule_uses_lowest_dimension():
    asset = make_asset(
        primitive="signature",
        material_type="certificate"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.3",
        hybrid=False,
    )

    assert result["d1"] == 1
    assert result["d2"] == 4
    assert result["d3"] == 3
    assert result["d4"] == 1

    assert result["maturity"] == 1
    assert result["maturity_label"] == "Rigid"


def test_tied_binding_constraints_are_returned():
    asset = make_asset(
        primitive="pke",
        material_type=None
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=3,
        tls_version="TLS1.2",
        hybrid=False,
    )

    assert result["d1"] == 2
    assert result["d2"] == 2
    assert result["d3"] == 2
    assert result["d4"] == 4

    assert result["maturity"] == 2

    assert result["binding_constraints"] == [
        "Migration Coordination Complexity",
        "Implementation Pervasiveness",
        "Protocol Agility",
    ]


def test_not_assessed_dimensions_are_excluded():
    asset = make_asset(
        primitive="pke",
        material_type="private-key"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=0,
        tls_version=None,
        hybrid=False,
    )

    assert result["d1"] == 2
    assert result["d2"] is None
    assert result["d3"] is None
    assert result["d4"] is None

    assert result["maturity"] == 2
    assert result["confidence"] == "Low"

    assert result["binding_constraints"] == [
        "Migration Coordination Complexity"
    ]


def test_high_confidence_when_all_dimensions_assessed():
    asset = make_asset(
        primitive="signature",
        material_type="certificate"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.3",
        hybrid=False,
    )

    assert result["confidence"] == "High"


def test_medium_confidence_when_three_dimensions_assessed():
    asset = make_asset(
        primitive="pke",
        material_type="private-key"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.2",
        hybrid=False,
    )

    assert result["d4"] is None
    assert result["confidence"] == "Medium"


def test_low_confidence_when_two_dimensions_assessed():
    asset = make_asset(
        primitive="pke",
        material_type="private-key"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version=None,
        hybrid=False,
    )

    assert result["d1"] == 2
    assert result["d2"] == 4
    assert result["d3"] is None
    assert result["d4"] is None

    assert result["confidence"] == "Low"


def test_hybrid_protocol_returns_level_4():
    asset = make_asset(
        primitive="kem",
        material_type="private-key"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.3",
        hybrid=True,
    )

    assert result["d1"] == 3
    assert result["d2"] == 4
    assert result["d3"] == 4
    assert result["d4"] == 3

    assert result["maturity"] == 3
    assert result["confidence"] == "High"

    assert result["binding_constraints"] == [
        "Migration Coordination Complexity",
        "Persistent Crypto Material Evidence",
    ]


def test_single_dimension_still_becomes_binding_constraint():
    asset = make_asset(
        primitive="pke",
        material_type="private-key"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=0,
        tls_version=None,
        hybrid=False,
    )

    assert result["maturity"] == 2

    assert result["binding_constraints"] == [
        "Migration Coordination Complexity"
    ]


def test_all_dimensions_missing_returns_not_assessed():
    asset = make_asset(
        primitive=None,
        material_type="private-key"
    )

    result = calculate_maturity(
        asset=asset,
        oid_location_count=0,
        tls_version=None,
        hybrid=False,
    )

    assert result == {
        "status": "Not Assessed"
    }