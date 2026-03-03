# nanocode MCP Server

A lightweight, fast, and secure Model Context Protocol (MCP) server that exposes coding agent tools for file manipulation, code searching, and shell command execution.

## Overview

**nanocode-mcp** is an MCP server designed to give AI assistants and MCP clients the ability to interact with your local filesystem and execute shell commands. Built with [FastMCP](https://github.com/jlowin/fastmcp), it provides a streamlined set of tools for coding tasks.

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

## Installation

### Prerequisites

- Python 3.10 or higher
- `fastmcp` package

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