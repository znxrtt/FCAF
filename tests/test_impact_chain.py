from impact_chain import (
    calculate_current_maturity,
    find_binding_constraints,
    build_impact_chain,
)

from recommendation_engine import (
    get_recommendations,
)


def test_calculate_current_maturity():
    scores = {
        "d1": 2,
        "d2": 4,
        "d3": 3,
        "d4": None,
    }

    assert calculate_current_maturity(
        scores
    ) == 2


def test_calculate_maturity_excludes_none():
    scores = {
        "d1": None,
        "d2": 4,
        "d3": None,
        "d4": 3,
    }

    assert calculate_current_maturity(
        scores
    ) == 3


def test_all_missing_scores_return_none():
    scores = {
        "d1": None,
        "d2": None,
        "d3": None,
        "d4": None,
    }

    assert calculate_current_maturity(
        scores
    ) is None


def test_find_single_binding_constraint():
    scores = {
        "d1": 2,
        "d2": 4,
        "d3": 3,
        "d4": None,
    }

    constraints = find_binding_constraints(
        scores
    )

    assert constraints == [
        "Migration Coordination Complexity"
    ]


def test_find_tied_binding_constraints():
    scores = {
        "d1": 2,
        "d2": 4,
        "d3": 2,
        "d4": None,
    }

    constraints = find_binding_constraints(
        scores
    )

    assert constraints == [
        "Migration Coordination Complexity",
        "Protocol Agility",
    ]


def test_current_project_impact_chain():
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

    result = build_impact_chain(
        assessment,
        recommendations
    )

    assert result["initial_maturity"] == 2
    assert result["final_maturity"] == 3
    assert result["maturity_improvement"] == 1
    assert len(result["steps"]) == 2


def test_first_remediation_does_not_immediately_raise_maturity():
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

    result = build_impact_chain(
        assessment,
        recommendations
    )

    first_step = result["steps"][0]

    assert first_step["from_level"] == 2
    assert first_step["to_level"] == 3
    assert first_step["maturity_before"] == 2
    assert first_step["maturity_after"] == 2
    assert first_step["maturity_changed"] is False

    assert first_step[
        "remaining_binding_constraints"
    ] == [
        "Protocol Agility"
    ]


def test_second_remediation_raises_maturity():
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

    result = build_impact_chain(
        assessment,
        recommendations
    )

    second_step = result["steps"][1]

    assert second_step["maturity_before"] == 2
    assert second_step["maturity_after"] == 3
    assert second_step["maturity_changed"] is True


def test_final_scores_are_correct():
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

    result = build_impact_chain(
        assessment,
        recommendations
    )

    assert result["final_scores"] == {
        "d1": 3,
        "d2": 4,
        "d3": 3,
        "d4": None,
    }


def test_empty_recommendations_do_not_change_maturity():
    assessment = {
        "d1": 3,
        "d2": 4,
        "d3": 3,
        "d4": None,
        "maturity": 3,
        "binding_constraints": [],
    }

    result = build_impact_chain(
        assessment,
        []
    )

    assert result["steps"] == []
    assert result["initial_maturity"] == 3
    assert result["final_maturity"] == 3
    assert result["maturity_improvement"] == 0


def test_impact_chain_does_not_modify_original_assessment():
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

    original_scores = {
        "d1": assessment["d1"],
        "d2": assessment["d2"],
        "d3": assessment["d3"],
        "d4": assessment["d4"],
    }

    recommendations = get_recommendations(
        assessment
    )

    build_impact_chain(
        assessment,
        recommendations
    )

    assert assessment["d1"] == original_scores["d1"]
    assert assessment["d2"] == original_scores["d2"]
    assert assessment["d3"] == original_scores["d3"]
    assert assessment["d4"] == original_scores["d4"]