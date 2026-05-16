from dataclasses import dataclass


@dataclass
class Chunk:
    content: str
    file_path: str
    chunk_type: str
    start_line: int
    end_line: int
    name: str | None = None
    language: str = ""


@dataclass
class FileDocument:
    file_path: str
    content: str
    language: str
