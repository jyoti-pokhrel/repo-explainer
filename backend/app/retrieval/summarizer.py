from pathlib import Path

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "index.js", "index.ts", "main.go",
    "main.rs", "server.js", "server.ts", "manage.py",
    "wsgi.py", "asgi.py", "cli.py", "run.py",
}

ARCH_PATTERNS = {
    "MVC": ["controllers", "models", "views", "templates"],
    "microservices": ["services", "api", "gateway"],
    "monolith": ["app", "src", "lib"],
}


def generate_summary(repo_path: str | Path) -> str:
    repo_path = Path(repo_path)
    lines = []

    entry_points = _find_entry_points(repo_path)
    if entry_points:
        lines.append(f"Entry points: {', '.join(entry_points)}")

    top_dirs = _get_top_dirs(repo_path)
    if top_dirs:
        lines.append(f"Top-level directories: {', '.join(top_dirs)}")

    arch = _detect_architecture(repo_path)
    if arch:
        lines.append(f"Likely architecture: {arch}")

    return "\n".join(lines) if lines else ""


def _find_entry_points(repo_path: Path) -> list[str]:
    found = []
    for name in ENTRY_POINT_NAMES:
        if (repo_path / name).exists():
            found.append(name)
    return found


def _get_top_dirs(repo_path: Path) -> list[str]:
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist", "target", ".idea", ".vscode", "docs", "tests", "test"}
    return sorted([
        d.name for d in repo_path.iterdir()
        if d.is_dir() and d.name not in skip
    ])


def _detect_architecture(repo_path: Path) -> str | None:
    try:
        top_dirs = {d.name.lower() for d in repo_path.iterdir() if d.is_dir()}
    except (PermissionError, OSError):
        return None

    for arch, markers in ARCH_PATTERNS.items():
        if any(m in top_dirs for m in markers):
            return arch
    return None
