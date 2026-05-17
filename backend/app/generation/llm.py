import os
from typing import Iterator

from dotenv import load_dotenv
from groq import Groq

from backend.app.ingestion.metadata import RepoMetadata
from backend.app.ingestion.models import Chunk

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""), timeout=30)


def _build_prompt(question: str, chunks: list[tuple[Chunk, float]], metadata: RepoMetadata | None = None, summary: str = "") -> str:
    context_parts = []
    for i, (chunk, score) in enumerate(chunks, 1):
        citation = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
        name = chunk.name or ""
        label = f" ({name})" if name else ""
        context_parts.append(f"[{i}] {citation}{label} [relevance: {score:.3f}]\n```{chunk.language}\n{chunk.content}\n```")

    context = "\n\n".join(context_parts)

    metadata_section = ""
    if metadata and (metadata.orms or metadata.databases or metadata.frameworks or metadata.languages):
        parts = []
        if metadata.project_name:
            parts.append(f"- Project: {metadata.project_name}")
        if metadata.description:
            parts.append(f"- Description: {metadata.description}")
        if metadata.languages:
            parts.append(f"- Languages: {', '.join(metadata.languages)}")
        if metadata.frameworks:
            parts.append(f"- Frameworks: {', '.join(metadata.frameworks)}")
        if metadata.orms:
            parts.append(f"- ORMs: {', '.join(metadata.orms)}")
        if metadata.databases:
            parts.append(f"- Databases: {', '.join(metadata.databases)}")
        if metadata.auth_methods:
            parts.append(f"- Authentication: {', '.join(metadata.auth_methods)}")
        if metadata.package_managers:
            parts.append(f"- Package managers: {', '.join(metadata.package_managers)}")
        metadata_section = "\n## Repository Metadata\n\n" + "\n".join(parts)

    summary_section = ""
    if summary:
        summary_section = f"\n## Repository Structure\n\n{summary}"

    return f"""You are a code analysis assistant. Answer the question using ONLY the provided code context and repository metadata.

## Repository Metadata

{metadata_section}

## Repository Structure

{summary_section}

## Context

{context}

## Question

{question}

## Rules

- Answer only from the provided context and metadata
- Cite sources as [file_path:line_start-line_end] inline
- If context is insufficient, explicitly say what's missing
- Include relevant code snippets in your answer
- Be concise but thorough
- When asked about ORMs, databases, or frameworks, reference the metadata section first"""


def generate_answer(question: str, chunks: list[tuple[Chunk, float]], metadata: RepoMetadata | None = None, summary: str = "") -> str:
    prompt = _build_prompt(question, chunks, metadata, summary)
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


def stream_answer(question: str, chunks: list[tuple[Chunk, float]], metadata: RepoMetadata | None = None, summary: str = "") -> Iterator[str]:
    prompt = _build_prompt(question, chunks, metadata, summary)
    stream = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
