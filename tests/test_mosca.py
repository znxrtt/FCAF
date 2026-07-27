from rules import (
    adjusted_migration_time,
    mosca_deadline,
    mosca_urgent,
)


# Maturity-adjusted migration time

def test_level_1_migration_multiplier():
    result = adjusted_migration_time(
        base_years=4,
        maturity_level=1
    )

    # 4 × 1.75 = 7
    assert result == 7.0


def test_level_2_migration_multiplier():
    result = adjusted_migration_time(
        base_years=4,
        maturity_level=2
    )

    # 4 × 1.50 = 6
    assert result == 6.0


def test_level_3_migration_multiplier():
    result = adjusted_migration_time(
        base_years=4,
        maturity_level=3
    )

    # 4 × 1.25 = 5
    assert result == 5.0


def test_level_4_migration_multiplier():
    result = adjusted_migration_time(
        base_years=4,
        maturity_level=4
    )

    # 4 × 1.00 = 4
    assert result == 4.0


def test_current_project_adjusted_migration_time():
    result = adjusted_migration_time(
        base_years=3,
        maturity_level=2
    )

    # Current project example:
    # 3 × 1.50 = 4.5
    assert result == 4.5


# Migration deadline

def test_mosca_deadline():
    result = mosca_deadline(
        crqc_year=2033,
        adjusted_x=4.5
    )

    assert result == 2028.5


def test_level_1_migration_deadline():
    adjusted_x = adjusted_migration_time(
        base_years=4,
        maturity_level=1
    )

    result = mosca_deadline(
        crqc_year=2033,
        adjusted_x=adjusted_x
    )

    assert result == 2026.0


# HNDL urgency

def test_mosca_urgent_case():
    result = mosca_urgent(
        data_retention_years=7,
        adjusted_x=4.5,
        crqc_year=2033,
        assessment_year=2026
    )

    # Years until CRQC = 7
    # X + Y = 4.5 + 7 = 11.5
    # 11.5 > 7, therefore urgent
    assert result is True


def test_mosca_non_urgent_case():
    result = mosca_urgent(
        data_retention_years=1,
        adjusted_x=2,
        crqc_year=2035,
        assessment_year=2026
    )

    # Years until CRQC = 9
    # X + Y = 2 + 1 = 3
    # 3 is not greater than 9
    assert result is False


def test_mosca_exact_boundary_is_not_urgent():
    result = mosca_urgent(
        data_retention_years=3,
        adjusted_x=4,
        crqc_year=2033,
        assessment_year=2026
    )

    # Years until CRQC = 7
    # X + Y = 7
    # Formula uses greater-than, not greater-than-or-equal
    assert result is False


def test_crqc_year_already_reached_is_urgent():
    result = mosca_urgent(
        data_retention_years=1,
        adjusted_x=1,
        crqc_year=2026,
        assessment_year=2026
    )

    assert result is True


def test_crqc_year_already_passed_is_urgent():
    result = mosca_urgent(
        data_retention_years=1,
        adjusted_x=1,
        crqc_year=2025,
        assessment_year=2026
    )

    assert result is True