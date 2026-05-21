import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "research" / "2026-05-21_bl-61_market-research_ru-education_v2.md"
HTML_PATH = (
    ROOT
    / "docs"
    / "research"
    / "html"
    / "2026-05-21_bl-61_market-research_ru-education_v2.html"
)
SCRIPT_PATH = ROOT / "scripts" / "tools" / "md_to_html_fullwidth.py"
BACKLOG_PATH = ROOT / "docs" / "backlog" / "2026-05-17_backlog_rag-optimization_v1.5.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
DOCS_INDEX_PATH = ROOT / "docs" / "README.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, number: int) -> str:
    marker = f"\n## {number}. "
    start = text.index(marker)
    next_marker = f"\n## {number + 1}. "
    end = text.find(next_marker, start + len(marker))
    return text[start:] if end == -1 else text[start:end]


def _external_markdown_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(https?://[^)]+\)", text)


def test_bl61_v2_component_tables_have_ru_explanations_and_concrete_usage() -> None:
    document = "\n" + _read(DOC_PATH)

    for number in range(4, 17):
        section = _section(document, number)
        first_table_header = next(line for line in section.splitlines() if line.startswith("| № |"))
        assert "Пояснение для БА" in first_table_header, number
        assert "**Что это значит для проекта:**" in section, number
        assert "**Почему важно для БА:**" in section, number
        assert "**Технически:**" in section, number
        assert "**Когда выбирать:**" in section, number
        assert "1-3 БА" in section, number
        assert "≤15 запросов/мин" in section, number
        assert len(_external_markdown_links(section)) >= 2, number


def test_bl61_v2_html_uses_wrapping_table_cells_without_ellipsis() -> None:
    html = _read(HTML_PATH)
    script = _read(SCRIPT_PATH)

    assert "white-space: normal;" in html
    assert "overflow-wrap: anywhere;" in html
    assert "text-overflow: ellipsis;" not in html
    assert "white-space: nowrap;" not in html
    assert "white-space: normal;" in script
    assert "text-overflow: ellipsis;" not in script


def test_bl61_v2_is_linked_from_project_docs() -> None:
    docs_index = _read(DOCS_INDEX_PATH)
    changelog = _read(CHANGELOG_PATH)
    backlog = _read(BACKLOG_PATH)

    assert "2026-05-21_bl-61_market-research_ru-education_v2.md" in docs_index
    assert "2026-05-21_bl-61_market-research_ru-education_v2.html" in docs_index
    assert "DOCS: BL-61.1 business-friendly education blocks for market research" in changelog

    backlog_line = next(line for line in backlog.splitlines() if line.startswith("| BL-61.1 |"))
    assert "✅ Closed" in backlog_line
    assert "pull/225" in backlog_line
