DIMENSION_KEYS = {
    "Migration Coordination Complexity": "d1",
    "Implementation Pervasiveness": "d2",
    "Protocol Agility": "d3",
    "Persistent Crypto Material Evidence": "d4",
}


def calculate_current_maturity(scores):
    """
    Returns the minimum of assessed dimension scores.

    None represents Not Assessed and is excluded.
    """

    assessed_scores = [
        score
        for score in scores.values()
        if score is not None
    ]

    if not assessed_scores:
        return None

    return min(assessed_scores)


def find_binding_constraints(scores):
    """
    Returns all assessed dimensions equal to the current
    minimum maturity level.
    """

    maturity = calculate_current_maturity(
        scores
    )

    if maturity is None:
        return []

    return [
        dimension_name
        for dimension_name, dimension_key
        in DIMENSION_KEYS.items()
        if scores.get(dimension_key) == maturity
    ]


def build_impact_chain(
    assessment,
    recommendations
):
    """
    Simulates the effect of applying the generated
    recommendations sequentially.

    The function does not modify the original assessment.

    Parameters
    ----------
    assessment : dict
        Output from calculate_maturity().

    recommendations : list
        Output from get_recommendations().

    Returns
    -------
    dict
        Current state, remediation steps and final state.
    """

    scores = {
        "d1": assessment.get("d1"),
        "d2": assessment.get("d2"),
        "d3": assessment.get("d3"),
        "d4": assessment.get("d4"),
    }

    initial_scores = scores.copy()

    initial_maturity = calculate_current_maturity(
        scores
    )

    steps = []

    for step_number, recommendation in enumerate(
        recommendations,
        start=1
    ):
        dimension_name = recommendation.get(
            "dimension"
        )

        dimension_key = DIMENSION_KEYS.get(
            dimension_name
        )

        if dimension_key is None:
            continue

        current_level = scores.get(
            dimension_key
        )

        target_level = recommendation.get(
            "target_level"
        )

        if (
            current_level is None
            or target_level is None
            or target_level <= current_level
        ):
            continue

        maturity_before = calculate_current_maturity(
            scores
        )

        scores[dimension_key] = target_level

        maturity_after = calculate_current_maturity(
            scores
        )

        remaining_constraints = (
            find_binding_constraints(
                scores
            )
        )

        steps.append({
            "step": step_number,
            "dimension": dimension_name,
            "dimension_key": dimension_key,
            "from_level": current_level,
            "to_level": target_level,
            "maturity_before": maturity_before,
            "maturity_after": maturity_after,
            "maturity_changed": (
                maturity_after != maturity_before
            ),
            "remaining_binding_constraints":
                remaining_constraints,
            "recommendation":
                recommendation.get(
                    "recommendation"
                ),
        })

    final_maturity = calculate_current_maturity(
        scores
    )

    return {
        "initial_scores": initial_scores,
        "initial_maturity": initial_maturity,
        "initial_binding_constraints":
            find_binding_constraints(
                initial_scores
            ),
        "steps": steps,
        "final_scores": scores.copy(),
        "final_maturity": final_maturity,
        "final_binding_constraints":
            find_binding_constraints(
                scores
            ),
        "maturity_improvement": (
            final_maturity - initial_maturity
            if (
                final_maturity is not None
                and initial_maturity is not None
            )
            else None
        ),
    }