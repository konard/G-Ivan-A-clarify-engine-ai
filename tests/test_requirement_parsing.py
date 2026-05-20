"""Tests for BL-59 RequirementBoundaryDetector (issue #211).

Covers the nine scenarios documented in
``docs/research/2026-05-20_bl-59_requirement-parsing_v1.md`` §6.3:

1. ``naive`` strategy is a pure pass-through (backward compatibility).
2. ``structural`` strategy propagates section context to descendant
   requirements.
3. ``structural`` strategy detects cross-references.
4. ``structural`` strategy merges orphan continuation fragments.
5. ``hybrid`` strategy falls back to ``structural`` when the LLM toggle is
   off (no Ollama dependency on CI).
6. Backward compatibility — if the ``parsing`` section is absent from the
   config, ``load_requirements_by_extension`` returns blocks identical to
   the pre-BL-59 ``DocxParser`` output (locator unchanged).
7. The detector preserves all original locator keys.
8. Golden-set roundtrip — accuracy on ``data/parsing_golden_set_v1.jsonl``
   is ≥ 90 % across the 20 hand-labelled scenarios.
9. Performance — a synthetic 50-page DOCX parses in ≤ 30 sec on CPU.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parsers import load_requirements_by_extension  # noqa: E402
from src.parsers.requirement_boundary_detector import (  # noqa: E402
    RequirementBoundaryDetector,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_SET_PATH = REPO_ROOT / "data" / "parsing_golden_set_v1.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _structural_config(**overrides: Any) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
        "strategy": "structural",
        "min_requirement_length": 30,
        "max_heading_length": 80,
        "preserve_original_fragments": True,
    }
    cfg.update(overrides)
    return cfg


def _block(text: str, locator: Dict[str, Any], block_id: int) -> Dict[str, Any]:
    return {"id": block_id, "text": text, "locator": dict(locator)}


def _load_golden_set() -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    with GOLDEN_SET_PATH.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def _golden_blocks(entry: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"id": index + 1, "text": item["text"], "locator": dict(item["locator"])}
        for index, item in enumerate(entry["raw_blocks"])
    ]


# ---------------------------------------------------------------------------
# 1. naive strategy — pass-through
# ---------------------------------------------------------------------------


def test_strategy_naive_returns_raw_blocks_unchanged() -> None:
    raw = [
        _block(
            "7.2 Функциональные требования",
            {"type": "paragraph", "index": 1},
            1,
        ),
        _block(
            "Система должна обеспечивать запись телефонных переговоров.",
            {"type": "paragraph", "index": 2},
            2,
        ),
    ]

    detector = RequirementBoundaryDetector({"strategy": "naive"})
    refined = detector.refine(raw)

    assert [item["text"] for item in refined] == [
        "7.2 Функциональные требования",
        "Система должна обеспечивать запись телефонных переговоров.",
    ]
    # locator keys are not touched and no enrichment keys are added.
    assert refined[0]["locator"] == {"type": "paragraph", "index": 1}
    assert refined[1]["locator"] == {"type": "paragraph", "index": 2}
    assert "block_type" not in refined[0]["locator"]
    assert "section_number" not in refined[1]["locator"]


# ---------------------------------------------------------------------------
# 2. structural — section context propagation
# ---------------------------------------------------------------------------


def test_strategy_structural_propagates_section_context() -> None:
    raw = [
        _block("7 Функциональные требования", {"type": "paragraph", "index": 1}, 1),
        _block("7.2 Аналитика", {"type": "paragraph", "index": 2}, 2),
        _block(
            "Должна быть реализована панель управления KPI с возможностью кастомизации виджетов.",
            {"type": "paragraph", "index": 3},
            3,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    # Headings are dropped from output — only the requirement remains.
    assert len(refined) == 1
    locator = refined[0]["locator"]
    assert locator["section_number"] == "7.2"
    assert "Аналитика" in locator["section_title"]
    assert locator["parent_id"] == 2  # id of the closest heading block
    assert locator["block_type"] == "requirement"


def test_strategy_structural_inherits_closest_parent() -> None:
    raw = [
        _block("4 Функциональные требования", {"type": "paragraph", "index": 1}, 1),
        _block("4.2 Уведомления", {"type": "paragraph", "index": 2}, 2),
        _block(
            "Должна быть возможность настройки правил уведомлений на email и SMS.",
            {"type": "paragraph", "index": 3},
            3,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    assert len(refined) == 1
    assert refined[0]["locator"]["section_number"] == "4.2"
    assert "Уведомления" in refined[0]["locator"]["section_title"]


# ---------------------------------------------------------------------------
# 3. structural — cross-reference extraction
# ---------------------------------------------------------------------------


def test_strategy_structural_detects_cross_refs() -> None:
    raw = [
        _block("8 Требования к безопасности", {"type": "paragraph", "index": 1}, 1),
        _block(
            "Система должна обеспечивать защиту персональных данных согласно п. 7.4 "
            "и в соответствии с разделом 9.1.",
            {"type": "paragraph", "index": 2},
            2,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    assert len(refined) == 1
    cross_refs = refined[0]["locator"].get("cross_refs") or []
    assert set(cross_refs) >= {"7.4", "9.1"}


def test_strategy_structural_detects_see_pn_reference_in_table() -> None:
    raw = [
        _block("2 Архитектурные требования", {"type": "paragraph", "index": 1}, 1),
        _block(
            "Должна быть реализована трёхуровневая архитектура согласно пункту 2.1.",
            {"type": "table", "table": 1, "row": 3, "col": 2, "paragraph": 1},
            2,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    assert len(refined) == 1
    locator = refined[0]["locator"]
    assert locator["type"] == "table"
    assert locator.get("cross_refs") == ["2.1"]
    assert locator["section_number"] == "2"


# ---------------------------------------------------------------------------
# 4. structural — continuation merge
# ---------------------------------------------------------------------------


def test_strategy_structural_merges_continuation_in_table_cell() -> None:
    """Short fragment in the same table cell merges with the previous block."""
    raw = [
        _block(
            "Система должна обеспечивать отказоустойчивую работу.",
            {"type": "table", "table": 2, "row": 4, "col": 3, "paragraph": 1},
            1,
        ),
        _block(
            "См. п. 9.1 для деталей.",
            {"type": "table", "table": 2, "row": 4, "col": 3, "paragraph": 2},
            2,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    assert len(refined) == 1
    assert "отказоустойчивую работу" in refined[0]["text"]
    assert "9.1" in (refined[0]["locator"].get("cross_refs") or [])


# ---------------------------------------------------------------------------
# 5. hybrid — falls back to structural when LLM toggle off
# ---------------------------------------------------------------------------


def test_strategy_hybrid_falls_back_when_llm_disabled() -> None:
    raw = [
        _block("7 Функциональные требования", {"type": "paragraph", "index": 1}, 1),
        _block(
            "Система должна обеспечивать запись телефонных переговоров с прослушиванием.",
            {"type": "paragraph", "index": 2},
            2,
        ),
    ]

    structural = RequirementBoundaryDetector(_structural_config()).refine(raw)
    hybrid = RequirementBoundaryDetector(
        _structural_config(strategy="hybrid", use_llm_boundary_check=False)
    ).refine(raw)

    assert hybrid == structural


def test_strategy_hybrid_with_llm_enabled_returns_structural_stub(caplog) -> None:
    """LLM Layer 2 is a logging stub in this PR; result equals structural."""
    raw = [
        _block("1 Общие положения", {"type": "paragraph", "index": 1}, 1),
        _block(
            "Система должна обеспечивать многофакторную аутентификацию пользователей.",
            {"type": "paragraph", "index": 2},
            2,
        ),
    ]

    structural = RequirementBoundaryDetector(_structural_config()).refine(raw)
    with caplog.at_level("WARNING"):
        hybrid = RequirementBoundaryDetector(
            _structural_config(strategy="hybrid", use_llm_boundary_check=True)
        ).refine(raw)

    assert hybrid == structural
    assert any(
        "LLM boundary validation" in record.getMessage() for record in caplog.records
    )


# ---------------------------------------------------------------------------
# 6. Backward compat — no ``parsing`` section → naive default
# ---------------------------------------------------------------------------


def test_backward_compat_default_strategy_is_naive() -> None:
    detector = RequirementBoundaryDetector()
    assert detector.strategy == "naive"


def test_backward_compat_empty_config_returns_raw_blocks_unchanged() -> None:
    raw = [
        _block(
            "Поддержать многофакторную аутентификацию для всех пользователей системы.",
            {"type": "paragraph", "index": 4},
            1,
        ),
    ]

    detector = RequirementBoundaryDetector({})
    refined = detector.refine(raw)

    assert [item["text"] for item in refined] == [raw[0]["text"]]
    assert refined[0]["locator"] == {"type": "paragraph", "index": 4}


def test_load_requirements_with_naive_config_keeps_locator_keys(
    tmp_path: Path,
) -> None:
    """Dispatcher must not enrich locators when parsing.strategy=naive."""
    docx_lib = pytest.importorskip("docx")

    doc_path = tmp_path / "tz.docx"
    document = docx_lib.Document()
    document.add_paragraph("Обеспечить запись телефонных переговоров")
    document.save(doc_path)

    config_path = tmp_path / "parsing_naive.yaml"
    config_path.write_text(
        "parsing:\n  strategy: naive\n",
        encoding="utf-8",
    )

    items = load_requirements_by_extension(doc_path, config_path=str(config_path))
    assert items
    assert items[0]["locator"] == {"type": "paragraph", "index": 1}


# ---------------------------------------------------------------------------
# 7. Locator preserves original keys
# ---------------------------------------------------------------------------


def test_locator_preserves_original_paragraph_keys() -> None:
    raw = [
        _block("7.2 Аналитика", {"type": "paragraph", "index": 1}, 1),
        _block(
            "Должна быть реализована панель управления KPI с возможностью кастомизации виджетов.",
            {"type": "paragraph", "index": 2},
            2,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    locator = refined[0]["locator"]
    # original keys preserved verbatim
    assert locator["type"] == "paragraph"
    assert locator["index"] == 2


def test_locator_preserves_original_table_keys() -> None:
    raw = [
        _block("5 Требования к интеграциям", {"type": "paragraph", "index": 3}, 1),
        _block(
            "Система должна поддерживать интеграцию с CRM по REST API.",
            {"type": "table", "table": 1, "row": 2, "col": 2, "paragraph": 1},
            2,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    locator = refined[0]["locator"]
    assert locator["type"] == "table"
    assert locator["table"] == 1
    assert locator["row"] == 2
    assert locator["col"] == 2
    assert locator["paragraph"] == 1
    # enrichment is additive
    assert locator["section_number"] == "5"


def test_locator_preserves_excel_cell_keys() -> None:
    raw = [
        _block(
            "Поддержать запись телефонных переговоров с возможностью прослушивания.",
            {
                "type": "cell",
                "sheet_name": "Sheet1",
                "row": 7,
                "column": "Требование",
            },
            1,
        ),
    ]

    detector = RequirementBoundaryDetector(_structural_config())
    refined = detector.refine(raw)

    locator = refined[0]["locator"]
    assert locator["type"] == "cell"
    assert locator["sheet_name"] == "Sheet1"
    assert locator["row"] == 7
    assert locator["column"] == "Требование"


# ---------------------------------------------------------------------------
# 8. Golden-set roundtrip
# ---------------------------------------------------------------------------


def _evaluate_golden_entry(
    entry: Mapping[str, Any], refined: List[Dict[str, Any]]
) -> bool:
    expected = entry["expected"]

    if "requirement_count" in expected:
        if len(refined) != expected["requirement_count"]:
            return False

    if not refined:
        return True

    first = refined[0]
    locator = first.get("locator") or {}

    contains = expected.get("first_text_contains")
    if contains and contains not in first.get("text", ""):
        return False

    sn = expected.get("section_number")
    if sn is not None:
        if sn == "" or sn is None:
            if locator.get("section_number"):
                return False
        elif locator.get("section_number") != sn:
            return False

    title_contains = expected.get("section_title_contains")
    if title_contains is not None and title_contains:
        if title_contains.lower() not in str(
            locator.get("section_title", "")
        ).lower():
            return False

    expected_refs = expected.get("cross_refs")
    if expected_refs:
        actual_refs = set(locator.get("cross_refs") or [])
        if not set(expected_refs).issubset(actual_refs):
            return False

    expected_locator_type = expected.get("locator_type")
    if expected_locator_type and locator.get("type") != expected_locator_type:
        return False

    return True


def test_golden_set_file_exists_and_is_well_formed() -> None:
    assert GOLDEN_SET_PATH.exists(), GOLDEN_SET_PATH
    entries = _load_golden_set()
    assert len(entries) >= 20
    for entry in entries:
        assert {"id", "scenario", "raw_blocks", "expected"} <= set(entry)


def test_golden_set_boundary_accuracy() -> None:
    """Aggregate accuracy on the BL-59 golden set must be ≥ 90 %."""
    entries = _load_golden_set()
    detector = RequirementBoundaryDetector(_structural_config())

    passed: List[str] = []
    failed: List[str] = []
    for entry in entries:
        refined = detector.refine(_golden_blocks(entry))
        if _evaluate_golden_entry(entry, refined):
            passed.append(entry["id"])
        else:
            failed.append(entry["id"])

    accuracy = len(passed) / len(entries)
    assert accuracy >= 0.9, (
        f"Golden set accuracy {accuracy:.2%} below 90 % threshold. "
        f"Failed cases: {failed}"
    )


# ---------------------------------------------------------------------------
# 9. Performance — synthetic 50-page docx parses in ≤ 30 sec
# ---------------------------------------------------------------------------


def test_performance_synthetic_50_pages() -> None:
    """A 50-page-equivalent input must be refined in well under the 30 s budget.

    We simulate a 50-page document with ~50 paragraphs/page = ~2500 blocks,
    alternating between headings and atomic requirements. The detector runs
    in-memory (no file I/O), so the budget is a generous upper bound for the
    rule-based layer.
    """
    raw: List[Dict[str, Any]] = []
    block_id = 1
    for page in range(1, 51):
        raw.append(
            _block(
                f"{page} Требования к подсистеме {page}",
                {"type": "paragraph", "index": block_id},
                block_id,
            )
        )
        block_id += 1
        for sub in range(1, 50):
            raw.append(
                _block(
                    (
                        f"Система должна обеспечивать выполнение операции №{sub} "
                        f"в подсистеме {page} согласно п. {page}.1."
                    ),
                    {"type": "paragraph", "index": block_id},
                    block_id,
                )
            )
            block_id += 1

    detector = RequirementBoundaryDetector(_structural_config())

    start = time.perf_counter()
    refined = detector.refine(raw)
    elapsed = time.perf_counter() - start

    assert refined, "detector returned no requirements"
    assert elapsed < 30.0, (
        f"Rule-based parsing took {elapsed:.2f} sec, "
        f"exceeding the 30 sec budget for a 50-page document."
    )
