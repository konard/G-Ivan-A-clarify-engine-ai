"""Input file parsers (Excel, DOCX, etc.) for the TZ analyzer."""

from src.parsers.excel_parser import (
    load_requirements as load_excel_requirements,
    load_config,
    setup_logging,
    ExcelParseError,
)
from src.parsers.docx_parser import load_requirements as load_docx_requirements
from src.parsers.base_parser import BaseParser, ParserError

__all__ = [
    "load_excel_requirements",
    "load_docx_requirements",
    "load_config",
    "setup_logging",
    "BaseParser",
    "ParserError",
    "ExcelParseError",
]


def load_requirements(file_path: str, config_path: str = None) -> list:
    """Load requirements from a file based on its extension.

    Args:
        file_path: Path to the input file (.xlsx or .docx).
        config_path: Путь к файлу конфигурации (опционально).

    Returns:
        A list of dictionaries shaped as ``{"id": int, "text": str}``.

    Raises:
        ValueError: If the file extension is not supported.
        FileNotFoundError: If the file does not exist.
    """
    from pathlib import Path

    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".xlsx":
        return load_excel_requirements(file_path, config_path=config_path)
    elif ext == ".docx":
        return load_docx_requirements(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}. Use .xlsx or .docx.")
