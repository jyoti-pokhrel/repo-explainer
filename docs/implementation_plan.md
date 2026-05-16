# CodeSage Implementation Plan

> Build each phase fully before moving to the next. Understand every line you write. No copy-pasting code you cannot explain.

# Phase 1 — Foundations & Setup
~2–3 days · understand before you build

## Read: What is Hybrid RAG?

Learn:
- BM25 sparse retrieval 
- Dense vector retrieval
- Why hybrid retrieval works better
- Reciprocal Rank Fusion (RRF)

Key ideas:
- Sparse search = keyword/token matching
- Dense search = semantic similarity
- Hybrid = combines precision + semantic understanding
- RRF merges rankings from both systems

Do not code yet.

## Project Structure

Recommended structure:

```txt
codesage/
├── app/
├── ingestion/
├── retrieval/
├── api/
├── tests/
├── requirements.txt
├── .env
└── README.md
```

Setup:
- Python virtual environment
- requirements.txt
- .env for API keys
- Git repository

## GitHub Repo Ingestion

Goal:
- Accept a GitHub repository URL
- Clone repository locally
- Parse code files
- Split code into chunks for indexing

Include:
- .py
- .js
- .ts
- .md

Chunking strategy:
- Per function
- Per class
- Small logical blocks

Recommended tools:
- GitPython
- tree-sitter

Fallback:
- Simple regex parsing initially

### Stack
- Python
- GitPython
- tree-sitter

# Phase 2 — Sparse + Dense Indexing
~3–4 days · the core of hybrid RAG

## Build BM25 Sparse Search

Tools:
- rank_bm25

Tasks:
- Tokenize code chunks
- Build BM25 index
- Return top-k results with scores

Test query:

```txt
authentication
```

Expected:
- Auth-related files/functions rank highly

Understand:
- TF-IDF style retrieval
- Exact token relevance
- Why BM25 works well for codebases

## Build Dense Vector Search

Tools:
- sentence-transformers
- Pinecone

Embedding model:

```txt
all-MiniLM-L6-v2
```

Tasks:
- Generate embeddings for chunks
- Store vectors in Pinecone
- Attach metadata

Metadata examples:
- file path
- function name
- line numbers

Why this matters:
- Dense search captures semantic meaning
- Useful when wording differs from implementation

## Merge Results with RRF

Important interview topic.

Implement Reciprocal Rank Fusion manually.

Formula:

```txt
score = Σ 1 / (k + rank)
```

Typical:

```txt
k = 60
```

Why RRF:
- Simple
- Extremely effective
- Combines sparse + dense rankings cleanly

Do not use a library for this.

Write it yourself.

### Stack
- rank_bm25
- sentence-transformers
- Pinecone (free tier)

# Phase 3 — Reranking + Answer Generation
~2–3 days · quality over speed

## Add Cohere Reranking

Tool:
- Cohere Rerank API

Pipeline:
1. Retrieve top 20 chunks using hybrid search
2. Send to Cohere reranker
3. Return top 5 most relevant chunks

Understand:
- Bi-encoder retrieval = fast
- Cross-encoder reranking = accurate

Why reranking matters:
- Retrieval gets candidates
- Reranker improves final relevance

## Answer Generation + Citations

Tool:
- Groq API with Llama 3.1

Pipeline:
1. Send top chunks to LLM
2. Generate answer
3. Include citations

Citation format example:

```txt
auth/login.py:120-148
```

Prompt requirements:
- Answer only from provided context
- Cite sources
- Mention uncertainty if context is insufficient

Recommended model:

```txt
Llama 3.1 70B
```

### Stack
- Cohere Rerank
- Groq API
- Llama 3.1

# Phase 4 — FastAPI Wrapper
~2 days · clean API design

## Build Two Endpoints Only

### POST /index

Input:

```json
{
  "repo_url": "https://github.com/user/repo"
}
```

Responsibility:
- Clone repo
- Parse files
- Build indexes
- Store vectors

### POST /query

Input:

```json
{
  "question": "How does authentication work?"
}
```

Output:
- Final answer
- Citations
- Relevant files

## Async Indexing + Status Polling

Indexing can take time.

Use:
- FastAPI BackgroundTasks

Add endpoint:

```txt
GET /status/{job_id}
```

Frontend polls:
- pending
- processing
- completed
- failed

This improves UX significantly.

### Stack
- FastAPI
- Pydantic
- BackgroundTasks

# Phase 5 — Deploy + Portfolio
~1–2 days · make it real

## Deploy to Render

Free deployment.

Steps:
1. Push project to GitHub
2. Connect repo to Render
3. Add environment variables

Environment variables:

```txt
GROQ_API_KEY=
COHERE_API_KEY=
PINECONE_API_KEY=
```

Result:
- Public live API
- Shareable portfolio project

## Write a README That Gets You Hired

Include:

### Project Overview
Explain what the system does.

### Architecture Diagram
Show:
- ingestion
- sparse retrieval
- dense retrieval
- RRF
- reranking
- generation

### Why Hybrid RAG?
Explain:
- BM25 strengths
- Dense retrieval strengths
- Why combining both improves retrieval quality

### Tradeoffs
Examples:
- Pinecone vs local vector DB
- Accuracy vs latency
- Chunk size decisions

### Demo
Add:
- live URL
- screenshots
- sample queries

### What Recruiters Look For
Show understanding of:
- retrieval systems
- embeddings
- ranking
- reranking
- system design
- API architecture

### Stack
- Render
- GitHub

# Final Goal

By the end, you will have built:
- A real hybrid RAG system
- Sparse retrieval
- Dense retrieval
- RRF fusion
- Reranking
- Code-aware ingestion
- FastAPI backend
- Production deployment

This is much stronger than a basic chatbot wrapper project.