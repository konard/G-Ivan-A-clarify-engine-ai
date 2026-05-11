"""Skeleton of the knowledge-base indexing pipeline.

Run from repo root:

    python3 knowledge_base/indexing/build_index.py

For now this is a placeholder: it logs the planned steps so the rest of the
pipeline can be wired up incrementally (parsing sources, chunking, embedding
with BGE-M3 and persisting to ChromaDB).
"""
from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_knowledge_base() -> None:
    logger.info("Starting KB indexing...")
    # TODO: Implement parsing of sources/
    # TODO: Implement chunking (250 tokens, overlap 50)
    # TODO: Implement embedding (BGE-M3)
    # TODO: Save to ChromaDB
    sources_dir = Path(__file__).resolve().parents[1] / "sources"
    if sources_dir.exists():
        files = sorted(p.name for p in sources_dir.iterdir() if p.is_file() and p.name != ".gitkeep")
        logger.info("Discovered %d source file(s) in %s: %s", len(files), sources_dir, files)
    else:
        logger.warning("Sources directory %s does not exist yet.", sources_dir)
    logger.info("KB indexing completed.")


if __name__ == "__main__":
    build_knowledge_base()
