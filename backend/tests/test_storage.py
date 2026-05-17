import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.app.ingestion.models import Chunk
from backend.app.ingestion.metadata import RepoMetadata
from backend.app.storage import (
    store_job, update_job, get_job, get_last_completed_job,
    store_chunks_db, get_chunks_db,
    store_metadata_db, get_metadata_db,
    clear_job_db, close_db,
)


@pytest.fixture(autouse=True)
def use_temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with patch("backend.app.storage.DB_PATH", db_path):
            close_db()
            yield
            close_db()


class TestStorageJobs:
    def test_store_and_get_job(self):
        store_job("test-1", "https://github.com/user/repo", "processing", "Cloning...")
        job = get_job("test-1")
        assert job is not None
        assert job["job_id"] == "test-1"
        assert job["status"] == "processing"

    def test_update_job(self):
        store_job("test-2", "https://github.com/user/repo", "processing")
        update_job("test-2", "completed", "Done", files=10, chunks=50)
        job = get_job("test-2")
        assert job["status"] == "completed"
        assert job["files"] == 10
        assert job["chunks"] == 50

    def test_get_last_completed_job(self):
        store_job("job-1", "https://github.com/user/repo1", "completed")
        store_job("job-2", "https://github.com/user/repo2", "processing")
        last = get_last_completed_job()
        assert last == "job-1"

    def test_get_nonexistent_job(self):
        assert get_job("nonexistent") is None


class TestStorageChunks:
    def test_store_and_get_chunks(self):
        chunks = [
            Chunk(content="def foo(): pass", file_path="app.py", chunk_type="function", start_line=1, end_line=1, name="foo", language="python"),
            Chunk(content="def bar(): pass", file_path="app.py", chunk_type="function", start_line=3, end_line=3, name="bar", language="python"),
        ]
        store_chunks_db("test-job", chunks)
        retrieved = get_chunks_db("test-job")
        assert len(retrieved) == 2
        assert retrieved[0].name == "foo"
        assert retrieved[1].name == "bar"

    def test_store_chunks_replaces_old(self):
        old_chunks = [Chunk(content="old", file_path="old.py", chunk_type="block", start_line=1, end_line=1, language="python")]
        store_chunks_db("test-job", old_chunks)

        new_chunks = [Chunk(content="new", file_path="new.py", chunk_type="block", start_line=1, end_line=1, language="python")]
        store_chunks_db("test-job", new_chunks)

        retrieved = get_chunks_db("test-job")
        assert len(retrieved) == 1
        assert retrieved[0].content == "new"

    def test_get_chunks_empty_job(self):
        assert get_chunks_db("nonexistent") == []


class TestStorageMetadata:
    def test_store_and_get_metadata(self):
        meta = RepoMetadata(
            project_name="test",
            orms=["SQLAlchemy"],
            databases=["PostgreSQL"],
            frameworks=["FastAPI"],
            file_count=10,
            total_lines=500,
        )
        store_metadata_db("test-job", meta)
        retrieved = get_metadata_db("test-job")
        assert retrieved is not None
        assert retrieved.project_name == "test"
        assert retrieved.orms == ["SQLAlchemy"]
        assert retrieved.databases == ["PostgreSQL"]
        assert retrieved.file_count == 10

    def test_get_nonexistent_metadata(self):
        assert get_metadata_db("nonexistent") is None


class TestClearJob:
    def test_clear_job_removes_all_data(self):
        chunk = Chunk(content="test", file_path="test.py", chunk_type="block", start_line=1, end_line=1, language="python")
        meta = RepoMetadata(project_name="test", file_count=1)

        store_job("clear-test", "https://github.com/user/repo", "completed")
        store_chunks_db("clear-test", [chunk])
        store_metadata_db("clear-test", meta)

        clear_job_db("clear-test")

        assert get_job("clear-test") is None
        assert get_chunks_db("clear-test") == []
        assert get_metadata_db("clear-test") is None
