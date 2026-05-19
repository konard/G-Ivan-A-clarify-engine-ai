"""Format-invariant export contract for export-markup v1.0.

The models in this module define the shared row shape that future
``.xlsx`` / ``.docx`` / ``.md`` exporters must validate before serialisation.
They deliberately do not implement any concrete file writer.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)

EXPORT_SCHEMA_VERSION = "1.0"

REQUIRED_COLUMN_IDS = (
    "requirement_id",
    "requirement_text",
    "Ref",
    "status",
    "comment",
    "confidence",
    "run_id",
)

MVP_COLUMN_IDS = ("status", "comment", "confidence", "run_id")

EXPORT_STATUS_VALUES = ("Да", "Нет", "Частично", "НД", "Ошибка")

RefType = Literal["table_cell_list", "paragraph", "list_item"]
Status = Literal["Да", "Нет", "Частично", "НД", "Ошибка"]
ListPathItem = Union[int, StrictStr]


class RefLocator(BaseModel):
    """Canonical trace locator supplied by parsers and written to reports."""

    model_config = ConfigDict(extra="allow")

    type: RefType
    source_file: StrictStr
    table_index: Optional[int] = None
    row: Optional[int] = None
    col: Optional[int] = None
    list_path: Optional[List[ListPathItem]] = None
    para_index: Optional[int] = None

    @field_validator("source_file")
    @classmethod
    def _source_file_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Ref.source_file must not be empty")
        return value

    @field_validator("table_index", "row", "col", "para_index")
    @classmethod
    def _locator_indexes_are_non_negative(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Ref numeric locator fields must be non-negative")
        return value

    @model_validator(mode="after")
    def _locator_has_required_coordinates(self) -> "RefLocator":
        if self.type == "paragraph" and self.para_index is None:
            raise ValueError("paragraph Ref requires para_index")
        if self.type == "list_item" and not self.list_path:
            raise ValueError("list_item Ref requires non-empty list_path")
        has_table_cell_coordinate = any(
            value is not None for value in (self.table_index, self.row, self.col)
        ) or bool(self.list_path)
        if self.type == "table_cell_list" and not has_table_cell_coordinate:
            raise ValueError(
                "table_cell_list Ref requires table_index, row, col, or list_path"
            )
        return self


class ExportRow(BaseModel):
    """One format-invariant analysis result row for export-markup v1.0."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    requirement_id: StrictStr
    requirement_text: StrictStr
    ref: RefLocator = Field(alias="Ref")
    status: Status
    comment: StrictStr
    confidence: float = Field(ge=0.0, le=1.0)
    run_id: StrictStr

    @field_validator("requirement_id")
    @classmethod
    def _requirement_id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requirement_id must not be empty")
        return value

    @field_validator("run_id")
    @classmethod
    def _run_id_is_uuid4(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("run_id must not be empty")
        try:
            parsed = uuid.UUID(value)
        except ValueError as exc:
            raise ValueError("run_id must be a valid UUID") from exc
        if parsed.version != 4:
            raise ValueError("run_id must be a UUID4 value")
        return value

    def to_contract_dict(self) -> Dict[str, Any]:
        """Return a JSON-compatible dict using the public ``Ref`` alias."""

        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class ExportMetadata(BaseModel):
    """Report-level metadata required by export-markup v1.0."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["1.0"]
    source_file: Optional[StrictStr] = None
    output_format: Optional[Literal["xlsx", "docx", "md"]] = None

    @field_validator("source_file")
    @classmethod
    def _metadata_source_file_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("metadata.source_file must not be empty when provided")
        return value


class ExportDocument(BaseModel):
    """A complete report payload before format-specific serialisation."""

    model_config = ConfigDict(extra="allow")

    metadata: ExportMetadata
    rows: List[ExportRow]

    @model_validator(mode="after")
    def _rows_share_single_run_id(self) -> "ExportDocument":
        run_ids = {row.run_id for row in self.rows}
        if len(run_ids) > 1:
            raise ValueError("all export rows must share the same run_id")
        return self

    def to_contract_dict(self) -> Dict[str, Any]:
        """Return a JSON-compatible document dict with public field aliases."""

        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
