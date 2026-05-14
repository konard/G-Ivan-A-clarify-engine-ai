#!/usr/bin/env python3
"""
Модуль индексации Базы Знаний (Knowledge Base Indexer).
Читает документы, чанкует, векторизует (BGE-M3) и сохраняет в ChromaDB.
"""

import os
import sys
import csv
import uuid
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml
from sentence_transformers import SentenceTransformer
import chromadb

# Пути
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "configs" / "embedding_config.yaml"
SOURCES_DIR = BASE_DIR / "knowledge_base" / "sources"
METADATA_DIR = BASE_DIR / "knowledge_base" / "metadata"
REGISTRY_FILE = METADATA_DIR / "source_registry.csv"

def setup_logging(run_id: str) -> logging.Logger:
    logger = logging.getLogger("kb_indexer")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    # JSON формат
    formatter = logging.Formatter(
        '{"run_id": "%(run_id)s", "time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}'
    )
    formatter.run_id = run_id # type: ignore
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        # Дефолтный конфиг если файл не найден
        return {
            "model": "BAAI/bge-m3",
            "chunk_size": 250,
            "overlap": 50,
            "persist_directory": str(BASE_DIR / "chroma_data")
        }
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_file_hash(file_path: Path) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_text(file_path: Path) -> Optional[str]:
    try:
        if file_path.suffix.lower() in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif file_path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                return "\n".join([page.extract_text() or "" for page in reader.pages])
            except ImportError:
                logging.warning(f"pypdf missing, skip PDF: {file_path}")
                return None
        return None
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return None

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    words = text.split()
    if len(words) <= chunk_size:
        return [text.strip()] if text.strip() else []
    
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def update_registry(filename: str, status: str, run_id: str):
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    updated = False
    
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["filename"] == filename:
                    row["status"] = status
                    row["indexed_date"] = datetime.now().isoformat()
                    row["run_id"] = run_id
                    updated = True
                rows.append(row)
    
    if not updated:
        rows.append({
            "filename": filename,
            "indexed_date": datetime.now().isoformat(),
            "status": status,
            "run_id": run_id,
            "hash": get_file_hash(SOURCES_DIR / filename) if (SOURCES_DIR / filename).exists() else ""
        })
    
    with open(REGISTRY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "indexed_date", "status", "run_id", "hash"])
        writer.writeheader()
        writer.writerows(rows)

def main():
    run_id = str(uuid.uuid4())
    logger = setup_logging(run_id)
    logger.info("Starting KB Indexing")
    
    try:
        config = load_config()
        model_name = config.get("model", "BAAI/bge-m3")
        chunk_size = config.get("chunk_size", 250)
        overlap = config.get("overlap", 50)
        persist_dir = config.get("persist_directory", str(BASE_DIR / "chroma_data"))
        
        logger.info(f"Loading model: {model_name}")
        model = SentenceTransformer(model_name)
        
        if not SOURCES_DIR.exists():
            logger.error(f"Sources dir not found: {SOURCES_DIR}")
            return
            
        files = [f for f in SOURCES_DIR.glob("*") if f.suffix.lower() in [".txt", ".md", ".pdf"]]
        if not files:
            logger.warning("No files found")
            return
            
        logger.info(f"Found {len(files)} files")
        
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_or_create_collection(name="knowledge_base")
        
        all_chunks, all_ids, all_metadatas = [], [], []
        
        for file_path in files:
            logger.info(f"Processing: {file_path.name}")
            text = load_text(file_path)
            if not text:
                update_registry(file_path.name, "Skipped", run_id)
                continue
            
            chunks = chunk_text(text, chunk_size, overlap)
            logger.info(f"Chunks: {len(chunks)}")
            
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_ids.append(f"{file_path.stem}_{i}")
                all_metadatas.append({"source": file_path.name, "chunk_idx": i})
            
            update_registry(file_path.name, "Indexed", run_id)
        
        if all_chunks:
            logger.info("Vectorizing...")
            embeddings = model.encode(all_chunks, show_progress_bar=True).tolist()
            
            batch_size = 100
            for i in range(0, len(all_ids), batch_size):
                collection.add(
                    ids=all_ids[i:i+batch_size],
                    embeddings=embeddings[i:i+batch_size],
                    metadatas=all_metadatas[i:i+batch_size],
                    documents=all_chunks[i:i+batch_size]
                )
            logger.info("Done.")
        else:
            logger.warning("No data to save")
            
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
