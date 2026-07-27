from recommendation_engine import (
    get_recommendations,
)


def test_single_binding_constraint_recommendation():
    assessment = {
        "d1": 2,
        "d2": 4,
        "d3": 3,
        "d4": None,
        "maturity": 2,
        "binding_constraints": [
            "Migration Coordination Complexity"
        ],
    }

    recommendations = get_recommendations(
        assessment
    )

    assert len(recommendations) == 1

    recommendation = recommendations[0]

    assert (
        recommendation["dimension"]
        == "Migration Coordination Complexity"
    )

    assert recommendation["current_level"] == 2
    assert recommendation["target_level"] == 3

    assert (
        "KEM-based construction"
        in recommendation["recommendation"]
    )


def test_tied_binding_constraints_generate_multiple_recommendations():
    assessment = {
        "d1": 2,
        "d2": 4,
        "d3": 2,
        "d4": None,
        "maturity": 2,
        "binding_constraints": [
            "Migration Coordination Complexity",
            "Protocol Agility",
        ],
    }

    recommendations = get_recommendations(
        assessment
    )

    assert len(recommendations) == 2

    dimensions = [
        recommendation["dimension"]
        for recommendation in recommendations
    ]

    assert (
        "Migration Coordination Complexity"
        in dimensions
    )

    assert "Protocol Agility" in dimensions


def test_protocol_level_2_recommendation():
    assessment = {
        "d1": 3,
        "d2": 4,
        "d3": 2,
        "d4": None,
        "maturity": 2,
        "binding_constraints": [
            "Protocol Agility"
        ],
    }

    recommendations = get_recommendations(
        assessment
    )

    recommendation = recommendations[0]

    assert recommendation["current_level"] == 2
    assert recommendation["target_level"] == 3

    assert (
        recommendation["recommendation"]
        == "Upgrade the endpoint from TLS 1.2 to TLS 1.3."
    )


def test_pervasiveness_level_1_recommendation():
    assessment = {
        "d1": 3,
        "d2": 1,
        "d3": 3,
        "d4": None,
        "maturity": 1,
        "binding_constraints": [
            "Implementation Pervasiveness"
        ],
    }

    recommendations = get_recommendations(
        assessment
    )

    recommendation = recommendations[0]

    assert (
        recommendation["dimension"]
        == "Implementation Pervasiveness"
    )

    assert recommendation["current_level"] == 1
    assert recommendation["target_level"] == 2

    assert (
        "Centralize cryptographic operations"
        in recommendation["recommendation"]
    )


def test_certificate_recommendation():
    assessment = {
        "d1": 3,
        "d2": 4,
        "d3": 3,
        "d4": 1,
        "maturity": 1,
        "binding_constraints": [
            "Persistent Crypto Material Evidence"
        ],
    }

    recommendations = get_recommendations(
        assessment
    )

    recommendation = recommendations[0]

    assert recommendation["current_level"] == 1
    assert recommendation["target_level"] == 2

    assert (
        "certificate"
        in recommendation["recommendation"].lower()
    )


def test_no_binding_constraints_returns_empty_list():
    assessment = {
        "d1": 4,
        "d2": 4,
        "d3": 4,
        "d4": 4,
        "maturity": 4,
        "binding_constraints": [],
    }

    recommendations = get_recommendations(
        assessment
    )

    assert recommendations == []


def test_level_4_constraint_does_not_generate_recommendation():
    assessment = {
        "d1": 4,
        "d2": 4,
        "d3": 4,
        "d4": 4,
        "maturity": 4,
        "binding_constraints": [
            "Protocol Agility"
        ],
    }

    recommendations = get_recommendations(
        assessment
    )

    assert recommendations == []


def test_unknown_dimension_is_ignored():
    assessment = {
        "d1": 2,
        "d2": 4,
        "d3": 3,
        "d4": None,
        "maturity": 2,
        "binding_constraints": [
            "Unknown Dimension"
        ],
    }

    recommendations = get_recommendations(
        assessment
    )

    assert recommendations == []


def test_recommendation_does_not_modify_assessment():
    assessment = {
        "d1": 2,
        "d2": 4,
        "d3": 2,
        "d4": None,
        "maturity": 2,
        "binding_constraints": [
            "Migration Coordination Complexity",
            "Protocol Agility",
        ],
    }

    original_assessment = assessment.copy()

    get_recommendations(
        assessment
    )

    assert assessment == original_assessment
