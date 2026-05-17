import os

import torch
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

from backend.app.ingestion.models import Chunk
from backend.app.storage import get_chunks_db

load_dotenv()

MODEL_NAME = "BAAI/bge-small-en-v1.5"
INDEX_NAME = "codesage"
DIMENSION = 384

_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = SentenceTransformer(MODEL_NAME, device=_device)
_pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

_indexes: dict[str, object] = {}


def _clear_gpu():
    if _device == "cuda":
        torch.cuda.empty_cache()


def _get_or_create_index(job_id: str):
    if job_id in _indexes:
        return _indexes[job_id]

    if INDEX_NAME not in _pc.list_indexes().names():
        _pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    idx = _pc.Index(INDEX_NAME)
    _indexes[job_id] = idx
    return idx


def _enrich_chunk(chunk: Chunk) -> str:
    lines = []
    if chunk.name:
        lines.append(f"{chunk.chunk_type}: {chunk.name}")
    lines.append(f"File: {chunk.file_path}")
    lines.append(f"Language: {chunk.language}")
    lines.append("")
    lines.append(chunk.content)
    return "\n".join(lines)


def embed_chunks(chunks: list[Chunk], job_id: str) -> None:
    index = _get_or_create_index(job_id)
    enriched = [_enrich_chunk(c) for c in chunks]
    embeddings = _model.encode(
        enriched,
        show_progress_bar=False,
        batch_size=32,
        normalize_embeddings=True,
    ).tolist()

    vectors = []
    for i, chunk in enumerate(chunks):
        vectors.append({
            "id": f"{job_id}-{i}",
            "values": embeddings[i],
            "metadata": {
                "job_id": job_id,
                "file_path": chunk.file_path,
                "chunk_type": chunk.chunk_type,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "name": chunk.name or "",
                "language": chunk.language,
                "index": i,
            },
        })

    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i : i + batch_size], namespace=job_id)

    _clear_gpu()


def search_dense(query: str, job_id: str, top_k: int = 20) -> list[tuple[Chunk, float]]:
    index = _get_or_create_index(job_id)
    query_embedding = _model.encode([query], normalize_embeddings=True).tolist()[0]

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=job_id,
    )

    stored = get_chunks_db(job_id)
    stored_lookup = {(c.file_path, c.start_line, c.end_line): c for c in stored}

    chunks_with_scores = []
    for match in results.matches:
        meta = match.metadata
        file_path = meta.get("file_path", "")
        start_line = meta.get("start_line", 0)
        end_line = meta.get("end_line", 0)

        key = (file_path, start_line, end_line)
        full_chunk = stored_lookup.get(key)

        if full_chunk is None:
            full_chunk = Chunk(
                content="",
                file_path=file_path,
                chunk_type=meta.get("chunk_type", ""),
                start_line=start_line,
                end_line=end_line,
                name=meta.get("name") or None,
                language=meta.get("language", ""),
            )

        chunks_with_scores.append((full_chunk, match.score))

    return chunks_with_scores
