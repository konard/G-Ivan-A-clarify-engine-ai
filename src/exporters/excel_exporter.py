"""Excel exporter for classification results.

The exporter preserves the original ТЗ structure (all columns from the input
workbook) and appends the **minimal MVP set** mandated by CONCEPT.md §4 FR-06:

    [Статус], [Комментарий], [Confidence], [RunID]

Additional operational columns ([Цитаты], [Рекомендация], [Требует ревью],
[Провайдер], [Ошибка]) are emitted alongside the MVP four — the extended schema
is captured in ADR-002 (post-pilot) but kept available today for BAs and
auditors who need the full picture in one file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

logger = logging.getLogger(__name__)

MVP_COLUMNS: List[str] = [
    "[Статус]",
    "[Комментарий]",
    "[Confidence]",
    "[RunID]",
]

EXTENDED_COLUMNS: List[str] = [
    "[Цитаты]",
    "[Уверенность]",  # alias retained for backward compatibility with audits
    "[Рекомендация]",
    "[Требует ревью]",
    "[Провайдер]",
    "[Ошибка]",
]

RESULT_COLUMNS: List[str] = MVP_COLUMNS + EXTENDED_COLUMNS


def _format_citations(citations: List[Dict[str, Any]]) -> str:
    if not citations:
        return ""
    parts: List[str] = []
    for citation in citations:
        source = citation.get("source", "?")
        section = citation.get("section", "")
        quote = citation.get("quote", "")
        chunk = f"{source}"
        if section:
            chunk += f" / {section}"
        if quote:
            chunk += f": «{quote}»"
        parts.append(chunk)
    return "\n".join(parts)


def _classification_row(item: Dict[str, Any], run_id: str = "") -> Dict[str, Any]:
    classification = item.get("classification") or {}
    confidence = float(classification.get("confidence", 0.0) or 0.0)
    return {
        "[Статус]": classification.get("classification", "НД"),
        "[Комментарий]": classification.get("reasoning", ""),
        "[Confidence]": confidence,
        "[RunID]": run_id,
        "[Цитаты]": _format_citations(classification.get("citations", [])),
        "[Уверенность]": confidence,
        "[Рекомендация]": classification.get("recommendations", ""),
        "[Требует ревью]": "Да" if classification.get("requires_ba_review") else "Нет",
        "[Провайдер]": classification.get("provider", ""),
        "[Ошибка]": item.get("error", ""),
    }


def save_results(
    results: Iterable[Dict[str, Any]],
    output_file: Union[str, Path],
    sheet_name: str = "Results",
    source_file: Optional[Union[str, Path]] = None,
    run_id: Optional[str] = None,
) -> Path:
    """Persist classification results to an Excel workbook.

    Args:
        results: Iterable of dicts produced by :func:`src.pipeline.run_analysis`.
            Each dict carries the original ``id``/``text`` plus a
            ``classification`` payload (see ``LLMClient.classify_requirement``).
        output_file: Destination ``.xlsx`` path.
        sheet_name: Worksheet name to write to.
        source_file: Optional input workbook path. When supplied, the exporter
            preserves the source columns and appends the classification
            columns next to them (row order is matched by 1-based ``id``).
        run_id: Optional pipeline run identifier. Stored as a worksheet-level
            metadata column ``[run_id]`` if provided.

    Returns:
        The absolute path of the saved workbook.
    """
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pandas is required to export results. Install it with `pip install pandas openpyxl`."
        ) from exc

    results_list: List[Dict[str, Any]] = list(results)
    run_id_value = run_id or ""
    classification_rows = [_classification_row(item, run_id_value) for item in results_list]

    source_df = _load_source_dataframe(source_file)
    if source_df is not None and not source_df.empty:
        # Match each result back to its source row by 1-based id.
        n = len(source_df)
        empty_row = {col: "" for col in RESULT_COLUMNS}
        empty_row["[Confidence]"] = 0.0
        empty_row["[Уверенность]"] = 0.0
        empty_row["[RunID]"] = run_id_value
        appended_rows: List[Dict[str, Any]] = [dict(empty_row) for _ in range(n)]
        for item, row in zip(results_list, classification_rows):
            idx = int(item.get("id", 0)) - 1
            if 0 <= idx < n:
                appended_rows[idx] = row
        appended_df = pd.DataFrame(appended_rows, columns=RESULT_COLUMNS)
        merged = pd.concat([source_df.reset_index(drop=True), appended_df], axis=1)
    else:
        # No source workbook supplied — fall back to a minimal results-only sheet.
        minimal_rows = []
        for item, row in zip(results_list, classification_rows):
            minimal_rows.append(
                {
                    "ID": item.get("id"),
                    "Требование": item.get("text"),
                    **row,
                }
            )
        merged = pd.DataFrame(minimal_rows)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_excel(output_path, sheet_name=sheet_name, index=False)
    logger.info("Saved %d rows to %s", len(merged), output_path, extra={"run_id": run_id_value} if run_id_value else {})
    return output_path


def _load_source_dataframe(source_file: Optional[Union[str, Path]]):
    """Best-effort read of the input ``.xlsx`` to preserve its structure."""
    if not source_file:
        return None
    path = Path(source_file)
    if not path.exists():
        return None
    if path.suffix.lower() not in {".xlsx", ".xls"}:
        return None
    try:
        import pandas as pd  # type: ignore
    except ImportError:  # pragma: no cover
        return None
    try:
        return pd.read_excel(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not preserve structure from %s: %s", path, exc)
        return None
