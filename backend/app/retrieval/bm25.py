import re
import nltk
from nltk.stem import PorterStemmer
from rank_bm25 import BM25Okapi

from backend.app.ingestion.models import Chunk

_nltk_initialized = False

CAMEL_CASE = re.compile(r"([a-z0-9])([A-Z])")
CODE_OPERATORS = re.compile(r"(==|!=|<=|>=|->|::|\+\+|--|&&|\|\||\.\.\.)")

_stemmer = PorterStemmer()
_stop_words: set[str] | None = None


def _ensure_nltk():
    global _nltk_initialized, _stop_words
    if _nltk_initialized:
        return
    for resource in ("punkt_tab", "stopwords"):
        try:
            nltk.data.find(f"tokenizers/{resource}" if resource == "punkt_tab" else f"corpora/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)
    from nltk.corpus import stopwords
    _stop_words = set(stopwords.words("english"))
    _nltk_initialized = True


def tokenize(text: str, is_query: bool = False) -> list[str]:
    _ensure_nltk()
    tokens: list[str] = []
    for op in CODE_OPERATORS.finditer(text):
        tokens.append(op.group())
    text = CODE_OPERATORS.sub(" ", text)
    text = text.replace("_", " ")
    text = CAMEL_CASE.sub(r"\1 \2", text)
    for part in text.split():
        part = part.strip().lower()
        if not part:
            continue
        if is_query and part in _stop_words:
            continue
        tokens.append(_stemmer.stem(part))
    return tokens


class BM25Search:
    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._chunks: list[Chunk] = []
        self._tokenized: list[list[str]] = []

    def build(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._tokenized = [tokenize(c.content) for c in chunks]
        self._bm25 = BM25Okapi(self._tokenized)

    def search(self, query: str, top_k: int = 20) -> list[tuple[Chunk, float]]:
        if not self._bm25 or not self._chunks:
            return []

        query_tokens = tokenize(query, is_query=True)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        ranked = sorted(
            [(self._chunks[i], scores[i]) for i in range(len(self._chunks))],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k]
