from cryptolyzer_parser import (
    normalize_version,
    highest_tls_version,
    detect_hybrid,
    parse_cryptolyzer_output,
)


# Version normalization

def test_normalize_known_version():
    assert normalize_version("tls1_2") == "TLS1.2"


def test_normalize_unknown_version_returns_none():
    assert normalize_version("tls9_9") is None


def test_highest_tls_version_picks_max():
    result = highest_tls_version(
        ["tls1_0", "tls1_2", "tls1_1"]
    )

    assert result == "TLS1.2"


def test_highest_tls_version_empty_list_returns_none():
    assert highest_tls_version([]) is None


# Hybrid/PQC detection — must only read a scoped negotiated-group
# field, never the whole serialized document.

def test_hybrid_true_when_scoped_group_field_contains_marker():
    data = {
        "target": {"address": "localhost"},
        "versions": ["tls1_3"],
        "groups": ["x25519_kyber768"],
    }

    assert detect_hybrid(data) is True


def test_hybrid_false_when_no_group_field_present():
    # The raw CryptoLyzer "versions" probe alone provides no
    # negotiated-group evidence, so hybrid must be False rather
    # than guessed.
    data = {
        "target": {"scheme": "tls", "address": "localhost"},
        "versions": ["tls1_2"],
    }

    assert detect_hybrid(data) is False


def test_hybrid_false_positive_guard_hostname():
    # A hostname containing "pqc" or "hybrid" must NOT trigger a
    # hybrid finding — only a real negotiated-group field can.
    data = {
        "target": {
            "scheme": "tls",
            "address": "pqc-hybrid-test.example.com",
        },
        "versions": ["tls1_2"],
    }

    assert detect_hybrid(data) is False


def test_hybrid_false_positive_guard_unrelated_metadata():
    data = {
        "target": {"address": "localhost"},
        "versions": ["tls1_3"],
        "notes": "hybrid cloud deployment, PQC roadmap planned",
    }

    assert detect_hybrid(data) is False


def test_hybrid_true_when_curves_field_contains_marker():
    data = {
        "target": {"address": "localhost"},
        "versions": ["tls1_3"],
        "curves": ["secp256r1", "ml-kem-768"],
    }

    assert detect_hybrid(data) is True


# End-to-end parse_cryptolyzer_output

def test_parse_cryptolyzer_output_no_hybrid_evidence(tmp_path):
    raw_file = tmp_path / "raw.json"

    raw_file.write_text(
        (
            '{"target": {"scheme": "tls", "address": "localhost", '
            '"ip": "127.0.0.1", "port": 8443}, '
            '"versions": ["tls1_2"]}'
        ),
        encoding="utf-8",
    )

    evidence = parse_cryptolyzer_output(
        str(raw_file),
        component_name="PKI Infrastructure",
    )

    assert evidence["tls_version"] == "TLS1.2"
    assert evidence["hybrid"] is False
    assert evidence["assessed"] is True
