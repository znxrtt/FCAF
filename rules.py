
from datetime import date
# ── Payment context weights ────────────────────────────────────────────────────
# Informed by PCI-DSS v4.0.1 Requirement 4 scope classification.
# Higher weight = greater HNDL exposure risk.

PAYMENT_WEIGHTS = {
    "Payment Gateway":    1.0,
    "PKI Infrastructure": 0.8,
    "Open Banking API":   0.7,
    "VPN Infrastructure": 0.6,
    "Internal Services":  0.3,
}


def get_payment_weight(component):
    return PAYMENT_WEIGHTS.get(component, 0.3)


# ── Maturity level labels ──────────────────────────────────────────────────────

LEVEL_LABELS = {
    1: "Rigid",
    2: "Constrained",
    3: "Adaptable",
    4: "Agile",
}


def level_label(level):
    return LEVEL_LABELS.get(level, "Unknown")


# ── D1: Migration Coordination Complexity ─────────────────────────────────────
# Evidence: algorithmProperties.primitive
#
# Measures how many discrete parties must coordinate
# to complete a successful cryptographic migration.
#
# Level 1  signature   signer + all verifiers must upgrade together
# Level 2  pke         sender + receiver must upgrade together
# Level 3  kem /       pairwise but standardized for protocol negotiation
#          keyagreement
# Level 4  hash / mac  coordination is strictly internal to the service
#          / kdf

def coordination_score(primitive):
    mapping = {
        "signature":    1,
        "pke":          2,
        "kem":          3,
        "keyagreement": 3,
        "hash":         4,
        "mac":          4,
        "kdf":          4,
    }
    return mapping.get(primitive, None)


# ── D2: Implementation Pervasiveness ──────────────────────────────────────────
# Evidence: evidence.occurrences.location, algorithmProperties.oid
#
# Measures how scattered a specific algorithm OID is
# across the codebase. Proxy for cryptographic modularity.
# Note: CycloneDX dependencies arrays are NOT used here.
#
# Level 1  OID in 5+ distinct file locations
# Level 2  OID in 3-5 distinct file locations
# Level 3  OID in 2 distinct file locations
# Level 4  OID in 1 file location (highly localised)

def pervasiveness_score(location_count):
    if not location_count:
        return None

    if location_count >= 5:
        return 1

    if location_count >= 3:
        return 2

    if location_count == 2:
        return 3

    return 4


# ── D3: Protocol Agility ───────────────────────────────────────────────────────
# Evidence: CryptoLyzer output
#
# Measures the endpoint's ability to negotiate algorithms
# dynamically. Supported by RFC 7696 and CAMM R22/R23/R24.
#
# Level 1  TLS 1.0 or TLS 1.1
# Level 2  TLS 1.2
# Level 3  TLS 1.3, no PQC or hybrid capability detected
# Level 4  PQC-capable or hybrid key exchange detected

def protocol_score(
    tls_version,
    hybrid=False
):

    if tls_version is None:
        return None

    if hybrid:
        return 4

    if tls_version == "TLS1.3":
        return 3

    if tls_version == "TLS1.2":
        return 2

    if tls_version in [
        "TLS1.0",
        "TLS1.1"
    ]:
        return 1

    return None


# ── D4: Persistent Crypto Material Evidence ───────────────────────────────────
# Evidence: relatedCryptoMaterialProperties.type,
#           algorithmProperties.primitive
#
# Measures the presence of long-lived cryptographic material
# that binds the system to legacy lifecycles.
#
# Level 1  type=certificate         (long-lived PKI artifact)
# Level 2  type=private-key +       (identity key)
#          primitive=signature
# Level 3  type=private-key +       (session key, more manageable)
#          primitive=keyagreement
# Level 4  No crypto material       (absence of detected persisted
#          reported in CBOM          material — does not prove ephemerality)

def material_score(
    material_type,
    primitive
):
    if material_type is None:
        return 4

    if material_type == "certificate":
        return 1

    if (
        material_type == "private-key"
        and primitive == "signature"
    ):
        return 2

    if (
        material_type == "private-key"
        and primitive in [
            "kem",
            "keyagreement",
        ]
    ):
        return 3

    # Material exists, but the current rubric does not
    # define this material/primitive combination.
    return None


# ── Assessment confidence ──────────────────────────────────────────────────────
# Based on how many dimensions could be scored from evidence.
# Does NOT affect the numerical maturity score.
#
# High    4 dimensions assessed
# Medium  3 dimensions assessed
# Low     2 or fewer dimensions assessed

def confidence(assessed_count):
    if assessed_count >= 4:
        return "High"
    if assessed_count == 3:
        return "Medium"
    return "Low"


# ── Algorithm risk ─────────────────────────────────────────────────────────────
# Used in Priority Score calculation.
# SHA1/MD5 = 4 (High), RSA/ECDH = 3 (Medium), else = 2 (Low)

def algorithm_risk(algorithm):
    normalized_algorithm = (
        (algorithm or "")
        .upper()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )

    if (
        "SHA1" in normalized_algorithm
        or "MD5" in normalized_algorithm
    ):
        return 4

    if "RSA" in normalized_algorithm:
        return 3

    if (
        "ECDH" in normalized_algorithm
        or "ECDSA" in normalized_algorithm
    ):
        return 3

    return 2


# ── Priority score ─────────────────────────────────────────────────────────────
# Priority Score = Algorithm Risk x Payment Weight x (5 - Maturity Level)
# Higher score = address first.

def calculate_priority(risk, weight, maturity):
    return round(risk * weight * (5 - maturity), 2)


# ── Mosca adjusted migration time ─────────────────────────────────────────────
# Heuristic prototype — not empirically validated.
# adjusted_X = base_X x (1 + (4 - L) / 4)
# where L = component maturity level



def adjusted_migration_time(
    base_years,
    maturity_level
):
    """
    Applies the prototype maturity-based overhead factor
    to the estimated base migration duration.
    """

    factor = (
        1 +
        (4 - maturity_level) / 4
    )

    return round(
        base_years * factor,
        2
    )


def mosca_deadline(
    crqc_year,
    adjusted_x
):
    """
    Returns the latest calendar year by which migration
    should be completed.
    """

    return round(
        crqc_year - adjusted_x,
        2
    )


def mosca_urgent(
    data_retention_years,
    adjusted_x,
    crqc_year,
    assessment_year=None
):
    """
    Evaluates the Mosca inequality:

        X + Y > Z

    X = adjusted migration duration
    Y = data confidentiality/retention duration
    Z = remaining years until the assumed CRQC year
    """

    if assessment_year is None:
        assessment_year = date.today().year

    years_until_crqc = (
        crqc_year - assessment_year
    )

    if years_until_crqc <= 0:
        return True

    return (
        adjusted_x +
        data_retention_years
    ) > years_until_crqc

