import os
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.app.ingestion.cloner import clone_repo, validate_github_url
from backend.app.ingestion.parser import parse_repo
from backend.app.ingestion.chunker import chunk_document
from backend.app.retrieval import build_index, query_repo

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
        return {
            "answer": "No repository has been indexed yet.",
            "citations": [],
            "relevant_files": [],
        }

    results = query_repo(last_job_id, request.question)
    if not results:
        return {
            "answer": "No relevant results found.",
            "citations": [],
            "relevant_files": [],
        }

    context_parts = []
    citations = []
    relevant_files = set()

    for chunk, score in results:
        citation = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
        context_parts.append(f"[{citation}]\n{chunk.content}")
        citations.append(citation)
        relevant_files.add(chunk.file_path)

    context = "\n\n".join(context_parts)

    return {
        "answer": _format_answer(context, results),
        "citations": citations,
        "relevant_files": sorted(relevant_files),
    }


def _format_answer(context: str, results: list[tuple]) -> str:
    lines = ["Here are the most relevant code chunks:\n"]
    for i, (chunk, score) in enumerate(results, 1):
        citation = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
        name = chunk.name or ""
        label = f"{name} " if name else ""
        lines.append(f"{i}. **{label}** ({citation}) [score: {score:.4f}]")
        lines.append(f"```{chunk.language}")
        lines.append(chunk.content)
        lines.append("```\n")
    return "\n".join(lines)


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
