import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "docs" / "research" / "2026-05-21_bl-61_market-research_v1.md"
EDUCATION_PATH = (
    ROOT
    / "docs"
    / "research"
    / "2026-05-21_bl-61_market-research_ru-education_v1.md"
)
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


def test_bl61_ru_education_file_exists_and_preserves_source_document() -> None:
    source = _read(SOURCE_PATH)
    education = _read(EDUCATION_PATH)

    assert "💡 **Для БА: что это значит для проекта?**" not in source
    assert "AUTO-GENERATED: do not edit education blocks manually" not in source
    assert "BL-67" in education
    assert "Elasticsearch 8.x" in education
    assert "NATS JetStream" in education
    assert "vLLM" in education
    assert "bge-reranker-large" in education


def test_bl61_sections_4_to_20_have_ba_blocks_and_external_links() -> None:
    education = "\n" + _read(EDUCATION_PATH)

    for number in range(4, 21):
        section = _section(education, number)
        assert "<!-- AUTO-GENERATED: do not edit education blocks manually -->" in section, number
        assert "💡 **Для БА: что это значит для проекта?**" in section, number
        assert "📚 **Читать далее:**" in section, number
        assert len(_external_markdown_links(section)) >= 2, number


def test_bl61_ru_education_is_linked_from_project_docs() -> None:
    docs_index = _read(DOCS_INDEX_PATH)
    changelog = _read(CHANGELOG_PATH)
    backlog = _read(BACKLOG_PATH)

    assert "2026-05-21_bl-61_market-research_ru-education_v1.md" in docs_index
    assert "DOCS: BL-67 RU-education layer for BL-61 market research" in changelog

    backlog_line = next(line for line in backlog.splitlines() if line.startswith("| BL-67 |"))
    assert "✅ Closed" in backlog_line
    assert "pull/221" in backlog_line
