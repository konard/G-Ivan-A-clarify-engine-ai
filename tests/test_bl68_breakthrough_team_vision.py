from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = "docs/research/2026-05-21_bl-68_breakthrough-team-vision_v1.md"
BACKLOG_PATH = "docs/backlog/2026-05-17_backlog_rag-optimization_v1.5.md"
CHANGELOG_PATH = "CHANGELOG.md"
DOCS_INDEX_PATH = "docs/README.md"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bl68_research_file_exists() -> None:
    assert (ROOT / DOC_PATH).exists(), f"Research file not found: {DOC_PATH}"


def test_bl68_research_covers_key_content() -> None:
    document = _read(DOC_PATH)

    assert "Прорыва" in document
    assert "data moat" in document or "data ownership" in document.lower() or "Data ownership" in document
    assert "Core + Extensible Shell" in document or "Core+Extensible Shell" in document
    assert "Hybrid" in document or "hybrid" in document
    assert "Streamlit" in document
    assert "BL-26" in document
    assert "self-hosted" in document or "Self-hosted" in document
    assert "Ollama" in document


def test_bl68_scope_note_no_main_docs() -> None:
    document = _read(DOC_PATH)
    assert "Не вносить" in document or "только в папке исследования" in document.lower() or "Сохранён исключительно" in document


def test_bl68_is_linked_from_project_docs() -> None:
    changelog = _read(CHANGELOG_PATH)
    backlog = _read(BACKLOG_PATH)
    docs_index = _read(DOCS_INDEX_PATH)

    assert "BL-68" in changelog

    backlog_line = next(line for line in backlog.splitlines() if line.startswith("| BL-68 |"))
    assert "✅ Closed" in backlog_line
    assert "pull/231" in backlog_line
    assert DOC_PATH in backlog_line or "bl-68_breakthrough" in backlog_line

    assert "BL-68" in docs_index
    assert "bl-68_breakthrough" in docs_index
