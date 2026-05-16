import os
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.app.ingestion.cloner import clone_repo, validate_github_url
from backend.app.ingestion.parser import parse_repo
from backend.app.ingestion.chunker import chunk_document
from backend.app.retrieval import build_index, query_repo
from backend.app.generation import stream_answer

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="CodeSage", description="Hybrid RAG for codebases")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class IndexRequest(BaseModel):
    repo_url: str


class QueryRequest(BaseModel):
    question: str


jobs: dict[str, dict] = {}


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/index")
async def index_repo(request: IndexRequest, background_tasks: BackgroundTasks):
    if not validate_github_url(request.repo_url):
        return {"error": "Invalid GitHub URL"}

    job_id = request.repo_url.split("/")[-1].replace(".git", "")
    jobs[job_id] = {"status": "processing", "message": "Cloning repository..."}

    background_tasks.add_task(_run_indexing, job_id, request.repo_url)

    return {"job_id": job_id, "status": "processing"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    return job


@app.post("/api/query")
async def query_endpoint(request: QueryRequest):
    last_job_id = None
    for jid, job in jobs.items():
        if job.get("status") == "completed":
            last_job_id = jid

    if not last_job_id:
        return {"error": "No repository has been indexed yet."}

    results = query_repo(last_job_id, request.question)
    if not results:
        return {"error": "No relevant results found."}

    citations = []
    relevant_files = set()
    for chunk, _ in results:
        citations.append(f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}")
        relevant_files.add(chunk.file_path)

    async def _stream():
        for token in stream_answer(request.question, results):
            yield token

    return StreamingResponse(_stream(), media_type="text/event-stream")


def _run_indexing(job_id: str, repo_url: str):
    try:
        temp_dir = clone_repo(repo_url)
        jobs[job_id]["message"] = "Parsing files..."

        documents = parse_repo(temp_dir.name)
        jobs[job_id]["message"] = f"Chunking {len(documents)} files..."

        all_chunks = []
        for doc in documents:
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)

        jobs[job_id]["message"] = "Building BM25 index..."
        build_index(job_id, all_chunks)

        jobs[job_id] = {
            "status": "completed",
            "files": len(documents),
            "chunks": len(all_chunks),
            "message": f"Indexed {len(documents)} files, {len(all_chunks)} chunks",
        }

        temp_dir.cleanup()
    except Exception as e:
        jobs[job_id] = {
            "status": "failed",
            "message": str(e),
        }
