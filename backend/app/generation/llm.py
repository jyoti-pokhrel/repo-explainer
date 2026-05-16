import os
from typing import Iterator

from dotenv import load_dotenv
from groq import Groq

from backend.app.ingestion.models import Chunk

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


def _build_prompt(question: str, chunks: list[tuple[Chunk, float]]) -> str:
    context_parts = []
    for i, (chunk, score) in enumerate(chunks, 1):
        citation = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
        name = chunk.name or ""
        label = f" ({name})" if name else ""
        context_parts.append(f"[{i}] {citation}{label} [relevance: {score:.3f}]\n```{chunk.language}\n{chunk.content}\n```")

    context = "\n\n".join(context_parts)

    return f"""You are a code analysis assistant. Answer the question using ONLY the provided code context.

## Context

{context}

## Question

{question}

## Rules

- Answer only from the provided context
- Cite sources as [file_path:line_start-line_end] inline
- If context is insufficient, explicitly say what's missing
- Include relevant code snippets in your answer
- Be concise but thorough"""


def generate_answer(question: str, chunks: list[tuple[Chunk, float]]) -> str:
    prompt = _build_prompt(question, chunks)
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content or ""


def stream_answer(question: str, chunks: list[tuple[Chunk, float]]) -> Iterator[str]:
    prompt = _build_prompt(question, chunks)
    stream = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2048,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content
