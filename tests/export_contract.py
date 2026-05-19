"""Contract tests for export-markup v1.0 (issue #146)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.exporters.contract import (
    EXPORT_SCHEMA_VERSION,
    ExportDocument,
    ExportMetadata,
    ExportRow,
)


def _uuid4_hex() -> str:
    return uuid.uuid4().hex


def _valid_row(**overrides):
    row = {
        "requirement_id": "REQ-001",
        "requirement_text": "Кириллица | pipe\n*markdown* 😀",
        "Ref": {
            "type": "table_cell_list",
            "source_file": "sample_tz.xlsx",
            "table_index": 0,
            "row": 2,
            "col": 3,
            "list_path": ["1", "2.1"],
        },
        "status": "Да",
        "comment": "",
        "confidence": 0.91,
        "run_id": _uuid4_hex(),
        "additional_columns": {"provider": "stub"},
    }
    row.update(overrides)
    return row


def test_export_row_round_trip_preserves_required_and_additional_fields():
    source = _valid_row(
        requirement_text="A" * 1200,
        comment="Комментарий с |, newline\nи *звёздочками* 😀",
    )

    row = ExportRow(**source)

    assert row.to_contract_dict() == source


def test_export_row_accepts_empty_text_and_comment_without_normalising():
    source = _valid_row(requirement_text="", comment="")

    row = ExportRow(**source)

    assert row.to_contract_dict()["requirement_text"] == ""
    assert row.to_contract_dict()["comment"] == ""


@pytest.mark.parametrize("status", ["maybe", "OK", "", None])
def test_export_row_rejects_status_outside_mvp_enum(status):
    with pytest.raises(ValidationError):
        ExportRow(**_valid_row(status=status))


@pytest.mark.parametrize(
    "ref",
    [
        {},
        {"type": "paragraph", "source_file": "sample.docx"},
        {"type": "list_item", "source_file": "sample.docx", "list_path": []},
        {"type": "table_cell_list", "source_file": "sample.xlsx"},
        {"type": "table_cell_list", "source_file": "sample.xlsx", "list_path": []},
    ],
)
def test_export_row_rejects_empty_or_incomplete_ref_locator(ref):
    with pytest.raises(ValidationError):
        ExportRow(**_valid_row(Ref=ref))


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_export_row_rejects_confidence_outside_closed_unit_interval(confidence):
    with pytest.raises(ValidationError):
        ExportRow(**_valid_row(confidence=confidence))


def test_export_row_rejects_non_uuid4_run_id():
    uuid1_run_id = uuid.uuid1().hex

    with pytest.raises(ValidationError):
        ExportRow(**_valid_row(run_id=uuid1_run_id))


def test_export_document_requires_schema_version_and_consistent_run_id():
    run_id = _uuid4_hex()
    metadata = ExportMetadata(
        schema_version=EXPORT_SCHEMA_VERSION,
        source_file="sample_tz.xlsx",
        output_format="xlsx",
    )

    document = ExportDocument(
        metadata=metadata,
        rows=[
            ExportRow(**_valid_row(run_id=run_id, requirement_id="REQ-001")),
            ExportRow(**_valid_row(run_id=run_id, requirement_id="REQ-002")),
        ],
    )

    assert document.to_contract_dict()["metadata"]["schema_version"] == "1.0"

    with pytest.raises(ValidationError):
        ExportDocument(
            metadata=metadata,
            rows=[
                ExportRow(**_valid_row(run_id=_uuid4_hex(), requirement_id="REQ-001")),
                ExportRow(**_valid_row(run_id=_uuid4_hex(), requirement_id="REQ-002")),
            ],
        )


def test_export_metadata_requires_schema_version():
    with pytest.raises(ValidationError):
        ExportMetadata(source_file="sample_tz.xlsx", output_format="xlsx")
