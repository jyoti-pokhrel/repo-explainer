import re

from tree_sitter import Language, Parser, Node, Query, QueryCursor

import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_go
import tree_sitter_java
import tree_sitter_c
import tree_sitter_cpp

from .models import Chunk, FileDocument

LANGUAGES = {
    "python": Language(tree_sitter_python.language()),
    "javascript": Language(tree_sitter_javascript.language()),
    "typescript": Language(tree_sitter_typescript.language_typescript()),
    "go": Language(tree_sitter_go.language()),
    "java": Language(tree_sitter_java.language()),
    "c": Language(tree_sitter_c.language()),
    "cpp": Language(tree_sitter_cpp.language()),
}

LANGUAGE_QUERY = {
    "python": {
        "function": "(function_definition) @func",
        "class": "(class_definition) @cls",
    },
    "javascript": {
        "function": """
            [
                (function_declaration) @func
                (method_definition) @func
                (arrow_function) @func
                (function_expression) @func
            ]
        """,
        "class": "(class_declaration) @cls",
    },
    "typescript": {
        "function": """
            [
                (function_declaration) @func
                (method_definition) @func
                (arrow_function) @func
                (function_expression) @func
            ]
        """,
        "class": "(class_declaration) @cls",
    },
    "go": {
        "function": "(function_declaration) @func",
        "class": "(type_declaration) @cls",
    },
    "java": {
        "function": """
            [
                (method_declaration) @func
                (constructor_declaration) @func
            ]
        """,
        "class": "(class_declaration) @cls",
    },
    "c": {
        "function": "(function_definition) @func",
        "class": "",
    },
    "cpp": {
        "function": """
            [
                (function_definition) @func
                (function_declarator) @func
            ]
        """,
        "class": "(class_specifier) @cls",
    },
}

FALLBACK_PATTERNS = {
    "python": [
        (r"^(async\s+)?def\s+(\w+)\s*\(", "function"),
        (r"^class\s+(\w+)", "class"),
    ],
    "javascript": [
        (r"^(export\s+)?(async\s+)?function\s+(\w+)\s*\(", "function"),
        (r"^(export\s+)?class\s+(\w+)", "class"),
        (r"^(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\(", "function"),
    ],
    "typescript": [
        (r"^(export\s+)?(async\s+)?function\s+(\w+)\s*\(", "function"),
        (r"^(export\s+)?class\s+(\w+)", "class"),
        (r"^(export\s+)?(const|let|var)\s+(\w+)\s*[:=].*=>", "function"),
    ],
    "go": [
        (r"^func\s+(\(\w+\s+\*\w+\)\s+)?(\w+)\s*\(", "function"),
        (r"^type\s+(\w+)\s+struct", "class"),
    ],
    "java": [
        (r"^\s*(public|private|protected|static|\s)+[\w<>\[\]\s]+\s+(\w+)\s*\(", "function"),
        (r"^\s*(public|private|protected|abstract|\s)+class\s+(\w+)", "class"),
    ],
    "c": [
        (r"^[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{", "function"),
    ],
    "cpp": [
        (r"^[\w\s\*:&<>\~]+\s+(\w+)\s*\([^)]*\)\s*(const\s*)?\{", "function"),
        (r"^(class|struct)\s+(\w+)", "class"),
    ],
}


def chunk_document(doc: FileDocument) -> list[Chunk]:
    if doc.language == "markdown":
        return _chunk_markdown(doc)

    if not doc.content.strip():
        return [_single_chunk(doc)]

    if doc.language in LANGUAGES:
        chunks = _chunk_with_tree_sitter(doc)
        if chunks:
            return chunks
        return _chunk_with_regex(doc)

    return [_single_chunk(doc)]


