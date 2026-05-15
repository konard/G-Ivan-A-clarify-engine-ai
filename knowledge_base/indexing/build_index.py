#!/usr/bin/env python3
"""Knowledge-base indexer (FR-02).

Reads documents from ``knowledge_base/sources/``, chunks them, vectorises
with the embedding model defined in ``configs/embedding_config.yaml``
(``model_name``, ``chunk_size``, ``chunk_overlap``) and writes the chunks to
ChromaDB. Every indexed file is recorded in
``knowledge_base/metadata/source_registry.csv`` with its SHA-256 hash.

Registry schema (FR-02, CONCEPT §4 / NFR-07):
    ``filename, version, sha256_hash, indexed_date, status, coverage``
"""

from __future__ import annotations

import csv
import hashlib
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "embedding_config.yaml"
SOURCES_DIR = BASE_DIR / "knowledge_base" / "sources"
METADATA_DIR = BASE_DIR / "knowledge_base" / "metadata"
REGISTRY_FILE = METADATA_DIR / "source_registry.csv"

REGISTRY_FIELDS: List[str] = [
    "filename",
    "version",
    "sha256_hash",
    "indexed_date",
    "status",
    "coverage",
]
DEFAULT_VERSION = "1.0"
DEFAULT_COVERAGE = "Medium"


def setup_logging(run_id: str) -> logging.Logger:
    """Configure a JSON-style logger that carries ``run_id`` on every record."""
    logger = logging.getLogger("kb_indexer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            '{"ts": "%(asctime)s", "level": "%(levelname)s", '
            f'"run_id": "{run_id}", "event": "%(message)s"}}'
        )
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def load_config(config_path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load chunking & embedding parameters from ``configs/embedding_config.yaml``.

    Returns sensible defaults if the file is missing so the script remains
    runnable in CI without the config tree.
    """
    if not config_path.exists():
        return {
            "model_name": "BAAI/bge-m3",
            "chunk_size": 250,
            "chunk_overlap": 50,
            "vector_store": {
                "persist_directory": str(BASE_DIR / "chroma_data"),
                "collection_name": "mango_kb",
            },
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_file_hash(file_path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of ``file_path``."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_text(file_path: Path) -> Optional[str]:
    try:
        suffix = file_path.suffix.lower()
        if suffix in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader  # type: ignore
            except ImportError:
                logging.warning("pypdf missing, skip PDF: %s", file_path)
                return None
            reader = PdfReader(str(file_path))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        return None
    except Exception as exc:  # noqa: BLE001
        logging.error("Error reading %s: %s", file_path, exc)
        return None


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Word-window chunker. Returns ``[]`` for empty input."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        stripped = text.strip()
        return [stripped] if stripped else []

    chunks: List[str] = []
    step = max(1, chunk_size - chunk_overlap)
    for start in range(0, len(words), step):
        end = start + chunk_size
        piece = " ".join(words[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end >= len(words):
            break
    return chunks


def _read_registry() -> Dict[str, Dict[str, str]]:
    if not REGISTRY_FILE.exists():
        return {}
    with open(REGISTRY_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["filename"]: row for row in reader if row.get("filename")}


def _write_registry(rows: List[Dict[str, str]]) -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    normalised: List[Dict[str, str]] = []
    for row in rows:
        normalised.append({field: row.get(field, "") for field in REGISTRY_FIELDS})
    with open(REGISTRY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRY_FIELDS)
        writer.writeheader()
        writer.writerows(normalised)


def update_registry(
    filename: str,
    sha256_hash: str,
    status: str,
    *,
    version: Optional[str] = None,
    coverage: Optional[str] = None,
) -> None:
    """Insert or update the row for ``filename`` in ``source_registry.csv``.

    Preserves existing ``version`` and ``coverage`` if the entry already
    existed; falls back to ``DEFAULT_VERSION`` / ``DEFAULT_COVERAGE`` otherwise.
    """
    registry = _read_registry()
    existing = registry.get(filename, {})
    registry[filename] = {
        "filename": filename,
        "version": version or existing.get("version") or DEFAULT_VERSION,
        "sha256_hash": sha256_hash,
        "indexed_date": datetime.now().strftime("%Y-%m-%d"),
        "status": status,
        "coverage": coverage or existing.get("coverage") or DEFAULT_COVERAGE,
    }
    _write_registry(list(registry.values()))


def _vector_store_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    vs = config.get("vector_store") or {}
    return {
        "persist_directory": vs.get("persist_directory") or str(BASE_DIR / "chroma_data"),
        "collection_name": vs.get("collection_name") or "mango_kb",
    }


def main() -> int:
    run_id = uuid.uuid4().hex
    logger = setup_logging(run_id)
    logger.info("Starting KB Indexing")

    config = load_config()
    model_name = config.get("model_name", "BAAI/bge-m3")
    chunk_size = int(config.get("chunk_size", 250))
    chunk_overlap = int(config.get("chunk_overlap", 50))
    store = _vector_store_settings(config)

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        import chromadb  # type: ignore
    except ImportError as exc:
        logger.error(
            "Required indexing dependency missing: %s. Install sentence-transformers and chromadb.",
            exc,
        )
        return 1

    if not SOURCES_DIR.exists():
        logger.error("Sources dir not found: %s", SOURCES_DIR)
        return 1

    files = [
        f for f in sorted(SOURCES_DIR.glob("*"))
        if f.is_file() and f.suffix.lower() in {".txt", ".md", ".pdf"}
    ]
    if not files:
        logger.warning("No indexable files found in %s", SOURCES_DIR)
        return 0

    logger.info("Loading model: %s", model_name)
    model = SentenceTransformer(model_name)

    client = chromadb.PersistentClient(path=store["persist_directory"])
    collection = client.get_or_create_collection(name=store["collection_name"])

    all_chunks: List[str] = []
    all_ids: List[str] = []
    all_metadatas: List[Dict[str, Any]] = []

    for file_path in files:
        logger.info("Processing %s", file_path.name)
        sha256 = get_file_hash(file_path)
        text = load_text(file_path)
        if not text:
            update_registry(file_path.name, sha256, status="Skipped")
            continue

        chunks = chunk_text(text, chunk_size, chunk_overlap)
        logger.info("chunks=%d file=%s", len(chunks), file_path.name)

        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{file_path.stem}_{i}")
            all_metadatas.append(
                {"source": file_path.name, "chunk_idx": i, "sha256_hash": sha256}
            )

        update_registry(file_path.name, sha256, status="Indexed")

    if not all_chunks:
        logger.warning("No data to save")
        return 0

    logger.info("Vectorising %d chunks", len(all_chunks))
    embeddings = model.encode(all_chunks, show_progress_bar=True).tolist()

    batch_size = 100
    for i in range(0, len(all_ids), batch_size):
        collection.add(
            ids=all_ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            metadatas=all_metadatas[i : i + batch_size],
            documents=all_chunks[i : i + batch_size],
        )
    logger.info("Indexing complete: collection=%s", store["collection_name"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
