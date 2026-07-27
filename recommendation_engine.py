RECOMMENDATIONS = {
    "Migration Coordination Complexity": {
        1: (
            "Define a coordinated migration plan for the signer "
            "and all dependent verifiers."
        ),
        2: (
            "Evaluate migration from public-key encryption "
            "to a standardized KEM-based construction, with "
            "a coordinated transition plan for both participants."
        ),
        3: (
            "Validate protocol compatibility and prepare for "
            "hybrid or PQC key establishment."
        ),
    },

    "Implementation Pervasiveness": {
        1: (
            "Centralize cryptographic operations behind a shared "
            "service or module."
        ),
        2: (
            "Reduce duplicated algorithm usage across source files."
        ),
        3: (
            "Consolidate the remaining algorithm implementations "
            "into one location."
        ),
    },

    "Protocol Agility": {
        1: (
            "Upgrade the endpoint from legacy TLS to TLS 1.3 "
            "and enable secure algorithm negotiation."
        ),
        2: (
            "Upgrade the endpoint from TLS 1.2 to TLS 1.3."
        ),
        3: (
            "Evaluate and test hybrid or PQC-capable key exchange."
        ),
    },

    "Persistent Crypto Material Evidence": {
        1: (
            "Review certificate dependencies and implement a "
            "controlled certificate and key rotation plan."
        ),
        2: (
            "Improve identity-key rotation and coordinate updates "
            "with all signature verifiers."
        ),
        3: (
            "Validate that session keys are generated per session "
            "and are not stored as long-lived material."
        ),
    },
}


def get_recommendations(assessment):
    """
    Returns recommendations only for the dimensions that
    currently bind the component maturity level.

    Parameters
    ----------
    assessment : dict
        Result returned by calculate_maturity().

    Returns
    -------
    list of dict
        Recommendations for the binding constraints.
    """

    binding_constraints = assessment.get(
        "binding_constraints",
        []
    )

    dimension_scores = {
        "Migration Coordination Complexity":
            assessment.get("d1"),

        "Implementation Pervasiveness":
            assessment.get("d2"),

        "Protocol Agility":
            assessment.get("d3"),

        "Persistent Crypto Material Evidence":
            assessment.get("d4"),
    }

    recommendations = []

    for dimension in binding_constraints:

        current_level = dimension_scores.get(
            dimension
        )

        recommendation = (
            RECOMMENDATIONS
            .get(dimension, {})
            .get(current_level)
        )

        if recommendation is None:
            continue

        recommendations.append({
            "dimension": dimension,
            "current_level": current_level,
            "target_level": min(
                current_level + 1,
                4
            ),
            "recommendation": recommendation,
        })

    return recommendations