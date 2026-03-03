#!/usr/bin/env python3
"""nanocode MCP server - coding agent tools exposed via Model Context Protocol"""

import glob as globlib
import json
import math
import os
import re
import subprocess
import threading
from typing import Optional

import ollama

from fastmcp import FastMCP

# Create the MCP server instance
mcp = FastMCP(
    "nanocode",
    instructions="A coding agent with tools for reading, writing, editing files, searching code, and running shell commands. Use these tools to help with coding tasks."
)


# --- File-based Vector Store for Semantic Search ---

VECTOR_STORE_FILE = ".nanocode-mcp/vector_store.json"
EMBEDDING_MODEL = "nomic-embed-text"
INDEXED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".md", ".txt", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bash", ".zsh", ".html", ".css", ".scss", ".sql", ".xml", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp"}

vector_store = {"documents": []}
index_lock = threading.Lock()
indexing_complete = False


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_vector_store() -> dict:
    """Load vector store from file if it exists."""
    if os.path.exists(VECTOR_STORE_FILE):
        try:
            with open(VECTOR_STORE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"documents": []}


def save_vector_store(store: dict) -> None:
    """Save vector store to file."""
    os.makedirs(os.path.dirname(VECTOR_STORE_FILE), exist_ok=True)
    with open(VECTOR_STORE_FILE, "w") as f:
        json.dump(store, f)


def get_file_embedding(text: str) -> Optional[list[float]]:
    """Get embedding for text using Ollama.

    Text is truncated to ~6000 chars to stay within the embedding model's
    context window (nomic-embed-text has 8192 token limit).
    """
    # Truncate to stay within embedding model context window
    # ~6000 chars ≈ 2000-3000 tokens for code
    truncated = text[:6000] if len(text) > 6000 else text
    try:
        response = ollama.embed(model=EMBEDDING_MODEL, input=truncated)
        return response["embeddings"][0]
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def index_file(filepath: str) -> Optional[dict]:
    """Index a single file, returning its document entry."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in INDEXED_EXTENSIONS:
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return None
    
    if not content.strip():
        return None
    
    embedding = get_file_embedding(content)
    if embedding is None:
        return None
    
    return {
        "path": filepath,
        "content": content[:5000],
        "embedding": embedding,
        "mtime": os.path.getmtime(filepath)
    }


def background_index() -> None:
    """Background thread to index all code files."""
    global vector_store, indexing_complete
    
    print("Starting background vectorization...")
    store = load_vector_store()
    existing_paths = {doc["path"]: doc for doc in store.get("documents", [])}
    
    base_dir = os.getcwd()
    new_docs = []
    
    for pattern in ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.json", "**/*.md", "**/*.yaml", "**/*.yml", "**/*.toml", "**/*.go", "**/*.rs", "**/*.java"]:
        for filepath in globlib.glob(os.path.join(base_dir, pattern), recursive=True):
            filepath = os.path.relpath(filepath, base_dir)
            if filepath in existing_paths:
                existing_doc = existing_paths[filepath]
                try:
                    current_mtime = os.path.getmtime(filepath)
                    if current_mtime > existing_doc.get("mtime", 0):
                        doc = index_file(filepath)
                        if doc:
                            new_docs.append(doc)
                except OSError:
                    pass
            else:
                doc = index_file(filepath)
                if doc:
                    new_docs.append(doc)
    
    if new_docs:
        store["documents"] = list(existing_paths.values()) + new_docs
        save_vector_store(store)
        vector_store = store
    
    indexing_complete = True
    print(f"Vectorization complete. Indexed {len(store.get('documents', []))} files.")


# Start background indexing
indexing_thread = threading.Thread(target=background_index, daemon=True)
indexing_thread.start()


# --- Tool implementations as MCP tools ---


@mcp.tool
def read_file(path: str, offset: int = 0, limit: Optional[int] = None) -> str:
    """Read a file with line numbers. Returns file content with numbered lines.
    
    Args:
        path: The file path to read (must be a file, not directory)
        offset: Starting line number (0-indexed, default 0)
        limit: Maximum number of lines to read (default: all lines)
    
    Returns:
        File content with line numbers prefixed
    """
    lines = open(path).readlines()
    if limit is None:
        limit = len(lines)
    selected = lines[offset : offset + limit]
    return "".join(f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected))


@mcp.tool
def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates or overwrites the file.
    
    Args:
        path: The file path to write to
        content: The content to write to the file
    
    Returns:
        "ok" on success
    """
    with open(path, "w") as f:
        f.write(content)
    return "ok"


