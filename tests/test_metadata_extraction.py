"""Tests for BL-02 chunk metadata extraction (issue #87).

Every chunk persisted in ChromaDB must carry the six BL-02 / BL-16a / NFR-02
required keys: ``source``, ``chunk_idx``, ``page_number``, ``section_title``,
``section_number``, ``product``. These tests pin the small extraction
helpers added to ``knowledge_base/indexing/build_index.py`` so regressions
in heading detection or product inference surface quickly.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "knowledge_base" / "indexing" / "build_index.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_index_bl02", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_required_metadata_keys_are_six() -> None:
    module = _load_module()
    assert module.REQUIRED_METADATA_KEYS == (
        "source",
        "chunk_idx",
        "page_number",
        "section_title",
        "section_number",
        "product",
    )


def test_extract_section_detects_dotted_numeric_heading() -> None:
    module = _load_module()
    text = "4.2 Подключение коннектора Битрикс24\nДалее идёт обычный абзац."
    number, title = module.extract_section(text)
    assert number == "4.2"
    assert "Битрикс24" in title


def test_extract_section_detects_razdel_heading() -> None:
    module = _load_module()
    text = "Раздел 5.1 Интеграционные протоколы\nREST API, SOAP, Webhooks."
    number, title = module.extract_section(text)
    assert number == "5.1"
    assert "Интеграционные" in title


def test_extract_section_returns_empty_when_missing() -> None:
    module = _load_module()
    assert module.extract_section("Просто текст без заголовка.") == ("", "")
    assert module.extract_section("") == ("", "")


def test_infer_product_uses_longest_matching_prefix() -> None:
    module = _load_module()
    assert module.infer_product("Click2call_Chrome_UserManual_1_0.pdf") == "Click2Call"
    assert module.infer_product("MangoOffice_VPBX_API_v1.9.pdf") == "VPBX API"
    assert module.infer_product("RECHEVAYA-ANALITIKA_1.26.18.pdf") == "Речевая аналитика"
    assert module.infer_product("Rolevaya-model-VATS_1_26_08.pdf") == "ВАТС"
    assert module.infer_product("SIP_trunk-1.23.43.pdf") == "SIP Trunk"


def test_infer_product_returns_unknown_for_unmapped_file() -> None:
    module = _load_module()
    assert module.infer_product("totally_unknown_doc.pdf") == "unknown"


def test_build_chunk_metadata_emits_all_required_keys() -> None:
    module = _load_module()
    meta = module.build_chunk_metadata(
        source="MangoOffice_VPBX_API_v1.9.pdf",
        chunk_idx=7,
        page_number=12,
        text="4.2 Подключение коннектора Битрикс24\nКонтекст ниже.",
    )
    for key in module.REQUIRED_METADATA_KEYS:
        assert key in meta, f"missing required key {key}"
    assert meta["source"] == "MangoOffice_VPBX_API_v1.9.pdf"
    assert meta["chunk_idx"] == 7
    assert meta["page_number"] == 12
    assert meta["section_number"] == "4.2"
    assert "Битрикс24" in meta["section_title"]
    assert meta["product"] == "VPBX API"


def test_build_chunk_metadata_falls_back_for_unknown_product() -> None:
    module = _load_module()
    meta = module.build_chunk_metadata(
        source="random_doc.txt",
        chunk_idx=0,
        page_number=1,
        text="Без заголовка.",
    )
    assert meta["product"] == "unknown"
    assert meta["section_title"] == ""
    assert meta["section_number"] == ""
    assert meta["page_number"] == 1


def test_metadata_coverage_counts_fully_filled_chunks() -> None:
    module = _load_module()
    full = {
        "source": "a.pdf",
        "chunk_idx": 1,
        "page_number": 2,
        "section_title": "Title",
        "section_number": "1.1",
        "product": "VPBX API",
    }
    partial = dict(full, section_title="", section_number="")
    metadatas = [full, full, full, partial, full]
    coverage = module._metadata_coverage(metadatas)
    assert 0.79 < coverage < 0.81


def test_load_pages_md_returns_single_page(tmp_path: Path) -> None:
    module = _load_module()
    src = tmp_path / "doc.md"
    src.write_text("Привет, мир", encoding="utf-8")
    import logging

    pages = module.load_pages(src, logging.getLogger("test"))
    assert pages == [(1, "Привет, мир")]


def test_load_product_map_merges_yaml_overrides(tmp_path: Path) -> None:
    module = _load_module()
    config = tmp_path / "products.yaml"
    config.write_text(
        "prefixes:\n  click2call: \"Click2Call Pro\"\n  custom_prefix: \"Custom Product\"\n",
        encoding="utf-8",
    )
    mapping = module.load_product_map(config_path=config)
    assert mapping["click2call"] == "Click2Call Pro"
    assert mapping["custom_prefix"] == "Custom Product"
    # Built-in fallbacks should still be present for keys not overridden.
    assert mapping["sip_trunk"] == "SIP Trunk"


# ----------------------------------------------------------------------- #
# Section Propagation (issue #90) — metadata inheritance, hierarchical
# reset, page-distance safety fallback and ``section_inherited`` flag.
# ----------------------------------------------------------------------- #


def test_section_depth_counts_dotted_parts() -> None:
    module = _load_module()
    assert module.section_depth("") == 0
    assert module.section_depth("5") == 1
    assert module.section_depth("5.1") == 2
    assert module.section_depth("5.1.3") == 3
    assert module.section_depth("5.1.3.4.2") == 5


def test_propagate_section_inherits_when_chunk_has_no_heading() -> None:
    module = _load_module()
    state = module.SectionState()
    # First chunk carries the heading and seeds the state.
    n1, t1, inh1 = module.propagate_section(
        state, "4.2 Подключение коннектора Битрикс24\nТекст ниже.", page_number=12
    )
    assert (n1, t1, inh1) == ("4.2", "Подключение коннектора Битрикс24", False)
    # Second chunk on the same page has no heading — must inherit.
    n2, t2, inh2 = module.propagate_section(
        state, "Просто продолжение раздела без заголовка.", page_number=12
    )
    assert (n2, t2, inh2) == ("4.2", "Подключение коннектора Битрикс24", True)


def test_propagate_section_resets_on_same_level_sibling() -> None:
    module = _load_module()
    state = module.SectionState()
    module.propagate_section(state, "5.1 Первый раздел", page_number=3)
    n, t, inh = module.propagate_section(state, "5.2 Второй раздел", page_number=4)
    assert n == "5.2"
    assert "Второй" in t
    assert inh is False
    # State must now reflect the sibling, not the previous heading.
    assert state.section_number == "5.2"
    assert state.depth == 2


def test_propagate_section_handles_deeper_subsection() -> None:
    module = _load_module()
    state = module.SectionState()
    module.propagate_section(state, "5.1 Раздел", page_number=2)
    n, t, inh = module.propagate_section(state, "5.1.3 Подраздел", page_number=2)
    assert n == "5.1.3"
    assert state.depth == 3
    assert inh is False


def test_propagate_section_safety_resets_after_page_gap() -> None:
    module = _load_module()
    state = module.SectionState()
    module.propagate_section(state, "5.1 Раздел", page_number=2)
    # Many pages later, still no heading — safety reset must fire.
    n, t, inh = module.propagate_section(
        state, "Просто текст без заголовка.", page_number=20, max_page_distance=6
    )
    assert (n, t, inh) == ("", "", False)
    assert state.is_empty()


def test_propagate_section_within_distance_keeps_inheritance() -> None:
    module = _load_module()
    state = module.SectionState()
    module.propagate_section(state, "5.1 Раздел", page_number=2)
    n, t, inh = module.propagate_section(
        state, "Продолжение без заголовка.", page_number=5, max_page_distance=6
    )
    assert n == "5.1"
    assert inh is True


def test_propagate_section_returns_empty_when_state_unseeded() -> None:
    module = _load_module()
    state = module.SectionState()
    n, t, inh = module.propagate_section(state, "Текст без заголовка.", page_number=1)
    assert (n, t, inh) == ("", "", False)


def test_build_chunk_metadata_emits_section_inherited_flag() -> None:
    module = _load_module()
    state = module.SectionState()
    first = module.build_chunk_metadata(
        source="MangoOffice_VPBX_API_v1.9.pdf",
        chunk_idx=0,
        page_number=12,
        text="4.2 Подключение коннектора Битрикс24\nТекст.",
        state=state,
    )
    second = module.build_chunk_metadata(
        source="MangoOffice_VPBX_API_v1.9.pdf",
        chunk_idx=1,
        page_number=12,
        text="Продолжение раздела без заголовка.",
        state=state,
    )
    assert first["section_inherited"] is False
    assert first["section_number"] == "4.2"
    assert second["section_inherited"] is True
    assert second["section_number"] == "4.2"
    assert "Битрикс24" in second["section_title"]


def test_build_chunk_metadata_without_state_is_backward_compatible() -> None:
    module = _load_module()
    meta = module.build_chunk_metadata(
        source="MangoOffice_VPBX_API_v1.9.pdf",
        chunk_idx=7,
        page_number=12,
        text="4.2 Подключение коннектора Битрикс24\nКонтекст ниже.",
    )
    # Legacy path still works and emits the audit flag as False.
    assert meta["section_number"] == "4.2"
    assert meta["section_inherited"] is False


def test_section_state_does_not_leak_across_documents() -> None:
    """Each file in the indexer must instantiate its own ``SectionState`` to
    prevent the last heading of file A from leaking into file B."""
    module = _load_module()
    state_a = module.SectionState()
    module.build_chunk_metadata(
        source="a.pdf",
        chunk_idx=0,
        page_number=1,
        text="5.1 Заголовок документа A",
        state=state_a,
    )
    # New document → caller MUST allocate a fresh state.
    state_b = module.SectionState()
    meta = module.build_chunk_metadata(
        source="b.pdf",
        chunk_idx=0,
        page_number=1,
        text="Текст без заголовка.",
        state=state_b,
    )
    assert meta["section_number"] == ""
    assert meta["section_inherited"] is False


def test_coverage_improves_with_section_propagation() -> None:
    """End-to-end sanity check: a long section split across many chunks
    achieves much higher coverage with propagation than without."""
    module = _load_module()
    long_section_chunks = [
        ("4.2 Подключение коннектора Битрикс24\nВведение в раздел.", 12),
        ("Продолжение раздела, без заголовка в самом чанке.", 12),
        ("Ещё один абзац того же раздела на следующей странице.", 13),
        ("Финальный абзац раздела перед следующим заголовком.", 14),
    ]

    # ``_metadata_coverage`` treats ``chunk_idx=0`` as missing (it counts
    # zero-valued ints as empty), so start from 1 to isolate the section
    # propagation effect that this test is really about.
    legacy_metadatas = [
        module.build_chunk_metadata(
            source="doc.pdf", chunk_idx=i + 1, page_number=p, text=t
        )
        for i, (t, p) in enumerate(long_section_chunks)
    ]
    legacy_cov = module._metadata_coverage(legacy_metadatas)

    state = module.SectionState()
    inherited_metadatas = [
        module.build_chunk_metadata(
            source="doc.pdf", chunk_idx=i + 1, page_number=p, text=t, state=state
        )
        for i, (t, p) in enumerate(long_section_chunks)
    ]
    inherited_cov = module._metadata_coverage(inherited_metadatas)

    # Without propagation only the first chunk gets a section → 0.25.
    assert legacy_cov == 0.25
    # With propagation every chunk inherits the section → 1.0.
    assert inherited_cov == 1.0
    # Three of the four chunks must be marked as inherited for audit.
    assert sum(1 for m in inherited_metadatas if m["section_inherited"]) == 3


def test_load_config_exposes_metadata_coverage_min_and_inheritance() -> None:
    module = _load_module()
    config = module.load_config()
    assert config.get("metadata_coverage_min") == 0.65
    inheritance = config.get("section_inheritance") or {}
    assert inheritance.get("enabled") is True
    assert int(inheritance.get("max_page_distance", 0)) == 6
