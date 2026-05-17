import pytest
import tempfile
from pathlib import Path

from backend.app.ingestion.metadata import extract_metadata, RepoMetadata


class TestExtractMetadata:
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = extract_metadata(tmpdir)
            assert isinstance(meta, RepoMetadata)
            assert meta.file_count == 0

    def test_python_project_with_requirements(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "requirements.txt").write_text("fastapi>=0.100\nsqlalchemy>=2.0\npsycopg2-binary\n")
            (root / "main.py").write_text("from fastapi import FastAPI\n\napp = FastAPI()\n")

            meta = extract_metadata(tmpdir)
            assert "FastAPI" in meta.frameworks
            assert "SQLAlchemy" in meta.orms
            assert "PostgreSQL" in meta.databases
            assert meta.file_count == 1

    def test_python_project_with_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text('[project]\nname = "my-app"\ndescription = "A test app"\ndependencies = ["django", "celery"]\n')
            (root / "uv.lock").touch()

            meta = extract_metadata(tmpdir)
            assert meta.project_name == "my-app"
            assert meta.description == "A test app"
            assert "Django" in meta.frameworks
            assert "Celery (task queue)" in meta.frameworks
            assert "uv" in meta.package_managers

    def test_js_project_with_package_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package.json").write_text('{"name": "test-app", "description": "Test", "dependencies": {"express": "^4.0", "prisma": "^5.0", "pg": "^8.0"}}')

            meta = extract_metadata(tmpdir)
            assert meta.project_name == "test-app"
            assert meta.description == "Test"
            assert "Express.js" in meta.frameworks
            assert "Prisma" in meta.orms
            assert "PostgreSQL" in meta.databases

    def test_go_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "go.mod").write_text("module example.com/app\n\ngo 1.21\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.0\n\tgithub.com/jackc/pgx/v5 v5.5.0\n)\n")

            meta = extract_metadata(tmpdir)
            assert meta.project_name == "example.com/app"
            assert "Go" in meta.languages
            assert "Gin" in meta.frameworks
            assert "PostgreSQL" in meta.databases

    def test_docker_compose_detects_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docker-compose.yml").write_text("services:\n  db:\n    image: postgres:15\n  cache:\n    image: redis:7\n")

            meta = extract_metadata(tmpdir)
            assert "PostgreSQL" in meta.databases
            assert "Redis" in meta.databases

    def test_env_file_detects_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env").write_text("DATABASE_URL=postgresql://localhost:5432/mydb\nREDIS_URL=redis://localhost:6379\n")

            meta = extract_metadata(tmpdir)
            assert "PostgreSQL" in meta.databases
            assert "Redis" in meta.databases

    def test_readme_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# My Awesome Project\n\nThis is a great project.\n")

            meta = extract_metadata(tmpdir)
            assert meta.description == "My Awesome Project"


class TestRepoMetadata:
    def test_to_dict_and_from_dict(self):
        m = RepoMetadata(
            project_name="test",
            description="A test",
            languages=["Python"],
            orms=["SQLAlchemy"],
            databases=["PostgreSQL"],
            frameworks=["FastAPI"],
            file_count=10,
            total_lines=500,
        )

        d = m.to_dict()
        restored = RepoMetadata.from_dict(d)

        assert restored.project_name == m.project_name
        assert restored.orms == m.orms
        assert restored.databases == m.databases
        assert restored.file_count == m.file_count
