"""Input file parsers (Excel, DOCX, etc.) for the TZ analyzer."""

from src.parsers.excel_parser import load_requirements as load_excel_requirements
from src.parsers.docx_parser import load_requirements as load_docx_requirements
from src.parsers.base_parser import BaseParser, ParserError

__all__ = [
    "load_excel_requirements",
    "load_docx_requirements",
    "BaseParser",
    "ParserError",
]


def load_requirements(file_path: str) -> list:
    """Load requirements from a file based on its extension.

    Args:
        file_path: Path to the input file (.xlsx or .docx).

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
        return load_excel_requirements(file_path)
    elif ext == ".docx":
        return load_docx_requirements(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}. Use .xlsx or .docx.")
