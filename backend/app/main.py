import os
import time
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from backend.app.ingestion.cloner import clone_repo, validate_github_url
from backend.app.ingestion.parser import parse_repo
from backend.app.ingestion.chunker import chunk_document
from backend.app.ingestion.metadata import extract_metadata
from backend.app.retrieval import build_index, query_repo
from backend.app.retrieval.router import classify_query, answer_metadata_query, QueryResult
from backend.app.retrieval.summarizer import generate_summary
from backend.app.generation import stream_answer
from backend.app.storage import store_job, update_job, get_job, get_last_completed_job, get_metadata_db, store_metadata_db

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="CodeSage", description="Hybrid RAG for codebases")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

QUERY_TIMEOUT = 30


@app.get("/health")
async def health():
    return {"status": "ok"}


class IndexRequest(BaseModel):
    repo_url: str


class QueryRequest(BaseModel):
    question: str
    job_id: str | None = None


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/index")
async def index_repo(request: IndexRequest, background_tasks: BackgroundTasks):
    if not validate_github_url(request.repo_url):
        return {"error": "Invalid GitHub URL"}

    job_id = request.repo_url.split("/")[-1].replace(".git", "")
    store_job(job_id, request.repo_url, "processing", "Cloning repository...")

    background_tasks.add_task(_run_indexing, job_id, request.repo_url)

    return {"job_id": job_id, "status": "processing"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return {"error": "Job not found"}
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "message": job["message"],
        "files": job.get("files", 0),
        "chunks": job.get("chunks", 0),
    }


@app.get("/api/metadata/{job_id}")
async def get_metadata(job_id: str):
    metadata = get_metadata_db(job_id)
    if not metadata:
        return {"error": "No metadata found for this job"}
    return metadata.to_dict()


@app.get("/api/code/{job_id}")
async def get_code(job_id: str, file_path: str):
    from backend.app.storage import get_chunks_db
    chunks = get_chunks_db(job_id)
    # Match any chunks that contain the requested file path (handling partial matches if needed)
    matching = [c for c in chunks if c.file_path == file_path or c.file_path.endswith(file_path)]
    if not matching:
        return {"error": "File not found"}
    matching.sort(key=lambda x: x.start_line)
    return {
        "file_path": file_path,
        "chunks": [{"start": c.start_line, "end": c.end_line, "content": c.content} for c in matching]
    }


@app.post("/api/query")
async def query_endpoint(request: QueryRequest):
    job_id = request.job_id or get_last_completed_job()

    if not job_id:
        return {"error": "No repository has been indexed yet."}

    job = get_job(job_id)
    if not job or job["status"] != "completed":
        return {"error": "Repository indexing is not complete."}

    t0 = time.time()
    query_type = classify_query(request.question)
    print(f"[QUERY] classification took {time.time()-t0:.3f}s -> {query_type}")

    if query_type == QueryResult.METADATA:
        metadata = get_metadata_db(job_id)
        if metadata:
            answer = answer_metadata_query(request.question, metadata)
            return {"answer": answer, "type": "metadata"}
        return {"error": "No metadata available for this repository."}

    metadata = get_metadata_db(job_id)
    summary = ""

    async def _stream():
        start = time.time()
        try:
            yield f"data: Searching codebase...\n\n"

            t1 = time.time()
            results = query_repo(job_id, request.question, top_k=5)
            print(f"[QUERY] retrieval took {time.time()-t1:.3f}s, got {len(results)} results")

            if not results:
                yield f"data: No relevant results found.\n\n"
                return

            yield f"data: Generating answer...\n\n"

            t2 = time.time()
            token_count = 0
            for token in stream_answer(request.question, results[:5], metadata, summary):
                if time.time() - start > QUERY_TIMEOUT:
                    yield f"data: Query timed out after {QUERY_TIMEOUT}s. Try a more specific question.\n\n"
                    print(f"[QUERY] TIMEOUT after {time.time()-start:.1f}s")
                    return
                token_count += 1
                yield f"data: {token}\n\n"

            print(f"[QUERY] LLM streaming took {time.time()-t2:.3f}s, {token_count} tokens")
            print(f"[QUERY] TOTAL query time: {time.time()-start:.3f}s")

        except Exception as e:
            print(f"[QUERY] ERROR: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


def _run_indexing(job_id: str, repo_url: str):
    try:
        temp_dir = clone_repo(repo_url)
        update_job(job_id, "processing", "Parsing files...")

        documents = parse_repo(temp_dir.name)
        update_job(job_id, "processing", f"Extracting metadata...")

        metadata = extract_metadata(temp_dir.name)
        store_metadata_db(job_id, metadata)

        update_job(job_id, "processing", f"Generating summary...")

        summary = generate_summary(temp_dir.name)

        update_job(job_id, "processing", f"Chunking {len(documents)} files...")

        all_chunks = []
        for doc in documents:
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)

        update_job(job_id, "processing", "Building BM25 index...")
        build_index(job_id, all_chunks)

        update_job(
            job_id,
            "completed",
            f"Indexed {len(documents)} files, {len(all_chunks)} chunks",
            files=len(documents),
            chunks=len(all_chunks),
        )

        temp_dir.cleanup()
    except Exception as e:
        update_job(job_id, "failed", str(e))
