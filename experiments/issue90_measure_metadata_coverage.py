#!/usr/bin/env python3
"""Measure metadata coverage with and without Section Propagation (issue #90).

Loads each KB source PDF once, chunks it, then walks the resulting chunks
twice — once with legacy per-chunk extraction, once with the new stateful
``SectionState`` — and reports:

* legacy coverage (pre-issue-#90 behaviour);
* propagated coverage (issue #90);
* per-field fill rates for ``section_title`` / ``section_number``;
* the inherited-chunk share (``section_inherited=True``);
* a small sample of metadata JSON for the analysis report.

Progress is streamed to stderr per file so the run can be monitored in
real time. Final report is JSON on stdout.

Run::

    python experiments/issue90_measure_metadata_coverage.py [--limit 3] > out.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "knowledge_base" / "indexing" / "build_index.py"
SOURCES_DIR = REPO_ROOT / "knowledge_base" / "sources"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_index_exp", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _per_field_fill(metadatas: List[Dict[str, Any]], key: str) -> float:
    if not metadatas:
        return 0.0
    return sum(1 for m in metadatas if m.get(key)) / len(metadatas)


def _coverage(metadatas: List[Dict[str, Any]], module) -> float:
    if not metadatas:
        return 0.0
    full = 0
    for meta in metadatas:
        if all(meta.get(key) for key in module.REQUIRED_METADATA_KEYS):
            full += 1
    return full / len(metadatas)


def _process_file(
    module,
    file_path: Path,
    *,
    max_page_distance: int,
    logger: logging.Logger,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Chunk ``file_path`` once and produce two metadata lists.

    Returns ``(legacy_metadatas, propagated_metadatas)``.
    """
    pages = module.load_pages(file_path, logger)
    if not pages:
        return [], []

    propagated_state = module.SectionState()
    legacy_metadatas: List[Dict[str, Any]] = []
    propagated_metadatas: List[Dict[str, Any]] = []
    chunk_idx = 0
    for page_number, page_text in pages:
        if not page_text or not page_text.strip():
            continue
        try:
            chunks = module.build_chunks(page_text)
        except RuntimeError as exc:
            logger.error("Tokenizer unavailable: %s", exc)
            return [], []
        for chunk in chunks:
            # +1 sidesteps the ``chunk_idx=0`` quirk of ``_metadata_coverage``
            # (zero-valued ints count as empty).
            common = dict(
                source=file_path.name,
                chunk_idx=chunk_idx + 1,
                page_number=page_number,
                text=chunk,
            )
            legacy_metadatas.append(module.build_chunk_metadata(**common))
            propagated_metadatas.append(
                module.build_chunk_metadata(
                    **common,
                    state=propagated_state,
                    max_page_distance=max_page_distance,
                )
            )
            chunk_idx += 1
    return legacy_metadatas, propagated_metadatas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N files")
    parser.add_argument("--samples", type=int, default=6, help="How many metadata samples to print")
    parser.add_argument("--max-page-distance", type=int, default=6)
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=0.0,
        help="Skip source files larger than this many MB (0 = no limit)",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="File name(s) to skip (may be passed multiple times)",
    )
    parser.add_argument("--out", default="", help="Optional path to write the JSON report")
    args = parser.parse_args()

    module = _load_module()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    logger = logging.getLogger("issue90")

    if not SOURCES_DIR.exists():
        print(f"Sources directory missing: {SOURCES_DIR}", file=sys.stderr)
        return 1

    files = sorted(p for p in SOURCES_DIR.glob("*") if p.is_file())
    if args.skip:
        skip_set = set(args.skip)
        files = [p for p in files if p.name not in skip_set]
    if args.max_file_mb > 0:
        max_bytes = int(args.max_file_mb * 1024 * 1024)
        files = [p for p in files if p.stat().st_size <= max_bytes]
    if args.limit > 0:
        files = files[: args.limit]

    summary_rows: List[Dict[str, Any]] = []
    legacy_all: List[Dict[str, Any]] = []
    propagated_all: List[Dict[str, Any]] = []
    sample_chunks: List[Dict[str, Any]] = []

    for idx, path in enumerate(files, start=1):
        t0 = time.time()
        print(f"[{idx}/{len(files)}] processing {path.name} ...", file=sys.stderr, flush=True)
        legacy, propagated = _process_file(
            module,
            path,
            max_page_distance=args.max_page_distance,
            logger=logger,
        )
        elapsed = time.time() - t0
        legacy_all.extend(legacy)
        propagated_all.extend(propagated)
        row = {
            "file": path.name,
            "chunks": len(propagated),
            "legacy_coverage": _coverage(legacy, module),
            "propagated_coverage": _coverage(propagated, module),
            "legacy_section_title_fill": _per_field_fill(legacy, "section_title"),
            "propagated_section_title_fill": _per_field_fill(propagated, "section_title"),
            "inherited_share": (
                sum(1 for m in propagated if m.get("section_inherited")) / max(1, len(propagated))
            ),
            "elapsed_seconds": round(elapsed, 1),
        }
        summary_rows.append(row)
        print(
            f"    chunks={row['chunks']} "
            f"legacy={row['legacy_coverage']:.4f} "
            f"propagated={row['propagated_coverage']:.4f} "
            f"inherited={row['inherited_share']:.4f} "
            f"({elapsed:.1f}s)",
            file=sys.stderr,
            flush=True,
        )
        if len(sample_chunks) < args.samples and propagated:
            non_inh = next((m for m in propagated if not m["section_inherited"] and m["section_number"]), None)
            inh = next((m for m in propagated if m["section_inherited"]), None)
            if non_inh is not None and len(sample_chunks) < args.samples:
                sample_chunks.append(non_inh)
            if inh is not None and len(sample_chunks) < args.samples:
                sample_chunks.append(inh)

    report = {
        "files_processed": len(files),
        "total_chunks": len(propagated_all),
        "legacy_coverage": _coverage(legacy_all, module),
        "propagated_coverage": _coverage(propagated_all, module),
        "legacy_section_title_fill": _per_field_fill(legacy_all, "section_title"),
        "legacy_section_number_fill": _per_field_fill(legacy_all, "section_number"),
        "propagated_section_title_fill": _per_field_fill(propagated_all, "section_title"),
        "propagated_section_number_fill": _per_field_fill(propagated_all, "section_number"),
        "inherited_share": (
            sum(1 for m in propagated_all if m.get("section_inherited"))
            / max(1, len(propagated_all))
        ),
        "max_page_distance": args.max_page_distance,
        "per_file": summary_rows,
        "samples": sample_chunks,
    }
    blob = json.dumps(report, ensure_ascii=False, indent=2)
    print(blob)
    if args.out:
        Path(args.out).write_text(blob, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
