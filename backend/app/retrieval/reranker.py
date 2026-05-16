from sentence_transformers import CrossEncoder

from backend.app.ingestion.models import Chunk

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder | None:
    global _model
    if _model is None:
        try:
            _model = CrossEncoder(_MODEL_NAME)
        except Exception:
            return None
    return _model


def rerank(query: str, chunks: list[tuple[Chunk, float]], top_k: int = 5) -> list[tuple[Chunk, float]]:
    model = _get_model()
    if model is None or not chunks:
        return chunks[:top_k]

    pairs = [(query, chunk.content) for chunk, _ in chunks]
    scores = model.predict(pairs).tolist()

    ranked = sorted(
        [(chunks[i][0], float(scores[i])) for i in range(len(chunks))],
        key=lambda x: x[1],
        reverse=True,
    )
    return ranked[:top_k]
