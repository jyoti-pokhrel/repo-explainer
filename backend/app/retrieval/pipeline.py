from backend.app.ingestion.models import Chunk
from backend.app.retrieval.bm25 import BM25Search
from backend.app.retrieval.rrf import reciprocal_rank_fusion
from backend.app.storage import get_chunks_db, store_chunks_db

_bm25_indices: dict[str, BM25Search] = {}


def build_index(job_id: str, chunks: list[Chunk]) -> None:
    from backend.app.retrieval.dense import embed_chunks

    store_chunks_db(job_id, chunks)

    bm25 = BM25Search()
    bm25.build(chunks)
    _bm25_indices[job_id] = bm25

    embed_chunks(chunks, job_id)


def query_repo(job_id: str, question: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
    from backend.app.retrieval.dense import search_dense

    bm25 = _bm25_indices.get(job_id)
    if not bm25:
        bm25 = _rebuild_bm25(job_id)
        if not bm25:
            return []

    bm25_results = bm25.search(question, top_k=10)
    dense_results = search_dense(question, job_id, top_k=10)

    fused = reciprocal_rank_fusion(bm25_results, dense_results, top_k=top_k)

    full_chunks = []
    stored = get_chunks_db(job_id)
    stored_lookup = {(c.file_path, c.start_line): c for c in stored}

    for chunk, score in fused:
        key = (chunk.file_path, chunk.start_line)
        if key in stored_lookup:
            full_chunks.append((stored_lookup[key], score))
        else:
            full_chunks.append((chunk, score))

    return full_chunks


def _rebuild_bm25(job_id: str) -> BM25Search | None:
    chunks = get_chunks_db(job_id)
    if not chunks:
        return None

    bm25 = BM25Search()
    bm25.build(chunks)
    _bm25_indices[job_id] = bm25
    return bm25
