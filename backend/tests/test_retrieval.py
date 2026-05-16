from backend.app.ingestion.models import Chunk
from backend.app.retrieval.bm25 import BM25Search, tokenize
from backend.app.retrieval.rrf import reciprocal_rank_fusion


class TestTokenize:
    def test_snake_case(self):
        tokens = tokenize("get_user_by_id")
        assert "get" in tokens
        assert "user" in tokens
        assert "by" in tokens
        assert "id" in tokens

    def test_camel_case(self):
        tokens = tokenize("getUserById")
        assert "get" in tokens
        assert "user" in tokens
        assert "id" in tokens

    def test_operators(self):
        tokens = tokenize("if (x == y)")
        assert "==" in tokens

    def test_lowercase(self):
        tokens = tokenize("Authentication")
        assert "authentication" in tokens


class TestBM25Search:
    def test_basic_search(self):
        chunks = [
            Chunk(content="def authenticate_user(): pass", file_path="auth.py", chunk_type="function", start_line=1, end_line=1, name="authenticate_user", language="python"),
            Chunk(content="def calculate_total(): pass", file_path="cart.py", chunk_type="function", start_line=1, end_line=1, name="calculate_total", language="python"),
            Chunk(content="class AuthMiddleware: pass", file_path="middleware.py", chunk_type="class", start_line=1, end_line=1, name="AuthMiddleware", language="python"),
        ]

        bm25 = BM25Search()
        bm25.build(chunks)

        results = bm25.search("authentication", top_k=2)
        assert len(results) == 2
        assert results[0][0].name in ("authenticate_user", "AuthMiddleware")

    def test_empty_index(self):
        bm25 = BM25Search()
        assert bm25.search("test") == []


class TestRRF:
    def test_fusion_overlap(self):
        chunk_a = Chunk(content="a", file_path="a.py", chunk_type="function", start_line=1, end_line=1, language="python")
        chunk_b = Chunk(content="b", file_path="b.py", chunk_type="function", start_line=1, end_line=1, language="python")
        chunk_c = Chunk(content="c", file_path="c.py", chunk_type="function", start_line=1, end_line=1, language="python")

        bm25 = [(chunk_a, 0.9), (chunk_b, 0.7), (chunk_c, 0.5)]
        dense = [(chunk_a, 0.8), (chunk_c, 0.6), (chunk_b, 0.4)]

        results = reciprocal_rank_fusion(bm25, dense, top_k=3)
        assert results[0][0] == chunk_a
        assert len(results) == 3

    def test_fusion_no_overlap(self):
        chunk_a = Chunk(content="a", file_path="a.py", chunk_type="function", start_line=1, end_line=1, language="python")
        chunk_b = Chunk(content="b", file_path="b.py", chunk_type="function", start_line=1, end_line=1, language="python")

        bm25 = [(chunk_a, 0.9)]
        dense = [(chunk_b, 0.8)]

        results = reciprocal_rank_fusion(bm25, dense, top_k=2)
        assert len(results) == 2

    def test_empty_results(self):
        results = reciprocal_rank_fusion([], [], top_k=5)
        assert results == []
