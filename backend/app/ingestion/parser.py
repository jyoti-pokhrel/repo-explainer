from pathlib import Path

from .models import FileDocument

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".md": "markdown",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
    "target",
    ".idea",
    ".vscode",
    "eggs",
    "*.egg-info",
}


def parse_repo(repo_path: str | Path) -> list[FileDocument]:
    repo_path = Path(repo_path)
    if not repo_path.is_dir():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    documents: list[FileDocument] = []

    for file_path in _walk(repo_path):
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        language = SUPPORTED_EXTENSIONS[ext]
        content = _read_file(file_path)
        if content is None:
            continue

        rel_path = str(file_path.relative_to(repo_path))
        documents.append(FileDocument(
            file_path=rel_path,
            content=content,
            language=language,
        ))

    return documents


def _walk(root: Path):
    for path in sorted(root.iterdir()):
        if path.name in SKIP_DIRS:
            continue
        if path.is_dir():
            yield from _walk(path)
        elif path.is_file():
            yield path


def _read_file(file_path: Path) -> str | None:
    try:
        return file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError):
        return None
