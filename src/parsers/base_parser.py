"""Base parser interface for tender requirement extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Union


class BaseParser(ABC):
    """Abstract base class for all requirement parsers.

    Subclasses must implement the :meth:`load_requirements` method to extract
    atomic requirements from a specific file format (e.g., Excel, DOCX).
    """

    @abstractmethod
    def load_requirements(
        self, file_path: Union[str, Path]
    ) -> List[Dict[str, Union[int, str]]]:
        """Load requirements from a file.

        Args:
            file_path: Path to the input file.

        Returns:
            A list of dictionaries shaped as ``{"id": int, "text": str}``.

        Raises:
            FileNotFoundError: If the file does not exist.
            ParserError: If the file cannot be parsed.
        """
        pass


class ParserError(RuntimeError):
    """Base exception for parser-related errors."""

    pass