def _chunk_with_tree_sitter(doc: FileDocument) -> list[Chunk]:
    language = LANGUAGES.get(doc.language)
    query_config = LANGUAGE_QUERY.get(doc.language)
    if not language or not query_config:
        return []

    parser = Parser(language)
    source = doc.content.encode("utf-8")

    try:
        tree = parser.parse(source)
    except Exception:
        return []

    root = tree.root_node
    if root.has_error:
        return []

    chunks: list[Chunk] = []

    for chunk_type, query_str in query_config.items():
        if not query_str.strip():
            continue

        try:
            query = Query(language, query_str)
        except Exception:
            continue

        cursor = QueryCursor(query)
        captures = cursor.captures(root)
        if not captures:
            continue

        for capture_name, nodes in captures.items():
            for node in nodes:
                text = node.text.decode("utf-8")
                name = _extract_name(node, doc.language, chunk_type)
                chunks.append(Chunk(
                    content=text,
                    file_path=doc.file_path,
                    chunk_type=chunk_type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    name=name,
                    language=doc.language,
                ))

    return chunks


def _extract_name(node: Node, language: str, chunk_type: str) -> str | None:
    text = node.text.decode("utf-8")
    lines = text.split("\n")
    first_line = lines[0].strip()

    patterns = {
        "python": {
            "function": r"^(async\s+)?def\s+(\w+)",
            "class": r"^class\s+(\w+)",
        },
        "javascript": {
            "function": r"^(export\s+)?(async\s+)?function\s+(\w+)|^(const|let|var)\s+(\w+)",
            "class": r"^(export\s+)?class\s+(\w+)",
        },
        "typescript": {
            "function": r"^(export\s+)?(async\s+)?function\s+(\w+)|^(export\s+)?(const|let|var)\s+(\w+)",
            "class": r"^(export\s+)?class\s+(\w+)",
        },
        "go": {
            "function": r"^func\s+(\(\w+\s+\*\w+\)\s+)?(\w+)",
            "class": r"^type\s+(\w+)",
        },
        "java": {
            "function": r"[\w<>\[\]]+\s+(\w+)\s*\(",
            "class": r"class\s+(\w+)",
        },
        "c": {
            "function": r"[\w\s\*]+\s+(\w+)\s*\(",
        },
        "cpp": {
            "function": r"[\w\s\*:&<>~]+\s+(\w+)\s*\(",
            "class": r"^(class|struct)\s+(\w+)",
        },
    }

    lang_patterns = patterns.get(language, {})
    pattern = lang_patterns.get(chunk_type)
    if not pattern:
        return None

    match = re.search(pattern, first_line)
    if match:
        groups = [g for g in match.groups() if g]
        return groups[-1] if groups else None
    return None


def _chunk_with_regex(doc: FileDocument) -> list[Chunk]:
    patterns = FALLBACK_PATTERNS.get(doc.language, [])
    if not patterns:
        return [_single_chunk(doc)]

    lines = doc.content.split("\n")
    chunks: list[Chunk] = []

    matches: list[tuple[int, int, str, str]] = []
    for i, line in enumerate(lines):
        for pattern, chunk_type in patterns:
            m = re.match(pattern, line)
            if m:
                groups = [g for g in m.groups() if g]
                name = groups[-1] if groups else None
                matches.append((i, chunk_type, name or "unknown", line))
                break

    if not matches:
        return [_single_chunk(doc)]

    for idx, (start_line, chunk_type, name, _) in enumerate(matches):
        end_line = matches[idx + 1][0] if idx + 1 < len(matches) else len(lines) - 1
        content = "\n".join(lines[start_line:end_line + 1])
        chunks.append(Chunk(
            content=content,
            file_path=doc.file_path,
            chunk_type=chunk_type,
            start_line=start_line + 1,
            end_line=end_line + 1,
            name=name,
            language=doc.language,
        ))

    return chunks


def _chunk_markdown(doc: FileDocument) -> list[Chunk]:
    heading_pattern = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(doc.content))

    if not matches:
        return [_single_chunk(doc)]

    chunks: list[Chunk] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(doc.content)
        content = doc.content[start:end].strip()
        heading = match.group(2).strip()
        line_num = doc.content[:start].count("\n") + 1
        end_line = doc.content[:end].count("\n") + 1

        chunks.append(Chunk(
            content=content,
            file_path=doc.file_path,
            chunk_type="markdown",
            start_line=line_num,
            end_line=end_line,
            name=heading,
            language="markdown",
        ))

    return chunks


def _single_chunk(doc: FileDocument) -> Chunk:
    return Chunk(
        content=doc.content,
        file_path=doc.file_path,
        chunk_type="block",
        start_line=1,
        end_line=doc.content.count("\n") + 1,
        language=doc.language,
    )
