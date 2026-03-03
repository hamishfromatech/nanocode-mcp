# nanocode MCP Server

A lightweight, fast, and secure Model Context Protocol (MCP) server that exposes coding agent tools for file manipulation, code searching, and shell command execution.

## Overview

**nanocode-mcp** is an MCP server designed to give AI assistants and MCP clients the ability to interact with your local filesystem and execute shell commands. Built with [FastMCP](https://github.com/jlowin/fastmcp), it provides a streamlined set of tools for coding tasks.

Based on [nanocode](https://github.com/1rgs/nanocode) by 1rgs.



- **Author & Maintainer**: The A-Tech Corporation PTY LTD
- **License**: Open Source

## Features

### Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with line numbers, supports offset and limit |
| `write_file` | Write content to a file (creates or overwrites) |
| `edit_file` | Edit a file by replacing text (find and replace) |
| `glob_search` | Find files by glob pattern, sorted by modification time |
| `grep_search` | Search files for regex patterns |
| `run_bash` | Execute shell commands with timeout support |
| `semantic_search` | Search codebase using natural language queries (requires Ollama) |
| `reindex_codebase` | Manually trigger a full re-index of the codebase |

### Semantic Search

The `semantic_search` tool enables natural language code search using vector embeddings. It indexes your codebase in the background and allows you to search for code using descriptive queries.

**Requirements:**
- [Ollama](https://ollama.com/) installed and running
- `nomic-embed-text` model: `ollama pull nomic-embed-text`

**How it works:**
- On startup, the server indexes supported file types in the background
- Index is persisted to `.nanocode-mcp/vector_store.json`
- Truncates files to ~6000 chars to stay within embedding model context limits

**Supported file types:** `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.json`, `.md`, `.txt`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.sh`, `.bash`, `.zsh`, `.html`, `.css`, `.scss`, `.sql`, `.xml`, `.go`, `.rs`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`
| `semantic_search` | Search codebase using natural language queries (requires Ollama) |
| `reindex_codebase` | Manually trigger a full re-index of the codebase |

### Semantic Search

The server includes a semantic search feature that indexes your codebase and enables natural language queries. It uses local embeddings via Ollama with the `nomic-embed-text` model.

**Setup:**
1. Install Ollama: https://ollama.com/
2. Pull the embedding model:
   ```bash
   ollama pull nomic-embed-text
   ```

The server automatically indexes supported file types in the background on startup. Indexed files include: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.json`, `.md`, `.txt`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.sh`, `.bash`, `.zsh`, `.html`, `.css`, `.scss`, `.sql`, `.xml`, `.go`, `.rs`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`

**Example:**
```
semantic_search("find authentication logic")
```

## Installation

### Prerequisites

- Python 3.10 or higher
- `fastmcp` package
- [Ollama](https://ollama.com/) with `nomic-embed-text` model (for semantic search)

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   > **Note:** `openai` is only required for the CLI test client.

3. Install fastmcp:
   ```bash
   pip install fastmcp
   ```

## Usage

### Running the Server

Start the MCP server using stdio transport (default):

```bash
python mcp_server.py
```

For HTTP transport:

```bash
python -c "from mcp_server import mcp; mcp.run(transport='http', host='0.0.0.0', port=8000)"
```

### Integrating with MCP Clients

#### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nanocode": {
      "command": "python",
      "args": ["C:/path/to/mcp_server.py"]
    }
  }
}
```

#### Other MCP Clients

For clients that support MCP over stdio, simply run:

```bash
python /path/to/mcp_server.py
```

### CLI Test Client

A CLI-based test client is included for easy testing with [Ollama](https://ollama.com/).

**Prerequisites:**
1. Install Ollama: https://ollama.com/
2. Pull the model:
   ```bash
   ollama pull qwen2.5:4b
   ```
3. Install additional dependency:
   ```bash
   pip install openai
   ```

**Run the client:**
```bash
python client.py
```

**Features:**
- Interactive chat interface with colored output
- Automatic tool calling via the AI agent
- Type `tools` to list available MCP tools
- Type `exit` or `quit` to stop

**Example session:**
```
You: List all Python files in the current directory

[Tool Call] glob_search({'pattern': '**/*.py'})
[Result] ./mcp_server.py
         ./client.py

Assistant: I found 2 Python files in the current directory:
- mcp_server.py
- client.py
```

## Tool Reference

### `read_file`

Read file contents with line numbers.

**Parameters:**
- `path` (string): File path to read
- `offset` (int, optional): Starting line number (0-indexed, default: 0)
- `limit` (int, optional): Maximum lines to read (default: all)

**Returns:** File content with line numbers prefixed

---

### `write_file`

Write content to a file, creating or overwriting it.

**Parameters:**
- `path` (string): File path to write
- `content` (string): Content to write

**Returns:** `"ok"` on success

---

### `edit_file`

Edit a file by replacing text.

**Parameters:**
- `path` (string): File path to edit
- `old_string` (string): Text to find and replace (must exist)
- `new_string` (string): Replacement text
- `replace_all` (bool, optional): Replace all occurrences (default: false)

**Returns:** `"ok"` on success, error message if not found or not unique

---

### `glob_search`

Find files matching a glob pattern, sorted by modification time (newest first).

**Parameters:**
- `pattern` (string): Glob pattern (e.g., `**/*.py`)
- `path` (string, optional): Base directory (default: current directory)

**Returns:** Newline-separated list of matching files

---

### `grep_search`

Search files for a regex pattern.

**Parameters:**
- `pattern` (string): Regex pattern to search
- `path` (string, optional): Base directory (default: current directory)

**Returns:** Matching lines as `filepath:line_number:content` (max 50 results)

---

### `run_bash`

Execute a shell command.

**Parameters:**
- `command` (string): Shell command to execute
- `timeout` (int, optional): Timeout in seconds (default: 30)

**Returns:** Command output (stdout and stderr combined)

---

### `semantic_search`

Search the codebase using natural language queries via vector embeddings.

**Parameters:**
- `query` (string): Natural language query describing what to search for
- `limit` (int, optional): Maximum results to return (default: 5)

**Returns:** Ranked search results with file paths, similarity scores, and context snippets

**Requires:** Ollama running with `nomic-embed-text` model

---

### `reindex_codebase`

Manually trigger a full re-index of the codebase for semantic search.

**Parameters:** None

**Returns:** Status message about the re-indexing operation

---

### `semantic_search`

Search the codebase using natural language queries via vector embeddings.

**Parameters:**
- `query` (string): Natural language query describing what to search for
- `limit` (int, optional): Maximum results to return (default: 5)

**Returns:** Ranked search results with file paths, similarity scores, and context snippets

**Requires:** Ollama running with `nomic-embed-text` model

---

### `reindex_codebase`

Manually trigger a full re-index of the codebase for semantic search.

**Parameters:** None

**Returns:** Status message about the re-indexing operation

---

### `semantic_search`

Search the codebase using natural language queries.

**Parameters:**
- `query` (string): Natural language query describing what to search for
- `limit` (int, optional): Maximum results to return (default: 5)

**Returns:** Ranked search results with file paths, similarity scores, and context snippets

**Requires:** Ollama with `nomic-embed-text` model running

---

### `reindex_codebase`

Manually trigger a full re-index of the codebase.

**Parameters:** None

**Returns:** Status message about the re-indexing operation

**Note:** Re-indexing runs in the background and clears the existing index

## Security Considerations

⚠️ **Warning**: This server provides direct filesystem access and shell command execution capabilities. Use with caution:

- Only connect to trusted MCP clients
- Review commands before execution in sensitive environments
- Consider running in a containerized or sandboxed environment
- The `run_bash` tool has timeout protection but no command restrictions

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

Open Source - see LICENSE file for details.

---

**Made with ❤️ by [The A-Tech Corporation PTY LTD](https://github.com/hamishfromatech)**