"""Input file parsers (Excel, DOCX, etc.) for the TZ analyzer."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.parsers.base_parser import BaseParser, ParserError
from src.parsers.docx_parser import DocxParser, load_requirements as load_docx_requirements
from src.parsers.excel_parser import (
    ExcelParser,
    ExcelParseError,
    load_config,
    load_requirements as load_excel_requirements,
    setup_logging,
)
from src.parsers.requirement_boundary_detector import RequirementBoundaryDetector

__all__ = [
    "ExcelParser",
    "DocxParser",
    "load_excel_requirements",
    "load_docx_requirements",
    "load_requirements_by_extension",
    "load_requirements",
    "parser_for_extension",
    "load_config",
    "setup_logging",
    "BaseParser",
    "ParserError",
    "ExcelParseError",
    "RequirementBoundaryDetector",
]


def parser_for_extension(
    file_path: str | Path,
    *,
    config_path: str | None = None,
    run_id: str | None = None,
) -> BaseParser:
    """Return the parser object matching the input file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in {".xlsx", ".xls"}:
        return ExcelParser(sheet_name=None, config_path=config_path, run_id=run_id)
    if ext == ".docx":
        return DocxParser(config_path=config_path)
    raise NotImplementedError(
        f"Unsupported file extension: {ext or '<none>'}. "
        "Please convert the input file to .docx and retry."
    )


def load_requirements_by_extension(
    file_path: str | Path,
    config_path: str | None = None,
    run_id: str | None = None,
) -> list:
    """Load requirements from a file based on its extension.

    The dispatcher routes to the appropriate format-specific parser and then
    applies the BL-59 :class:`RequirementBoundaryDetector` post-processing
    step (rule-based structural analysis + optional LLM boundary check).
    The public contract (``[{id, text, locator}]``) is preserved; the
    locator may carry additional structural keys (``section_number``,
    ``section_title``, ``parent_id``, ``cross_refs``, ``block_type``,
    ``span``) when the detector recognises them.

    Args:
        file_path: Path to the input file (.xlsx or .docx).
        config_path: Путь к файлу конфигурации (опционально). При
            отсутствии секции ``parsing`` в конфиге detector работает в
            режиме ``naive`` (pass-through), что эквивалентно поведению до
            BL-59.

    Returns:
        A list of dictionaries shaped as ``{"id": int, "text": str, "locator": dict}``.

    Raises:
        NotImplementedError: If the file extension is not supported.
        FileNotFoundError: If the file does not exist.
    """
    parser = parser_for_extension(file_path, config_path=config_path, run_id=run_id)
    raw_requirements = parser.load_requirements(file_path)
    return _apply_boundary_detector(raw_requirements, config_path=config_path)


def _apply_boundary_detector(
    raw_requirements: List[Dict[str, Any]],
    *,
    config_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Apply BL-59 RequirementBoundaryDetector if configured.

    Returns ``raw_requirements`` unchanged when the parsing config cannot be
    loaded or does not declare a ``parsing`` section, which keeps backward
    compatibility with pre-BL-59 setups.
    """
    try:
        config = load_config(config_path)
    except Exception:  # noqa: BLE001 - never block parsing on config issues
        return raw_requirements

    parsing_config = (config or {}).get("parsing") or {}
    detector = RequirementBoundaryDetector(parsing_config)
    return detector.refine(raw_requirements)


def load_requirements(
    file_path: str | Path,
    config_path: str | None = None,
    run_id: str | None = None,
) -> list:
    """Backward-compatible alias for the extension dispatcher."""
    return load_requirements_by_extension(
        file_path, config_path=config_path, run_id=run_id
    )
