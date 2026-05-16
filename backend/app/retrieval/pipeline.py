from backend.app.ingestion.models import Chunk
from backend.app.retrieval.bm25 import BM25Search
from backend.app.retrieval.dense import embed_chunks, search_dense
from backend.app.retrieval.reranker import rerank
from backend.app.retrieval.rrf import reciprocal_rank_fusion
from backend.app.retrieval.store import store_chunks

_bm25_indices: dict[str, BM25Search] = {}


def build_index(job_id: str, chunks: list[Chunk]) -> None:
    store_chunks(job_id, chunks)

    bm25 = BM25Search()
    bm25.build(chunks)
    _bm25_indices[job_id] = bm25

    embed_chunks(chunks, job_id)


def query_repo(job_id: str, question: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
    bm25 = _bm25_indices.get(job_id)
    if not bm25:
        return []

    bm25_results = bm25.search(question, top_k=20)
    dense_results = search_dense(question, job_id, top_k=20)

    fused = reciprocal_rank_fusion(bm25_results, dense_results, top_k=20)
    return rerank(question, fused, top_k=top_k)
