import os
from uuid import uuid4

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

from backend.app.ingestion.models import Chunk

load_dotenv()

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_NAME = "codesage"
DIMENSION = 384

_model = SentenceTransformer(MODEL_NAME)
_pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])


def _get_index():
    if INDEX_NAME not in _pc.list_indexes().names():
        _pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return _pc.Index(INDEX_NAME)


def embed_chunks(chunks: list[Chunk], job_id: str) -> None:
    index = _get_index()
    contents = [c.content for c in chunks]
    embeddings = _model.encode(contents, show_progress_bar=False).tolist()

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
                "content": chunk.content[:500],
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

    chunks_with_scores = []
    for match in results.matches:
        meta = match.metadata
        chunk = Chunk(
            content=meta.get("content", ""),
            file_path=meta.get("file_path", ""),
            chunk_type=meta.get("chunk_type", ""),
            start_line=meta.get("start_line", 0),
            end_line=meta.get("end_line", 0),
            name=meta.get("name") or None,
            language=meta.get("language", ""),
        )
        chunks_with_scores.append((chunk, match.score))

    return chunks_with_scores
