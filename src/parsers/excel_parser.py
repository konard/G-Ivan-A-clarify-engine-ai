"""Excel parser for tender requirements (ТЗ).

Reads an .xlsx workbook and extracts a list of atomic requirements from the
"Требование" column (or the first non-empty textual column as a fallback).
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import pandas as pd
    import yaml
except ImportError as exc:  # pragma: no cover - import guarded for environments without pandas
    pd = None  # type: ignore[assignment]
    yaml = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

# Глобальный run_id для текущей сессии парсинга
_current_run_id: str = str(uuid.uuid4())

# Инициализация логгера
logger = logging.getLogger(__name__)

REQUIREMENT_COLUMN_CANDIDATES_DEFAULT = [
    "Требование",
    "требование",
    "Requirement",
    "requirement",
    "Текст требования",
    "Описание",
    "Суть",
    "Наименование",
    "Description",
]


class JsonFormatter(logging.Formatter):
    """Форматтер логов в JSON с добавлением run_id."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": getattr(record, "run_id", _current_run_id),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_json: bool = True,
) -> None:
    """Настроить логирование с JSON форматом и run_id.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Путь к файлу лога. Если None, логи выводятся в stderr.
        use_json: Если True, использовать JSON формат, иначе текстовый.
    """
    logger_root = logging.getLogger()
    logger_root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Очищаем существующие обработчики
    logger_root.handlers.clear()

    formatter: logging.Formatter
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            f"%(asctime)s - %(name)s - %(levelname)s - [run_id:{_current_run_id}] - %(message)s"
        )

    handler: logging.Handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger_root.addHandler(handler)


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Загрузить конфигурацию из YAML файла.

    Args:
        config_path: Путь к файлу конфигурации. По умолчанию ищет configs/parsing_config.yaml.

    Returns:
        Словарь с конфигурацией.

    Raises:
        FileNotFoundError: Если файл конфигурации не найден.
        ExcelParseError: Если не удалось загрузить зависимости для чтения YAML.
    """
    if yaml is None:  # pragma: no cover - defensive
        raise ExcelParseError(
            "PyYAML is required to load configuration. Install it with `pip install pyyaml`."
        ) from _IMPORT_ERROR

    if config_path is None:
        # Поиск конфига относительно корня проекта
        possible_paths = [
            Path("configs/parsing_config.yaml"),
            Path(__file__).parent.parent / "configs" / "parsing_config.yaml",
        ]
        for p in possible_paths:
            if p.exists():
                config_path = p
                break
        else:
            # Возвращаем конфигурацию по умолчанию, если файл не найден
            logging.warning("Config file not found, using defaults.")
            return {
                "allowed_extensions": [".xlsx", ".xls", ".docx"],
                "column_keywords": REQUIREMENT_COLUMN_CANDIDATES_DEFAULT,
                "text_processing": {
                    "trim": True,
                    "lowercase": False,
                    "remove_empty": True,
                    "min_length": 5,
                },
                "logging": {"level": "INFO", "format": "json", "output": "logs/parser.log"},
                "incoming_dir": "data/incoming",
            }

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config or {}


class ExcelParseError(RuntimeError):
    """Raised when the Excel file cannot be parsed into requirements."""

    def __init__(self, message: str, run_id: Optional[str] = None):
        super().__init__(message)
        self.run_id = run_id or _current_run_id


def _ensure_pandas() -> None:
    if pd is None:  # pragma: no cover - defensive
        raise ExcelParseError(
            "pandas is required to parse Excel files. Install it with "
            "`pip install pandas openpyxl`."
        ) from _IMPORT_ERROR


def _detect_requirement_column(
    df: "pd.DataFrame", keywords: Optional[List[str]] = None
) -> str:
    """Return the column name to use as the source of requirement text.

    Args:
        df: DataFrame с данными Excel.
        keywords: Список ключевых слов для поиска колонки.

    Returns:
        Имя найденной колонки.

    Raises:
        ExcelParseError: Если ни одна подходящая колонка не найдена.
    """
    if keywords is None:
        keywords = REQUIREMENT_COLUMN_CANDIDATES_DEFAULT

    for candidate in keywords:
        if candidate in df.columns:
            return candidate

    # Fallback: first column whose values are mostly non-empty strings.
    for column in df.columns:
        series = df[column].dropna()
        if series.empty:
            continue
        if series.map(lambda v: isinstance(v, str) and v.strip()).any():
            logger.warning(
                "No standard requirement column found; using fallback column '%s'.",
                column,
                extra={"run_id": _current_run_id},
            )
            return column

    raise ExcelParseError(
        "No requirement column found. Expected one of: " + ", ".join(keywords)
    )


def load_requirements(
    file_path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = 0,
    column: Optional[str] = None,
    config_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Union[int, str]]]:
    """Load tender requirements from an Excel workbook.

    Args:
        file_path: Path to the .xlsx file.
        sheet_name: Sheet name or index. Defaults to the first sheet.
        column: Explicit requirement column name. If omitted, the parser tries
            the standard names listed in :data:`REQUIREMENT_COLUMN_CANDIDATES_DEFAULT`.
        config_path: Путь к файлу конфигурации. Если не указан, используется конфиг по умолчанию.

    Returns:
        A list of dictionaries shaped as ``{"id": int, "text": str}``.

    Raises:
        FileNotFoundError: If the file does not exist.
        ExcelParseError: If the file cannot be read or contains no requirements.
    """
    _ensure_pandas()

    # Загружаем конфигурацию
    config = load_config(config_path)
    
    # Настраиваем логирование на основе конфига
    log_config = config.get("logging", {})
    setup_logging(
        level=log_config.get("level", "INFO"),
        log_file=log_config.get("output") if log_config.get("format") == "json" else None,
        use_json=log_config.get("format", "json") == "json",
    )

    path = Path(file_path)
    if not path.exists():
        logger.error("Excel file not found: %s", path, extra={"run_id": _current_run_id})
        raise FileNotFoundError(f"Excel file not found: {path}")
    if path.stat().st_size == 0:
        logger.error("Excel file is empty: %s", path, extra={"run_id": _current_run_id})
        raise ExcelParseError(f"Excel file is empty: {path}", _current_run_id)

    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception as exc:  # pandas wraps many parser errors
        logger.error("Failed to read Excel file %s: %s", path, exc, extra={"run_id": _current_run_id})
        raise ExcelParseError(f"Failed to read Excel file {path}: {exc}", _current_run_id) from exc

    if df.empty:
        logger.error("Excel sheet is empty: %s", path, extra={"run_id": _current_run_id})
        raise ExcelParseError(f"Excel sheet is empty: {path}", _current_run_id)

    # Получаем ключевые слова из конфига или используем дефолтные
    keywords = config.get("column_keywords", REQUIREMENT_COLUMN_CANDIDATES_DEFAULT)
    target_column = column or _detect_requirement_column(df, keywords)
    if target_column not in df.columns:
        logger.error(
            "Column '%s' is not present in %s. Available columns: %s",
            target_column,
            path,
            list(df.columns),
            extra={"run_id": _current_run_id},
        )
        raise ExcelParseError(
            f"Column '{target_column}' is not present in {path}. "
            f"Available columns: {list(df.columns)}",
            _current_run_id,
        )

    # Настройки обработки текста
    text_config = config.get("text_processing", {})
    do_trim = text_config.get("trim", True)
    do_lowercase = text_config.get("lowercase", False)
    remove_empty = text_config.get("remove_empty", True)
    min_length = text_config.get("min_length", 5)

    requirements: List[Dict[str, Union[int, str]]] = []
    for idx, raw_value in enumerate(df[target_column].tolist(), start=1):
        if raw_value is None:
            continue
        text = str(raw_value)
        if do_trim:
            text = text.strip()
        if do_lowercase:
            text = text.lower()
        if remove_empty and (not text or text.lower() == "nan"):
            continue
        if len(text) < min_length:
            logger.warning(
                "Requirement %d is too short (%d chars), skipping: %s",
                idx,
                len(text),
                text[:50],
                extra={"run_id": _current_run_id},
            )
            continue
        requirements.append({"id": idx, "text": text})

    if not requirements:
        logger.error(
            "Column '%s' in %s does not contain any valid requirements.",
            target_column,
            path,
            extra={"run_id": _current_run_id},
        )
        raise ExcelParseError(
            f"Column '{target_column}' in {path} does not contain any non-empty values.",
            _current_run_id,
        )

    logger.info(
        "Loaded %d requirements from %s", len(requirements), path, extra={"run_id": _current_run_id}
    )
    return requirements
