from rules import (
    calculate_priority,
    adjusted_migration_time,
)

from maturity_engine import (
    calculate_maturity,
)


def make_rsa_asset():
    return {
        "name": "RSA-2048",
        "primitive": "pke",
        "material_type": "private-key",
        "oid": "1.2.840.113549.1.1.1",
        "locations": [
            "payment_simulation/pki/"
            "certificate_manager.py"
        ],
    }


# Payment-weight sensitivity

def test_payment_weight_does_not_change_maturity():
    asset = make_rsa_asset()

    assessment_before = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.2",
        hybrid=False,
    )

    assessment_after = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.2",
        hybrid=False,
    )

    low_weight = 0.7
    high_weight = 0.9

    low_priority = calculate_priority(
        risk=3,
        weight=low_weight,
        maturity=assessment_before["maturity"],
    )

    high_priority = calculate_priority(
        risk=3,
        weight=high_weight,
        maturity=assessment_after["maturity"],
    )

    assert assessment_before["maturity"] == 2
    assert assessment_after["maturity"] == 2
    assert high_priority > low_priority


def test_increasing_payment_weight_increases_priority():
    low_weight_priority = calculate_priority(
        risk=3,
        weight=0.3,
        maturity=2,
    )

    medium_weight_priority = calculate_priority(
        risk=3,
        weight=0.6,
        maturity=2,
    )

    high_weight_priority = calculate_priority(
        risk=3,
        weight=1.0,
        maturity=2,
    )

    assert low_weight_priority == 2.7
    assert medium_weight_priority == 5.4
    assert high_weight_priority == 9.0

    assert (
        low_weight_priority
        < medium_weight_priority
        < high_weight_priority
    )


def test_decreasing_payment_weight_decreases_priority():
    original_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=2,
    )

    reduced_priority = calculate_priority(
        risk=3,
        weight=0.7,
        maturity=2,
    )

    assert original_priority == 7.2
    assert reduced_priority == 6.3
    assert reduced_priority < original_priority


def test_zero_payment_weight_produces_zero_priority():
    priority = calculate_priority(
        risk=4,
        weight=0.0,
        maturity=1,
    )

    assert priority == 0.0


# Algorithm-risk sensitivity

def test_increasing_algorithm_risk_increases_priority():
    low_risk_priority = calculate_priority(
        risk=2,
        weight=0.8,
        maturity=2,
    )

    medium_risk_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=2,
    )

    high_risk_priority = calculate_priority(
        risk=4,
        weight=0.8,
        maturity=2,
    )

    assert low_risk_priority == 4.8
    assert medium_risk_priority == 7.2
    assert high_risk_priority == 9.6

    assert (
        low_risk_priority
        < medium_risk_priority
        < high_risk_priority
    )


def test_algorithm_risk_does_not_change_maturity():
    asset = make_rsa_asset()

    assessment = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.2",
        hybrid=False,
    )

    priorities = [
        calculate_priority(
            risk=risk,
            weight=0.8,
            maturity=assessment["maturity"],
        )
        for risk in [2, 3, 4]
    ]

    assert assessment["maturity"] == 2
    assert priorities == [4.8, 7.2, 9.6]


# Maturity sensitivity

def test_increasing_maturity_decreases_priority():
    level_1_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=1,
    )

    level_2_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=2,
    )

    level_3_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=3,
    )

    level_4_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=4,
    )

    assert level_1_priority == 9.6
    assert level_2_priority == 7.2
    assert level_3_priority == 4.8
    assert level_4_priority == 2.4

    assert (
        level_1_priority
        > level_2_priority
        > level_3_priority
        > level_4_priority
    )


def test_one_level_maturity_improvement_reduces_priority():
    current_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=2,
    )

    projected_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=3,
    )

    assert current_priority == 7.2
    assert projected_priority == 4.8
    assert projected_priority < current_priority


# Ranking sensitivity

def test_priority_ranking_orders_highest_score_first():
    assets = [
        {
            "name": "Internal AES",
            "priority": calculate_priority(
                risk=2,
                weight=0.3,
                maturity=4,
            ),
        },
        {
            "name": "PKI RSA",
            "priority": calculate_priority(
                risk=3,
                weight=0.8,
                maturity=2,
            ),
        },
        {
            "name": "Gateway SHA1",
            "priority": calculate_priority(
                risk=4,
                weight=1.0,
                maturity=1,
            ),
        },
    ]

    ranked_assets = sorted(
        assets,
        key=lambda item: item["priority"],
        reverse=True,
    )

    assert ranked_assets[0]["name"] == "Gateway SHA1"
    assert ranked_assets[1]["name"] == "PKI RSA"
    assert ranked_assets[2]["name"] == "Internal AES"


def test_payment_weight_can_change_backlog_order():
    low_weight_asset = calculate_priority(
        risk=4,
        weight=0.3,
        maturity=2,
    )

    high_weight_asset = calculate_priority(
        risk=3,
        weight=1.0,
        maturity=2,
    )

    assert low_weight_asset == 3.6
    assert high_weight_asset == 9.0
    assert high_weight_asset > low_weight_asset


# Mosca sensitivity

def test_lower_maturity_increases_adjusted_migration_time():
    level_1_time = adjusted_migration_time(
        base_years=4,
        maturity_level=1,
    )

    level_2_time = adjusted_migration_time(
        base_years=4,
        maturity_level=2,
    )

    level_3_time = adjusted_migration_time(
        base_years=4,
        maturity_level=3,
    )

    level_4_time = adjusted_migration_time(
        base_years=4,
        maturity_level=4,
    )

    assert level_1_time == 7.0
    assert level_2_time == 6.0
    assert level_3_time == 5.0
    assert level_4_time == 4.0

    assert (
        level_1_time
        > level_2_time
        > level_3_time
        > level_4_time
    )


def test_base_migration_time_does_not_change_maturity():
    asset = make_rsa_asset()

    assessment = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.2",
        hybrid=False,
    )

    short_migration = adjusted_migration_time(
        base_years=2,
        maturity_level=assessment["maturity"],
    )

    long_migration = adjusted_migration_time(
        base_years=5,
        maturity_level=assessment["maturity"],
    )

    assert assessment["maturity"] == 2
    assert short_migration == 3.0
    assert long_migration == 7.5


# Confidence separation

def test_confidence_is_not_part_of_priority_formula():
    high_confidence_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=2,
    )

    low_confidence_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=2,
    )

    assert (
        high_confidence_priority
        == low_confidence_priority
    )

    assert high_confidence_priority == 7.2


# Current project baseline

def test_current_project_sensitivity_baseline():
    asset = make_rsa_asset()

    assessment = calculate_maturity(
        asset=asset,
        oid_location_count=1,
        tls_version="TLS1.2",
        hybrid=False,
    )

    baseline_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=assessment["maturity"],
    )

    higher_weight_priority = calculate_priority(
        risk=3,
        weight=0.9,
        maturity=assessment["maturity"],
    )

    improved_maturity_priority = calculate_priority(
        risk=3,
        weight=0.8,
        maturity=3,
    )

    assert assessment["maturity"] == 2
    assert baseline_priority == 7.2
    assert higher_weight_priority == 8.1
    assert improved_maturity_priority == 4.8