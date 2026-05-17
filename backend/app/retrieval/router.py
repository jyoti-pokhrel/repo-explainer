import re

from backend.app.ingestion.metadata import RepoMetadata

METADATA_KEYWORDS = [
    r"\borm\b",
    r"\bdatabase\b",
    r"\bdb\b",
    r"\bframework\b",
    r"\blibrary\b",
    r"\blanguage\b",
    r"\bstack\b",
    r"\btech\b",
    r"\bdependency\b",
    r"\bpackage\b",
    r"\btool\b",
    r"\bwhat auth\b",
    r"\bwhich auth\b",
    r"\bwhat authentication\b",
    r"\bwhich authentication\b",
    r"\bhow many files\b",
    r"\bproject structure\b",
    r"\bwhat does this repo\b",
    r"\bwhat is this repo\b",
    r"\bwhat is this project\b",
    r"\bwhat does this project\b",
    r"\bdescribe this repo\b",
    r"\bdescribe this project\b",
    r"\bsummary\b",
    r"\boverview\b",
    r"\bpackage manager\b",
    r"\bbuild tool\b",
]

RAG_PREFIXES = [
    "explain",
    "how does",
    "how do",
    "how is",
    "how are",
    "why does",
    "why do",
    "walk through",
    "walk me through",
]

METADATA_PATTERN = re.compile("|".join(METADATA_KEYWORDS), re.IGNORECASE)
RAG_PREFIX_PATTERN = re.compile(r"^\s*(" + "|".join(RAG_PREFIXES) + r")\b", re.IGNORECASE)


class QueryResult:
    METADATA = "metadata"
    RAG = "rag"


def classify_query(question: str) -> str:
    if RAG_PREFIX_PATTERN.match(question):
        return QueryResult.RAG
    if METADATA_PATTERN.search(question):
        return QueryResult.METADATA
    return QueryResult.RAG


def answer_metadata_query(question: str, metadata: RepoMetadata) -> str:
    q = question.lower()

    if any(kw in q for kw in ["orm", "object relational", "object-relational"]):
        if metadata.orms:
            return f"This project uses: {', '.join(metadata.orms)}."
        return "No ORM detected in this project's dependencies."

    if any(kw in q for kw in ["database", "db", "data store", "datastore"]):
        if metadata.databases:
            return f"This project uses: {', '.join(metadata.databases)}."
        return "No specific database detected in this project's dependencies."

    if any(kw in q for kw in ["framework", "web framework", "backend framework", "frontend framework"]):
        if metadata.frameworks:
            return f"This project uses: {', '.join(metadata.frameworks)}."
        return "No major framework detected in this project's dependencies."

    if any(kw in q for kw in ["auth", "authentication", "authorization", "login"]):
        if metadata.auth_methods:
            return f"This project uses: {', '.join(metadata.auth_methods)}."
        return "No specific authentication library detected."

    if any(kw in q for kw in ["language", "programming language", "written in"]):
        if metadata.languages:
            return f"This project is written in: {', '.join(metadata.languages)}."
        return "Could not determine the primary language."

    if any(kw in q for kw in ["package manager", "build tool", "dependency manager"]):
        if metadata.package_managers:
            return f"This project uses: {', '.join(metadata.package_managers)}."
        return "No package manager detected."

    if any(kw in q for kw in ["how many files", "file count", "number of files"]):
        return f"This project has {metadata.file_count} indexed source files ({metadata.total_lines:,} total lines)."

    if any(kw in q for kw in ["describe", "what is this", "summary", "overview", "what does this"]):
        parts = []
        if metadata.project_name:
            parts.append(f"**Project**: {metadata.project_name}")
        if metadata.description:
            parts.append(f"**Description**: {metadata.description}")
        if metadata.languages:
            parts.append(f"**Languages**: {', '.join(metadata.languages)}")
        if metadata.frameworks:
            parts.append(f"**Frameworks**: {', '.join(metadata.frameworks)}")
        if metadata.orms:
            parts.append(f"**ORMs**: {', '.join(metadata.orms)}")
        if metadata.databases:
            parts.append(f"**Databases**: {', '.join(metadata.databases)}")
        if metadata.auth_methods:
            parts.append(f"**Auth**: {', '.join(metadata.auth_methods)}")
        parts.append(f"**Files**: {metadata.file_count} source files ({metadata.total_lines:,} lines)")
        if metadata.config_files:
            parts.append(f"**Config files**: {', '.join(metadata.config_files)}")
        return "\n".join(parts) if parts else "No metadata available for this project."

    if metadata.orms or metadata.databases or metadata.frameworks:
        parts = []
        if metadata.orms:
            parts.append(f"ORMs: {', '.join(metadata.orms)}")
        if metadata.databases:
            parts.append(f"Databases: {', '.join(metadata.databases)}")
        if metadata.frameworks:
            parts.append(f"Frameworks: {', '.join(metadata.frameworks)}")
        if metadata.auth_methods:
            parts.append(f"Auth: {', '.join(metadata.auth_methods)}")
        return "Based on the project's dependencies:\n" + "\n".join(parts)

    return "No specific metadata found for this project. Try asking about the code structure or how specific features work."
