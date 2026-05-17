import pytest

from backend.app.retrieval.router import classify_query, answer_metadata_query, QueryResult
from backend.app.ingestion.metadata import RepoMetadata


@pytest.fixture
def sample_metadata():
    return RepoMetadata(
        project_name="test-app",
        description="A test application",
        languages=["Python"],
        orms=["SQLAlchemy"],
        databases=["PostgreSQL", "Redis"],
        frameworks=["FastAPI"],
        auth_methods=["JWT"],
        package_managers=["uv"],
        file_count=42,
        total_lines=3500,
    )


class TestClassifyQuery:
    def test_orm_query(self):
        assert classify_query("What ORM does this project use?") == QueryResult.METADATA

    def test_database_query(self):
        assert classify_query("Which database is used?") == QueryResult.METADATA

    def test_framework_query(self):
        assert classify_query("What framework is this?") == QueryResult.METADATA

    def test_language_query(self):
        assert classify_query("What language is this written in?") == QueryResult.METADATA

    def test_auth_query(self):
        assert classify_query("How does authentication work?") == QueryResult.RAG

    def test_what_auth_query(self):
        assert classify_query("What auth is used?") == QueryResult.METADATA

    def test_how_auth_detail_query(self):
        assert classify_query("How is authentication actually done in detail?") == QueryResult.RAG

    def test_what_authentication_query(self):
        assert classify_query("What authentication is used?") == QueryResult.METADATA

    def test_explain_auth_query(self):
        assert classify_query("Explain the authentication middleware") == QueryResult.RAG

    def test_summary_query(self):
        assert classify_query("Describe this project") == QueryResult.METADATA

    def test_code_query(self):
        assert classify_query("How does the user registration flow work?") == QueryResult.RAG

    def test_implementation_query(self):
        assert classify_query("Explain the user registration flow") == QueryResult.RAG

    def test_how_to_query(self):
        assert classify_query("How do I add a new endpoint?") == QueryResult.RAG


class TestAnswerMetadataQuery:
    def test_orm_answer(self, sample_metadata):
        answer = answer_metadata_query("What ORM is used?", sample_metadata)
        assert "SQLAlchemy" in answer

    def test_database_answer(self, sample_metadata):
        answer = answer_metadata_query("Which database?", sample_metadata)
        assert "PostgreSQL" in answer
        assert "Redis" in answer

    def test_framework_answer(self, sample_metadata):
        answer = answer_metadata_query("What framework?", sample_metadata)
        assert "FastAPI" in answer

    def test_auth_answer(self, sample_metadata):
        answer = answer_metadata_query("How is auth handled?", sample_metadata)
        assert "JWT" in answer

    def test_language_answer(self, sample_metadata):
        answer = answer_metadata_query("What language?", sample_metadata)
        assert "Python" in answer

    def test_file_count_answer(self, sample_metadata):
        answer = answer_metadata_query("How many files?", sample_metadata)
        assert "42" in answer

    def test_overview_answer(self, sample_metadata):
        answer = answer_metadata_query("Describe this project", sample_metadata)
        assert "test-app" in answer
        assert "SQLAlchemy" in answer
        assert "PostgreSQL" in answer

    def test_no_orm(self):
        meta = RepoMetadata()
        answer = answer_metadata_query("What ORM?", meta)
        assert "No ORM detected" in answer
