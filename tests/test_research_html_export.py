from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = (
    ROOT
    / "docs"
    / "research"
    / "html"
    / "2026-05-21_bl-61_market-research_ru-education_v1.html"
)
SCRIPT_PATH = ROOT / "scripts" / "tools" / "md_to_html_fullwidth.py"
DOCS_INDEX_PATH = ROOT / "docs" / "README.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_bl61_fullwidth_html_export_exists_with_table_contract() -> None:
    html = _read(HTML_PATH)

    assert "<!doctype html>" in html.lower()
    assert "Research: RU-education adaptation for BL-61 Market Comparison" in html
    assert "width: 100vw;" in html
    assert "max-width: none;" in html
    assert "table-layout: fixed;" in html
    assert "font-size: 11px;" in html
    assert "min-width: 80px;" in html
    assert "overflow-x: auto;" in html
    assert "@media (prefers-color-scheme: dark)" in html
    assert 'id="4-компонент-1-vector-database-search-engine"' in html
    assert "<table>" in html


def test_bl61_fullwidth_html_export_is_documented_and_reproducible() -> None:
    docs_index = _read(DOCS_INDEX_PATH)
    changelog = _read(CHANGELOG_PATH)
    script = _read(SCRIPT_PATH)

    assert "2026-05-21_bl-61_market-research_ru-education_v1.html" in docs_index
    assert "scripts/tools/md_to_html_fullwidth.py" in docs_index
    assert "DOCS: BL-61 HTML export with full-width tables for research review" in changelog
    assert "html.escape" in script
    assert "table-layout: fixed" in script