@mcp.tool
def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Edit a file by replacing old_string with new_string.
    
    Args:
        path: The file path to edit
        old_string: The text to find and replace (must exist in file)
        new_string: The text to replace old_string with
        replace_all: If True, replace all occurrences; if False, old_string must be unique
    
    Returns:
        "ok" on success, or error message if old_string not found or not unique
    """
    text = open(path).read()
    if old_string not in text:
        return "error: old_string not found in file"
    count = text.count(old_string)
    if not replace_all and count > 1:
        return f"error: old_string appears {count} times, must be unique (use replace_all=true)"
    replacement = text.replace(old_string, new_string) if replace_all else text.replace(old_string, new_string, 1)
    with open(path, "w") as f:
        f.write(replacement)
    return "ok"


@mcp.tool
def glob_search(pattern: str, path: str = ".") -> str:
    """Find files by glob pattern, sorted by modification time (newest first).
    
    Args:
        pattern: Glob pattern to match files (e.g., "**/*.py")
        path: Base directory to search from (default: current directory)
    
    Returns:
        Newline-separated list of matching files, or "none" if no matches
    """
    full_pattern = (path + "/" + pattern).replace("//", "/")
    files = globlib.glob(full_pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )
    return "\n".join(files) or "none"


@mcp.tool
def grep_search(pattern: str, path: str = ".") -> str:
    """Search files for a regex pattern.
    
    Args:
        pattern: Regex pattern to search for
        path: Base directory to search from (default: current directory)
    
    Returns:
        Matching lines in format "filepath:line_number:content", up to 50 results
    """
    regex = re.compile(pattern)
    hits = []
    for filepath in globlib.glob(path + "/**", recursive=True):
        try:
            for line_num, line in enumerate(open(filepath), 1):
                if regex.search(line):
                    hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"


@mcp.tool
def run_bash(command: str, timeout: int = 30) -> str:
    """Run a shell command and return the output.
    
    Args:
        command: Shell command to execute
        timeout: Maximum time to wait in seconds (default: 30)
    
    Returns:
        Command output (stdout and stderr combined)
    """
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    output_lines = []
    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                output_lines.append(line)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append(f"\n(timed out after {timeout}s)")
    return "".join(output_lines).strip() or "(empty)"


@mcp.tool
def semantic_search(query: str, limit: int = 5) -> str:
    """Search the codebase using semantic (embedding-based) search.
    
    Args:
        query: Natural language query describing what to search for
        limit: Maximum number of results to return (default: 5)
    
    Returns:
        Ranked search results with file paths, similarity scores, and context snippets
    """
    global vector_store, indexing_complete
    
    query_embedding = get_file_embedding(query)
    if query_embedding is None:
        return "error: could not generate embedding for query (is Ollama running?)"
    
    docs = vector_store.get("documents", [])
    if not docs:
        if not indexing_complete:
            return "indexing in progress... please try again in a few seconds"
        return "no indexed documents found"
    
    results = []
    for doc in docs:
        sim = cosine_similarity(query_embedding, doc.get("embedding", []))
        results.append((sim, doc))
    
    results.sort(key=lambda x: x[0], reverse=True)
    top_results = results[:limit]
    
    output = []
    for score, doc in top_results:
        content = doc.get("content", "")[:800]
        path = doc.get("path", "unknown")
        output.append(f"{path} (score: {score:.3f})\n---\n{content}\n---\n")
    
    return "\n".join(output) if output else "no results found"


@mcp.tool
def reindex_codebase() -> str:
    """Manually trigger a full re-index of the codebase.
    
    Returns:
        Status message about the re-indexing operation
    """
    global vector_store, indexing_complete
    
    indexing_complete = False
    
    def reindex():
        global vector_store, indexing_complete
        save_vector_store({"documents": []})
        vector_store = {"documents": []}
        background_index()
    
    thread = threading.Thread(target=reindex, daemon=True)
    thread.start()
    
    return "re-indexing started in background..."



# --- Entry point ---

if __name__ == "__main__":
    # Run the MCP server
    # Default: stdio transport (for Claude Desktop and other MCP clients)
    # Can also use: mcp.run(transport="http", host="0.0.0.0", port=8000)
    mcp.run()