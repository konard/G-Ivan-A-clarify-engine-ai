from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_PATH = "docs/research/2026-05-20_bl-60_next-gen-architecture_v1.md"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _section(text: str, number: int) -> str:
    marker = f"\n## {number}. "
    start = text.index(marker)
    next_marker = f"\n## {number + 1}. "
    end = text.find(next_marker, start + len(marker))
    return text[start:] if end == -1 else text[start:end]


def test_bl60_sections_4_to_15_have_ba_adaptation_blocks() -> None:
    research = "\n" + _read(RESEARCH_PATH)

    for number in range(4, 16):
        section = _section(research, number)
        assert "### 🧠 Пояснение для БА" in section, number
        assert "### 📚 Что почитать" in section, number
        assert "<details" in section, number
        assert "проверено 2026-05-21" in section, number
        assert section.count("|") >= 10, number


def test_bl60_ru_adaptation_is_linked_from_docs_index_and_changelog() -> None:
    docs_index = _read("docs/README.md")
    changelog = _read("CHANGELOG.md")

    assert RESEARCH_PATH in docs_index
    assert "BL-60-ru" in docs_index
    assert "DOCS: BL-60-ru — Russian adaptation with educational annotations for non-technical stakeholders" in changelog
