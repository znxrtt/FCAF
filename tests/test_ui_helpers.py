import json

import pytest

from ui_helpers import (
    escape,
    escape_join,
    compact_html,
    badge,
    metric_card,
    display_score,
    validate_uploaded_json,
    EvidenceValidationError,
    MAX_UPLOAD_BYTES,
    load_validation_summary,
)


# ── HTML escaping ────────────────────────────────────────────────────────

def test_escape_none_returns_empty_string():
    assert escape(None) == ""


def test_escape_neutralizes_script_tags():
    result = escape("<script>alert(1)</script>")

    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_escape_neutralizes_attribute_breakout():
    result = escape('"><img src=x onerror=alert(1)>')

    assert "<img" not in result
    assert "&quot;" in result
    assert "&gt;" in result


def test_escape_handles_non_string_values():
    assert escape(42) == "42"
    assert escape(3.5) == "3.5"


def test_escape_join_escapes_every_item():
    result = escape_join(["<b>a</b>", "plain"])

    assert "&lt;b&gt;" in result
    assert "plain" in result


def test_badge_escapes_label():
    result = badge("<b>evil</b>", "measured")

    assert "<b>" not in result
    assert "badge-measured" in result


def test_metric_card_escapes_all_fields():
    result = metric_card(
        "<script>x</script>",
        "<img src=x>",
        "<svg onload=alert(1)>",
        "cyan",
    )

    assert "<script>" not in result
    assert "<img" not in result
    assert "<svg" not in result
    assert "accent-cyan" in result


# ── Text-spacing preservation (line-join defect fix) ────────────────────

def test_compact_html_preserves_word_spacing_across_lines():
    content = """
        <div class="panel-copy">
            CryptoLyzer evidence applied only
            when the component matches.
        </div>
    """

    result = compact_html(content)

    assert "onlywhen" not in result
    assert "only when" in result


def test_compact_html_collapses_to_single_line():
    content = """
        <div>
            first
            second
        </div>
    """

    result = compact_html(content)

    assert "\n" not in result


def test_compact_html_does_not_add_space_between_tags():
    content = """
        <div class="a">
            <span>text</span>
        </div>
    """

    result = compact_html(content)

    assert "<div class=\"a\"> <span>" in result


# ── Not Assessed display ─────────────────────────────────────────────────

def test_display_score_none_shows_not_assessed():
    assert display_score(None) == "Not Assessed"


def test_display_score_passes_through_value():
    assert display_score(3) == 3


# ── Upload validation ────────────────────────────────────────────────────

class _FakeUploadedFile:
    def __init__(self, name, content_bytes):
        self.name = name
        self._content_bytes = content_bytes

    def getvalue(self):
        return self._content_bytes


def test_validate_uploaded_json_accepts_valid_object():
    upload = _FakeUploadedFile(
        "cbom.json",
        json.dumps({"bomFormat": "CycloneDX"}).encode("utf-8"),
    )

    data = validate_uploaded_json(upload)

    assert data == {"bomFormat": "CycloneDX"}


def test_validate_uploaded_json_rejects_malformed_json():
    upload = _FakeUploadedFile(
        "broken.json",
        b"{not valid json",
    )

    with pytest.raises(EvidenceValidationError):
        validate_uploaded_json(upload)


def test_validate_uploaded_json_rejects_non_object_top_level():
    upload = _FakeUploadedFile(
        "array.json",
        b"[1, 2, 3]",
    )

    with pytest.raises(EvidenceValidationError):
        validate_uploaded_json(upload)


def test_validate_uploaded_json_rejects_oversized_file():
    upload = _FakeUploadedFile(
        "big.json",
        b"{}",
    )

    with pytest.raises(EvidenceValidationError):
        validate_uploaded_json(upload, max_bytes=1)


def test_validate_uploaded_json_rejects_excessive_nesting():
    nested = {}
    cursor = nested

    for _ in range(50):
        cursor["next"] = {}
        cursor = cursor["next"]

    upload = _FakeUploadedFile(
        "deep.json",
        json.dumps(nested).encode("utf-8"),
    )

    with pytest.raises(EvidenceValidationError):
        validate_uploaded_json(upload, max_depth=10)


def test_validate_uploaded_json_rejects_missing_required_keys():
    upload = _FakeUploadedFile(
        "mapping.json",
        json.dumps({"pki": "PKI Infrastructure"}).encode("utf-8"),
    )

    with pytest.raises(EvidenceValidationError):
        validate_uploaded_json(
            upload,
            required_keys=["bomFormat"],
        )


def test_validate_uploaded_json_decodes_utf16(tmp_path):
    payload = json.dumps({"bomFormat": "CycloneDX"})

    upload = _FakeUploadedFile(
        "utf16.json",
        payload.encode("utf-16"),
    )

    data = validate_uploaded_json(upload)

    assert data == {"bomFormat": "CycloneDX"}


def test_max_upload_bytes_is_a_reasonable_positive_limit():
    assert 0 < MAX_UPLOAD_BYTES <= 50 * 1024 * 1024


# ── Validation summary loading ──────────────────────────────────────────

def test_load_validation_summary_missing_file_returns_none(tmp_path):
    result = load_validation_summary(
        str(tmp_path / "does_not_exist.json")
    )

    assert result is None


def test_load_validation_summary_malformed_json_returns_none(tmp_path):
    path = tmp_path / "validation_summary.json"
    path.write_text("{not valid json", encoding="utf-8")

    assert load_validation_summary(str(path)) is None


def test_load_validation_summary_missing_required_key_returns_none(
    tmp_path
):
    path = tmp_path / "validation_summary.json"

    path.write_text(
        json.dumps({"total_tests": 175}),
        encoding="utf-8",
    )

    assert load_validation_summary(str(path)) is None


def test_load_validation_summary_valid_file_is_returned(tmp_path):
    path = tmp_path / "validation_summary.json"

    summary = {
        "generated_at": "2026-07-17T00:00:00+00:00",
        "total_tests": 175,
        "passed": 175,
        "failed": 0,
        "duration_seconds": 0.5,
        "category_counts": {"tests/test_rules.py": {"passed": 31}},
    }

    path.write_text(json.dumps(summary), encoding="utf-8")

    result = load_validation_summary(str(path))

    assert result == summary
