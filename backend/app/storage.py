import json
import sqlite3
from pathlib import Path
from typing import Optional

from backend.app.ingestion.models import Chunk
from backend.app.ingestion.metadata import RepoMetadata

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "codesage.db"

_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_db(_conn)
    return _conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            repo_url TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            files INTEGER DEFAULT 0,
            chunks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            chunk_type TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            name TEXT,
            language TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        );

        CREATE TABLE IF NOT EXISTS metadata (
            job_id TEXT PRIMARY KEY,
            project_name TEXT,
            description TEXT,
            languages TEXT,
            orms TEXT,
            databases TEXT,
            frameworks TEXT,
            auth_methods TEXT,
            package_managers TEXT,
            config_files TEXT,
            file_count INTEGER DEFAULT 0,
            total_lines INTEGER DEFAULT 0,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_job_id ON chunks(job_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path, start_line);
    """)
    conn.commit()


def store_job(job_id: str, repo_url: str, status: str, message: str = "") -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO jobs (job_id, repo_url, status, message) VALUES (?, ?, ?, ?)",
        (job_id, repo_url, status, message),
    )
    conn.commit()


def update_job(job_id: str, status: str, message: str = "", files: int = 0, chunks: int = 0) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE jobs SET status = ?, message = ?, files = ?, chunks = ? WHERE job_id = ?",
        (status, message, files, chunks, job_id),
    )
    conn.commit()


def get_job(job_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if row:
        return dict(row)
    return None


def get_last_completed_job() -> Optional[str]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT job_id FROM jobs WHERE status = 'completed' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return row["job_id"] if row else None


def store_chunks_db(job_id: str, chunks: list[Chunk]) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM chunks WHERE job_id = ?", (job_id,))
    conn.executemany(
        "INSERT INTO chunks (job_id, file_path, chunk_type, start_line, end_line, name, language, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (job_id, c.file_path, c.chunk_type, c.start_line, c.end_line, c.name, c.language, c.content)
            for c in chunks
        ],
    )
    conn.commit()


def get_chunks_db(job_id: str) -> list[Chunk]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT file_path, chunk_type, start_line, end_line, name, language, content FROM chunks WHERE job_id = ?",
        (job_id,),
    ).fetchall()
    return [
        Chunk(
            file_path=r["file_path"],
            chunk_type=r["chunk_type"],
            start_line=r["start_line"],
            end_line=r["end_line"],
            name=r["name"],
            language=r["language"],
            content=r["content"],
        )
        for r in rows
    ]


def store_metadata_db(job_id: str, metadata: RepoMetadata) -> None:
    conn = _get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO metadata
           (job_id, project_name, description, languages, orms, databases, frameworks, auth_methods, package_managers, config_files, file_count, total_lines)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            metadata.project_name,
            metadata.description,
            json.dumps(metadata.languages),
            json.dumps(metadata.orms),
            json.dumps(metadata.databases),
            json.dumps(metadata.frameworks),
            json.dumps(metadata.auth_methods),
            json.dumps(metadata.package_managers),
            json.dumps(metadata.config_files),
            metadata.file_count,
            metadata.total_lines,
        ),
    )
    conn.commit()


def get_metadata_db(job_id: str) -> Optional[RepoMetadata]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM metadata WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        return None

    m = RepoMetadata()
    m.project_name = row["project_name"] or ""
    m.description = row["description"] or ""
    m.languages = json.loads(row["languages"]) if row["languages"] else []
    m.orms = json.loads(row["orms"]) if row["orms"] else []
    m.databases = json.loads(row["databases"]) if row["databases"] else []
    m.frameworks = json.loads(row["frameworks"]) if row["frameworks"] else []
    m.auth_methods = json.loads(row["auth_methods"]) if row["auth_methods"] else []
    m.package_managers = json.loads(row["package_managers"]) if row["package_managers"] else []
    m.config_files = json.loads(row["config_files"]) if row["config_files"] else []
    m.file_count = row["file_count"] or 0
    m.total_lines = row["total_lines"] or 0
    return m


def clear_job_db(job_id: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
    conn.execute("DELETE FROM chunks WHERE job_id = ?", (job_id,))
    conn.execute("DELETE FROM metadata WHERE job_id = ?", (job_id,))
    conn.commit()


def close_db() -> None:
    global _conn
    if _conn:
        _conn.close()
        _conn = None
