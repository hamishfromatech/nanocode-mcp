#!/usr/bin/env python3
"""nanocode MCP server - coding agent tools exposed via Model Context Protocol"""

import glob as globlib
import os
import re
import subprocess
from typing import Optional

from fastmcp import FastMCP

# Create the MCP server instance
mcp = FastMCP(
    "nanocode",
    instructions="A coding agent with tools for reading, writing, editing files, searching code, and running shell commands. Use these tools to help with coding tasks."
)


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


# --- Entry point ---

if __name__ == "__main__":
    # Run the MCP server
    # Default: stdio transport (for Claude Desktop and other MCP clients)
    # Can also use: mcp.run(transport="http", host="0.0.0.0", port=8000)
    mcp.run()