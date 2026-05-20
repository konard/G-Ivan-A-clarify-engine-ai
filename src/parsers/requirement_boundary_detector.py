"""Requirement Atomization & Document Structure Recognition (BL-59).

Post-parsing layer that takes raw candidate blocks produced by
:class:`~src.parsers.docx_parser.DocxParser` or
:class:`~src.parsers.excel_parser.ExcelParser` and applies a rule-based
boundary detection:

* recognise numbered section headings (``7.2 Функциональные требования``);
* propagate structural context (``section_number``, ``section_title``,
  ``parent_id``) into descendant atomic requirements;
* detect cross-references in the body text (``см. п. 7.4``) and store them
  in the locator;
* merge orphan continuation fragments back into the requirement they belong
  to;
* drop heading-only blocks from the final output (they carry context but are
  not themselves requirements).

The detector preserves the original locator keys, so backward compatibility
with :class:`~src.exporters.ExportRouter` and :mod:`src.pipeline` is
guaranteed. New keys (``section_number``, ``section_title``, ``parent_id``,
``cross_refs``, ``block_type``, ``span``, ``llm_validated``) are added only
when the corresponding structural information is recognised.

See ``docs/research/2026-05-20_bl-59_requirement-parsing_v1.md`` for the
design rationale, supported strategies and metrics.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default configuration (mirrors configs/parsing_config.yaml::parsing)
# ---------------------------------------------------------------------------

DEFAULT_STRATEGY = "naive"  # safe default when ``parsing`` section is absent
DEFAULT_MIN_REQUIREMENT_LENGTH = 50
DEFAULT_MAX_HEADING_LENGTH = 80

DEFAULT_REQUIREMENT_VERBS: Sequence[str] = (
    "должен",
    "должны",
    "должна",
    "должно",
    "обеспеч",
    "поддерж",
    "предостав",
    "позвол",
    "иметь",
    "выполн",
    "автоматич",
    "реализ",
)

DEFAULT_SECTION_NUMBER_PATTERN = r"^(\d+(?:\.\d+)*)\.?\s+(.+)"

DEFAULT_CROSS_REF_PATTERNS: Sequence[str] = (
    r"см\.?\s*(?:п\.?\s*|пункт\s*|раздел\s*)?(\d+(?:\.\d+)+)",
    r"согласно\s*(?:п\.?\s*|пункту\s*|разделу\s*)?(\d+(?:\.\d+)*)",
    r"в\s*соответствии\s*с\s*(?:п\.?\s*|пунктом\s*|разделом\s*)?(\d+(?:\.\d+)*)",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class _SectionContext:
    """Tracking state for a currently active section heading."""

    number: str
    title: str
    parent_id: Optional[int]
    path: List[str] = field(default_factory=list)  # hierarchical breadcrumb


@dataclass
class _Classification:
    """Result of classifying a single raw block."""

    block_type: str  # heading | requirement | list_item | continuation
    section_number: Optional[str] = None
    section_title: Optional[str] = None


# ---------------------------------------------------------------------------
# Detector implementation
# ---------------------------------------------------------------------------


class RequirementBoundaryDetector:
    """Apply structural boundary detection to raw parser candidates.

    Three strategies are supported (see ``parsing.strategy`` in
    ``configs/parsing_config.yaml``):

    ``naive``
        Pass-through. The detector only re-numbers ``id`` fields to keep the
        contract intact; the locator is not enriched. Useful for CI baseline
        and as an emergency rollback.

    ``structural``
        Rule-based: heading detection via the configured section-number
        pattern, requirement classification via the verb list, continuation
        merge for orphan fragments shorter than ``min_requirement_length``,
        cross-reference extraction. Deterministic, CPU-only, no external
        dependencies.

    ``hybrid``
        ``structural`` plus an optional LLM boundary validation pass
        (toggle ``use_llm_boundary_check``). When the toggle is ``False``
        the strategy behaves identically to ``structural``. The LLM
        validator is currently a stub — it documents the contract for the
        upcoming Layer 2 implementation without forcing an Ollama
        dependency on CI.
    """

    SUPPORTED_STRATEGIES = ("naive", "structural", "hybrid")

    def __init__(self, parsing_config: Optional[Dict[str, Any]] = None) -> None:
        parsing_config = parsing_config or {}
        strategy = str(parsing_config.get("strategy", DEFAULT_STRATEGY)).lower()
        if strategy not in self.SUPPORTED_STRATEGIES:
            logger.warning(
                "Unknown parsing.strategy '%s'; falling back to 'naive'.", strategy
            )
            strategy = "naive"
        self.strategy = strategy

        self.min_requirement_length = int(
            parsing_config.get("min_requirement_length", DEFAULT_MIN_REQUIREMENT_LENGTH)
        )
        self.max_heading_length = int(
            parsing_config.get("max_heading_length", DEFAULT_MAX_HEADING_LENGTH)
        )
        self.preserve_original_fragments = bool(
            parsing_config.get("preserve_original_fragments", True)
        )

        self.use_llm_boundary_check = bool(
            parsing_config.get("use_llm_boundary_check", False)
        )
        self.llm_model = str(parsing_config.get("llm_model", "qwen2.5:7b"))
        self.llm_timeout_seconds = int(parsing_config.get("llm_timeout_seconds", 10))
        self.llm_total_timeout_seconds = int(
            parsing_config.get("llm_total_timeout_seconds", 30)
        )

        verbs = parsing_config.get("requirement_verbs") or list(
            DEFAULT_REQUIREMENT_VERBS
        )
        self.requirement_verbs = tuple(str(verb).lower() for verb in verbs)

        section_pattern = str(
            parsing_config.get("section_number_pattern", DEFAULT_SECTION_NUMBER_PATTERN)
        )
        self._section_re = re.compile(section_pattern)

        cross_ref_patterns = parsing_config.get("cross_ref_patterns") or list(
            DEFAULT_CROSS_REF_PATTERNS
        )
        self._cross_ref_res = [
            re.compile(pattern, re.IGNORECASE) for pattern in cross_ref_patterns
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refine(self, raw_blocks: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Refine raw candidate blocks into atomic requirements.

        Args:
            raw_blocks: Output of :meth:`BaseParser.load_requirements`. Each
                item is a dict with ``id``, ``text`` and ``locator`` keys.

        Returns:
            A new list of dicts with the same shape. ``locator`` is enriched
            with optional structural keys when the corresponding context is
            recognised. ``id`` is re-numbered contiguously to keep the
            downstream contract intact.
        """
        if not raw_blocks:
            return []

        if self.strategy == "naive":
            return self._naive(raw_blocks)

        refined = self._structural(raw_blocks)
        if self.strategy == "hybrid" and self.use_llm_boundary_check:
            refined = self._llm_validate(refined)
        return refined

    # ------------------------------------------------------------------
    # Strategy: naive (backward compatibility)
    # ------------------------------------------------------------------

    @staticmethod
    def _naive(raw_blocks: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for block in raw_blocks:
            item = {
                "id": len(result) + 1,
                "text": block.get("text", ""),
                "locator": dict(block.get("locator") or {}),
            }
            result.append(item)
        return result

    # ------------------------------------------------------------------
    # Strategy: structural (rule-based)
    # ------------------------------------------------------------------

    def _structural(
        self, raw_blocks: Sequence[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        classifications = [self._classify(block) for block in raw_blocks]

        # First pass: assemble heading map so that downstream blocks can
        # reference a stable ``parent_id`` (the id of the heading block in
        # the *raw* input list).
        section_stack: List[_SectionContext] = []
        current_section: Optional[_SectionContext] = None
        heading_anchor: Dict[int, _SectionContext] = {}
        for index, (block, classification) in enumerate(
            zip(raw_blocks, classifications)
        ):
            if classification.block_type != "heading":
                continue
            number = classification.section_number or ""
            depth = number.count(".") + 1 if number else 1
            while section_stack and section_stack[-1].number.count(".") + 1 >= depth:
                section_stack.pop()
            parent_id = section_stack[-1].parent_id if section_stack else None
            ctx = _SectionContext(
                number=number,
                title=str(block.get("text", "")).strip(),
                parent_id=int(block.get("id") or (index + 1)),
                path=[s.number for s in section_stack if s.number] + ([number] if number else []),
            )
            section_stack.append(ctx)
            heading_anchor[index] = ctx
            current_section = ctx

        # Second pass: produce refined requirements, propagating context.
        section_stack.clear()
        current_section = None
        refined: List[Dict[str, Any]] = []

        for index, (block, classification) in enumerate(
            zip(raw_blocks, classifications)
        ):
            if classification.block_type == "heading":
                ctx = heading_anchor.get(index)
                if ctx is not None:
                    depth = ctx.number.count(".") + 1 if ctx.number else 1
                    while (
                        section_stack
                        and section_stack[-1].number.count(".") + 1 >= depth
                    ):
                        section_stack.pop()
                    section_stack.append(ctx)
                    current_section = ctx
                # Headings carry context but are not emitted as requirements.
                continue

            text = str(block.get("text", "")).strip()
            if not text:
                continue

            locator = dict(block.get("locator") or {})

            if (
                classification.block_type == "continuation"
                and refined
                and self._can_merge_continuation(refined[-1], block)
            ):
                self._merge_continuation(refined[-1], block, text)
                continue

            enriched_locator = self._enrich_locator(
                locator,
                block_type=classification.block_type,
                section=current_section,
                section_number_override=classification.section_number,
                section_title_override=classification.section_title,
                text=text,
                source_block_id=block.get("id"),
            )

            refined.append(
                {
                    "id": len(refined) + 1,
                    "text": text,
                    "locator": enriched_locator,
                }
            )

        return refined

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def _classify(self, block: Dict[str, Any]) -> _Classification:
        text = str(block.get("text", "")).strip()
        if not text:
            return _Classification(block_type="continuation")

        section_match = self._section_re.match(text)
        has_verb = self._has_requirement_verb(text)

        if section_match:
            number = section_match.group(1)
            remainder = section_match.group(2).strip()
            # Heading heuristic: short remainder, no requirement verb,
            # no terminal sentence punctuation.
            is_short = len(remainder) <= self.max_heading_length
            ends_like_sentence = remainder.endswith((".", ";", ":"))
            if is_short and not has_verb and not ends_like_sentence:
                return _Classification(
                    block_type="heading",
                    section_number=number,
                    section_title=remainder,
                )
            return _Classification(
                block_type="requirement",
                section_number=number,
                section_title=None,
            )

        if has_verb and len(text) >= self.min_requirement_length:
            return _Classification(block_type="requirement")

        # All-caps short line → treat as heading (e.g. ``ОБЩИЕ ТРЕБОВАНИЯ``).
        upper_letters = [c for c in text if c.isalpha()]
        if (
            upper_letters
            and all(c.isupper() for c in upper_letters)
            and 5 <= len(text) <= self.max_heading_length
        ):
            return _Classification(block_type="heading", section_title=text)

        if len(text) < self.min_requirement_length:
            return _Classification(block_type="continuation")

        return _Classification(block_type="requirement")

    def _has_requirement_verb(self, text: str) -> bool:
        lowered = text.lower()
        return any(verb in lowered for verb in self.requirement_verbs)

    # ------------------------------------------------------------------
    # Locator enrichment
    # ------------------------------------------------------------------

    def _enrich_locator(
        self,
        locator: Dict[str, Any],
        *,
        block_type: str,
        section: Optional[_SectionContext],
        section_number_override: Optional[str],
        section_title_override: Optional[str],
        text: str,
        source_block_id: Any,
    ) -> Dict[str, Any]:
        enriched: Dict[str, Any] = dict(locator)
        enriched["block_type"] = block_type

        section_number = section_number_override or (
            section.number if section else None
        )
        if section_number:
            enriched["section_number"] = section_number

        section_title = section_title_override or (
            section.title if section else None
        )
        if section_title:
            enriched["section_title"] = section_title

        if section and section.parent_id is not None:
            enriched["parent_id"] = section.parent_id

        cross_refs = self._extract_cross_refs(text)
        if cross_refs:
            enriched["cross_refs"] = cross_refs

        if self.preserve_original_fragments:
            span_token = self._span_token(locator, source_block_id)
            if span_token:
                enriched["span"] = [span_token]

        return enriched

    def _extract_cross_refs(self, text: str) -> List[str]:
        seen: List[str] = []
        for regex in self._cross_ref_res:
            for match in regex.finditer(text):
                ref = match.group(1)
                if ref and ref not in seen:
                    seen.append(ref)
        return seen

    @staticmethod
    def _span_token(locator: Dict[str, Any], source_block_id: Any) -> str:
        loc_type = locator.get("type")
        if loc_type == "paragraph":
            return f"para{locator.get('index')}"
        if loc_type == "table":
            return (
                f"table{locator.get('table')}"
                f"-r{locator.get('row')}"
                f"-c{locator.get('col')}"
                f"-p{locator.get('paragraph')}"
            )
        if loc_type == "cell":
            return (
                f"sheet:{locator.get('sheet_name')}"
                f"-r{locator.get('row')}"
                f"-c{locator.get('column')}"
            )
        if source_block_id is not None:
            return f"block{source_block_id}"
        return ""

    # ------------------------------------------------------------------
    # Continuation merge
    # ------------------------------------------------------------------

    def _can_merge_continuation(
        self,
        previous: Dict[str, Any],
        block: Dict[str, Any],
    ) -> bool:
        prev_locator = previous.get("locator") or {}
        block_locator = block.get("locator") or {}
        if prev_locator.get("type") != block_locator.get("type"):
            return False
        if prev_locator.get("block_type") not in {
            "requirement",
            "list_item",
        }:
            return False

        if prev_locator.get("type") == "table":
            if (
                prev_locator.get("table") != block_locator.get("table")
                or prev_locator.get("row") != block_locator.get("row")
                or prev_locator.get("col") != block_locator.get("col")
            ):
                return False

        if prev_locator.get("type") == "cell":
            if (
                prev_locator.get("sheet_name") != block_locator.get("sheet_name")
                or prev_locator.get("column") != block_locator.get("column")
                or prev_locator.get("row") != block_locator.get("row")
            ):
                return False

        return True

    def _merge_continuation(
        self,
        previous: Dict[str, Any],
        block: Dict[str, Any],
        text: str,
    ) -> None:
        previous["text"] = f"{previous['text'].rstrip()} {text}".strip()
        locator = previous.get("locator") or {}
        cross_refs = list(locator.get("cross_refs") or [])
        for ref in self._extract_cross_refs(text):
            if ref not in cross_refs:
                cross_refs.append(ref)
        if cross_refs:
            locator["cross_refs"] = cross_refs

        if self.preserve_original_fragments:
            span = list(locator.get("span") or [])
            token = self._span_token(block.get("locator") or {}, block.get("id"))
            if token and token not in span:
                span.append(token)
            if span:
                locator["span"] = span

        previous["locator"] = locator

    # ------------------------------------------------------------------
    # Optional Layer 2 — LLM boundary validation (stub).
    # ------------------------------------------------------------------

    def _llm_validate(
        self, refined: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """LLM boundary validation stub.

        The real Layer 2 implementation lives behind the toggle
        ``parsing.use_llm_boundary_check``. The MVP ships the stub so the
        ``hybrid`` strategy degrades to pure ``structural`` until a local
        Ollama instance is wired up. When the toggle is enabled but no LLM
        client is available, the detector logs a warning and returns the
        ``structural`` result without modifications.

        See ``docs/research/2026-05-20_bl-59_requirement-parsing_v1.md`` §5
        for the prompt contract and §4.6 for the validation pipeline.
        """
        logger.warning(
            "LLM boundary validation is enabled but the Ollama client is not "
            "wired up yet (BL-59 Step 2). Returning structural result; see "
            "docs/research/2026-05-20_bl-59_requirement-parsing_v1.md §4.6."
        )
        return refined
