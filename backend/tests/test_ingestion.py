import pytest

from backend.app.ingestion.cloner import validate_github_url
from backend.app.ingestion.models import Chunk, FileDocument
from backend.app.ingestion.chunker import chunk_document


class TestValidateGithubUrl:
    def test_valid_url(self):
        assert validate_github_url("https://github.com/user/repo") is True

    def test_valid_url_with_git(self):
        assert validate_github_url("https://github.com/user/repo.git") is True

    def test_invalid_url(self):
        assert validate_github_url("https://gitlab.com/user/repo") is False

    def test_empty_string(self):
        assert validate_github_url("") is False

    def test_not_a_url(self):
        assert validate_github_url("not-a-url") is False


class TestChunk:
    def test_chunk_defaults(self):
        chunk = Chunk(
            content="def foo(): pass",
            file_path="test.py",
            chunk_type="function",
            start_line=1,
            end_line=1,
        )
        assert chunk.name is None
        assert chunk.language == ""


class TestChunkDocument:
    def test_markdown_no_headings(self):
        doc = FileDocument(
            file_path="README.md",
            content="Just plain text.\nNo headings here.",
            language="markdown",
        )
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "block"

    def test_markdown_with_headings(self):
        doc = FileDocument(
            file_path="README.md",
            content="## Section One\ncontent one\n\n## Section Two\ncontent two",
            language="markdown",
        )
        chunks = chunk_document(doc)
        assert len(chunks) == 2
        assert chunks[0].name == "Section One"
        assert chunks[1].name == "Section Two"

    def test_python_single_function(self):
        doc = FileDocument(
            file_path="app.py",
            content="def hello():\n    print('world')\n",
            language="python",
        )
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "function"
        assert chunks[0].name == "hello"

    def test_python_class_and_function(self):
        content = """\
class MyClass:
    def method(self):
        pass

def standalone():
    pass
"""
        doc = FileDocument(
            file_path="app.py",
            content=content,
            language="python",
        )
        chunks = chunk_document(doc)
        names = [c.name for c in chunks if c.name]
        assert "MyClass" in names
        assert "standalone" in names

    def test_empty_python_file(self):
        doc = FileDocument(
            file_path="empty.py",
            content="",
            language="python",
        )
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "block"

    def test_javascript_function(self):
        doc = FileDocument(
            file_path="app.js",
            content="function greet(name) {\n  return `Hello, ${name}`;\n}\n",
            language="javascript",
        )
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].name == "greet"

    def test_typescript_class(self):
        doc = FileDocument(
            file_path="app.ts",
            content="class UserService {\n  getUsers(): User[] {\n    return [];\n  }\n}\n",
            language="typescript",
        )
        chunks = chunk_document(doc)
        assert any(c.name == "UserService" for c in chunks)

    def test_go_function(self):
        doc = FileDocument(
            file_path="main.go",
            content="func main() {\n\tprintln(\"hello\")\n}\n",
            language="go",
        )
        chunks = chunk_document(doc)
        assert any(c.name == "main" for c in chunks)

    def test_java_class(self):
        doc = FileDocument(
            file_path="App.java",
            content="public class App {\n    public static void main(String[] args) {}\n}\n",
            language="java",
        )
        chunks = chunk_document(doc)
        assert any(c.name == "App" for c in chunks)
