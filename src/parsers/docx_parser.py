"""DOCX parser stub for tender requirements (ТЗ).

This module provides a placeholder implementation for parsing .docx files.
Full implementation can be added later using libraries like `python-docx`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Union

from src.parsers.base_parser import BaseParser, ParserError

logger = logging.getLogger(__name__)


class DocxParseError(ParserError):
    """Raised when the DOCX file cannot be parsed into requirements."""

    pass


class DocxParser(BaseParser):
    """Parser for Microsoft Word (.docx) documents.

    Currently a stub that raises :exc:`DocxParseError` indicating that
    DOCX parsing is not yet implemented.
    """

    def load_requirements(
        self, file_path: Union[str, Path]
    ) -> List[Dict[str, Union[int, str]]]:
        """Load tender requirements from a DOCX file.

        Args:
            file_path: Path to the .docx file.

        Returns:
            A list of dictionaries shaped as ``{"id": int, "text": str}``.

        Raises:
            FileNotFoundError: If the file does not exist.
            DocxParseError: Always raised in this stub implementation.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"DOCX file not found: {path}")

        raise DocxParseError(
            "DOCX parsing is not yet implemented. "
            "Please use Excel (.xlsx) files for now or install `python-docx` "
            "and extend this class."
        )


def load_requirements(file_path: Union[str, Path]) -> List[Dict[str, Union[int, str]]]:
    """Convenience function to load requirements from a DOCX file.

    Args:
        file_path: Path to the .docx file.

    Returns:
        A list of dictionaries shaped as ``{"id": int, "text": str}``.

    Raises:
        FileNotFoundError: If the file does not exist.
        DocxParseError: Raised as DOCX parsing is not implemented.
    """
    parser = DocxParser()
    return parser.load_requirements(file_path)
