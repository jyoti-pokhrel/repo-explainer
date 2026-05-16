from backend.app.ingestion.models import Chunk

K = 60


def reciprocal_rank_fusion(
    bm25_results: list[tuple[Chunk, float]],
    dense_results: list[tuple[Chunk, float]],
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    scores: dict[str, float] = {}
    chunk_map: dict[str, Chunk] = {}

    for rank, (chunk, _) in enumerate(bm25_results, 1):
        key = _chunk_key(chunk)
        scores[key] = scores.get(key, 0) + 1 / (K + rank)
        chunk_map[key] = chunk

    for rank, (chunk, _) in enumerate(dense_results, 1):
        key = _chunk_key(chunk)
        scores[key] = scores.get(key, 0) + 1 / (K + rank)
        chunk_map[key] = chunk

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(chunk_map[key], score) for key, score in ranked[:top_k]]


def _chunk_key(chunk: Chunk) -> str:
    return f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
