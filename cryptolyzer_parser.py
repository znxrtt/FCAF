import json


VERSION_MAP = {
    "ssl2": "SSL2.0",
    "ssl3": "SSL3.0",
    "tls1": "TLS1.0",
    "tls1_0": "TLS1.0",
    "tls1_1": "TLS1.1",
    "tls1_2": "TLS1.2",
    "tls1_3": "TLS1.3",
}


HYBRID_MARKERS = (
    "kyber",
    "mlkem",
    "ml-kem",
    "x25519kyber",
    "hybrid",
    "pqc",
)

# CryptoLyzer's TLS "versions" analyzer (the only analyzer reflected
# in the current raw fixture format) reports which protocol versions
# an endpoint accepts. It does NOT report negotiated key-exchange
# groups, so it can never provide hybrid/PQC evidence on its own.
#
# Hybrid/PQC capability can only be established from CryptoLyzer's
# curve/group analyzer output (e.g. `cryptolyzer.tls.curves`), which
# reports the negotiated or supported key-exchange group names (for
# example "x25519_kyber768"). If a scan did not run that analyzer,
# none of these fields will be present, and hybrid must be reported
# as False rather than guessed from unrelated text.
HYBRID_EVIDENCE_FIELDS = (
    "groups",
    "curves",
    "key_exchange_groups",
    "negotiated_group",
)


def load_cryptolyzer_output(file_path):
    """
    Loads CryptoLyzer JSON exported by PowerShell.

    PowerShell may save redirected output as UTF-8,
    UTF-8 with BOM, or UTF-16 depending on the version
    and command used.
    """

    encodings = (
        "utf-8-sig",
        "utf-16",
    )

    last_error = None

    for encoding in encodings:
        try:
            with open(
                file_path,
                "r",
                encoding=encoding
            ) as file:
                return json.load(file)

        except UnicodeDecodeError as error:
            last_error = error

    raise ValueError(
        "Unable to decode CryptoLyzer JSON as UTF-8 "
        f"or UTF-16: {file_path}"
    ) from last_error


def normalize_version(version):
    if not version:
        return None

    normalized = (
        str(version)
        .lower()
        .replace("-", "_")
        .replace(".", "_")
    )

    return VERSION_MAP.get(normalized)


def detect_hybrid(data):
    """
    Detects hybrid/PQC key-exchange capability from a scoped
    negotiated-group/curve field only.

    Deliberately does NOT search the whole serialized document —
    doing so would false-positive on unrelated text such as a
    hostname or scheme value that happens to contain a marker
    word (e.g. "pqc-test.example.com"). If none of the expected
    group/curve fields are present, there is insufficient
    evidence to claim hybrid capability, so this returns False
    rather than guessing.
    """

    for field in HYBRID_EVIDENCE_FIELDS:
        value = data.get(field)

        if not value:
            continue

        serialized_value = json.dumps(
            value
        ).lower()

        if any(
            marker in serialized_value
            for marker in HYBRID_MARKERS
        ):
            return True

    return False


def highest_tls_version(versions):
    normalized_versions = [
        normalize_version(version)
        for version in versions
    ]

    normalized_versions = [
        version
        for version in normalized_versions
        if version is not None
    ]

    version_rank = {
        "SSL2.0": 0,
        "SSL3.0": 0,
        "TLS1.0": 1,
        "TLS1.1": 1,
        "TLS1.2": 2,
        "TLS1.3": 3,
    }

    if not normalized_versions:
        return None

    return max(
        normalized_versions,
        key=lambda version: version_rank[version]
    )


def parse_cryptolyzer_output(
    file_path,
    component_name
):
    data = load_cryptolyzer_output(
        file_path
    )

    target = data.get(
        "target",
        {}
    )

    versions = data.get(
        "versions",
        []
    )

    tls_version = highest_tls_version(
        versions
    )

    hybrid = detect_hybrid(
        data
    )

    return {
        "component": component_name,
        "source": "cryptolyzer",
        "target": {
            "scheme": target.get("scheme"),
            "address": target.get("address"),
            "ip": target.get("ip"),
            "port": target.get("port"),
        },
        "detected_versions": versions,
        "tls_version": tls_version,
        "hybrid": hybrid,
        "assessed": (
            tls_version is not None
            or hybrid
        ),
    }


if __name__ == "__main__":

    input_file = "cryptolyzer_raw.json"
    output_file = "cryptolyzer_evidence.json"

    evidence = parse_cryptolyzer_output(
        file_path=input_file,
        component_name="PKI Infrastructure",
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            evidence,
            file,
            indent=2
        )

    print(
        json.dumps(
            evidence,
            indent=2
        )
    )

    print(
        f"\nGenerated: {output_file}"
    )
