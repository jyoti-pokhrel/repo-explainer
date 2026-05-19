import os
from typing import TYPE_CHECKING

from pinecone import Pinecone, ServerlessSpec

from backend.app.ingestion.models import Chunk
from backend.app.storage import get_chunks_db

if TYPE_CHECKING:
    import torch
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
INDEX_NAME = "codesage"
DIMENSION = 384

_model = None
_pc = None
_device = None
_indexes: dict[str, object] = {}


def _get_device():
    global _device
    if _device is None:
        import torch
        _device = "cuda" if torch.cuda.is_available() else "cpu"
    return _device


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME, device=_get_device())
    return _model


def _get_pc():
    global _pc
    if _pc is None:
        api_key = os.environ.get("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY environment variable is required")
        _pc = Pinecone(api_key=api_key)
    return _pc


def _clear_gpu():
    if _get_device() == "cuda":
        import torch
        torch.cuda.empty_cache()


def _get_or_create_index(job_id: str):
    if job_id in _indexes:
        return _indexes[job_id]

    pc = _get_pc()
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    idx = pc.Index(INDEX_NAME)
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
    model = _get_model()

    encode_batch_size = 32
    upsert_batch_size = 100
    global_index = 0

    for i in range(0, len(chunks), encode_batch_size):
        batch = chunks[i : i + encode_batch_size]
        enriched = [_enrich_chunk(c) for c in batch]
        embeddings = model.encode(
            enriched,
            show_progress_bar=False,
            batch_size=encode_batch_size,
            normalize_embeddings=True,
        ).tolist()

        vectors = []
        for j, chunk in enumerate(batch):
            vectors.append({
                "id": f"{job_id}-{global_index}",
                "values": embeddings[j],
                "metadata": {
                    "job_id": job_id,
                    "file_path": chunk.file_path,
                    "chunk_type": chunk.chunk_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "name": chunk.name or "",
                    "language": chunk.language,
                    "index": global_index,
                },
            })
            global_index += 1

        for k in range(0, len(vectors), upsert_batch_size):
            index.upsert(vectors=vectors[k : k + upsert_batch_size], namespace=job_id)

    _clear_gpu()


def search_dense(query: str, job_id: str, top_k: int = 20) -> list[tuple[Chunk, float]]:
    index = _get_or_create_index(job_id)
    model = _get_model()
    query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]

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
