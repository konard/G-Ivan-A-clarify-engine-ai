from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = "docs/research/2026-05-21_bl-62_synthesis-optimized-architectures_v1.md"
BACKLOG_PATH = "docs/backlog/2026-05-17_backlog_rag-optimization_v1.5.md"
CHANGELOG_PATH = "CHANGELOG.md"
DOCS_INDEX_PATH = "docs/README.md"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _section(text: str, number: int) -> str:
    marker = f"\n## {number}. "
    start = text.index(marker)
    next_marker = f"\n## {number + 1}. "
    end = text.find(next_marker, start + len(marker))
    return text[start:] if end == -1 else text[start:end]


def test_bl62_synthesis_research_covers_issue_dod() -> None:
    document = "\n" + _read(DOC_PATH)

    assert "Synthesis Research" in document
    assert "Бюджетно-оптимизированный" in document
    assert "Целе-оптимизированный" in document
    assert "docs/research/2026-05-20_bl-60_next-gen-architecture_v1.md" in document
    assert "docs/research/2026-05-21_bl-61_market-research_v1.md" in document

    for number in range(3, 5):
        option = _section(document, number)
        assert "```mermaid" in option, number
        assert "TCO" in option and "12 мес" in option, number
        assert "Roadmap" in option, number
        assert "Rollback" in option, number
        assert "Риски" in option, number
        assert "Критерии выбора" in option, number

    assert "NIST AI RMF" in document
    assert "OWASP LLM Top 10" in document
    assert "Strangler Fig" in document
    assert "FrugalGPT" in document
    assert "evaluate_rag.py" in document
    assert "smoke на ARM" in document
    assert "ADR-010" in document


def test_bl62_synthesis_is_linked_from_project_docs() -> None:
    changelog = _read(CHANGELOG_PATH)
    backlog = _read(BACKLOG_PATH)
    docs_index = _read(DOCS_INDEX_PATH)

    assert "RESEARCH: BL-62 synthesis of optimized architecture options (budget vs target)" in changelog

    backlog_line = next(line for line in backlog.splitlines() if line.startswith("| BL-62 |"))
    assert "✅ Closed" in backlog_line
    assert "pull/227" in backlog_line
    assert DOC_PATH in backlog_line

    assert DOC_PATH in docs_index
