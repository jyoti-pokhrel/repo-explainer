from dataclasses import dataclass, field

from backend.app.ingestion.models import Chunk

_store: dict[str, list[Chunk]] = {}


def store_chunks(job_id: str, chunks: list[Chunk]) -> None:
    _store[job_id] = chunks


def get_chunks(job_id: str) -> list[Chunk]:
    return _store.get(job_id, [])


def get_all_chunks() -> list[tuple[str, list[Chunk]]]:
    return list(_store.items())


def clear_job(job_id: str) -> None:
    _store.pop(job_id, None)
