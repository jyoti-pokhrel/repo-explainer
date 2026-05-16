import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

from backend.app.ingestion.models import Chunk
from backend.app.retrieval.store import get_chunks

load_dotenv()

MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
INDEX_NAME = "codesage"
DIMENSION = 768

_model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
_pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])


def _get_index():
    if INDEX_NAME in _pc.list_indexes().names():
        _pc.delete_index(INDEX_NAME)

    _pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    return _pc.Index(INDEX_NAME)


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
    index = _get_index()
    enriched = [_enrich_chunk(c) for c in chunks]
    embeddings = _model.encode(enriched, show_progress_bar=False).tolist()

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


def search_dense(query: str, job_id: str, top_k: int = 20) -> list[tuple[Chunk, float]]:
    index = _get_index()
    query_embedding = _model.encode([query]).tolist()[0]

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=job_id,
    )

    stored_chunks = {c.file_path: c for c in get_chunks(job_id)}
    chunks_with_scores = []

    for match in results.matches:
        meta = match.metadata
        file_path = meta.get("file_path", "")
        start_line = meta.get("start_line", 0)
        end_line = meta.get("end_line", 0)

        full_chunk = None
        for c in get_chunks(job_id):
            if c.file_path == file_path and c.start_line == start_line and c.end_line == end_line:
                full_chunk = c
                break

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
