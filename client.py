#!/usr/bin/env python3
"""
nanocode CLI Client - Test client for the nanocode MCP server.

This client connects to the MCP server and provides a CLI-based agent
powered by Ollama (qwen3.5:4b) to interact with the tools.

Usage:
    python client.py

Requirements:
    pip install fastmcp openai
    ollama pull qwen3.5:4b
"""

import asyncio
import json
import sys
from openai import OpenAI
from fastmcp.client import Client

# Import the MCP server directly for in-process stdio connection
from mcp_server import mcp

# Ollama OpenAI-compatible client
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Required but unused for Ollama
)

MODEL = "qwen3.5:4b"

SYSTEM_PROMPT = """You are a helpful coding assistant with access to file system tools.

You have access to the following tools:
- read_file: Read file contents with line numbers
- write_file: Write content to a file (creates or overwrites)
- edit_file: Edit a file by replacing text
- glob_search: Find files by glob pattern (sorted by modification time)
- grep_search: Search files for regex patterns
- run_bash: Execute shell commands with timeout

Use these tools to help the user with coding tasks. Always be helpful and explain what you're doing.
When using tools, be precise with file paths and content.

IMPORTANT: When calling tools, use the exact function format. Think through each action before executing.
"""


def mcp_tools_to_openai(tools) -> list:
    """Convert MCP tools to OpenAI function format."""
    openai_tools = []
    for tool in tools:
        # Build parameters schema
        properties = {}
        required = []
        
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            schema = tool.inputSchema
            if isinstance(schema, dict):
                properties = schema.get("properties", {})
                required = schema.get("required", [])
        elif hasattr(tool, 'input_schema') and tool.input_schema:
            schema = tool.input_schema
            if isinstance(schema, dict):
                properties = schema.get("properties", {})
                required = schema.get("required", [])
        
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Call the {tool.name} tool",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
        })
    return openai_tools


async def run_agent():
    """Run the CLI agent with MCP tools and Ollama."""
    print("=" * 60)
    print("nanocode CLI Client")
    print(f"Model: {MODEL} (via Ollama)")
    print("=" * 60)
    print()
    print("Type your message and press Enter. Type 'exit' or 'quit' to stop.")
    print("Type 'tools' to list available MCP tools.")
    print()
    
    # Connect to MCP server directly (in-process, stdio mode)
    async with Client(mcp) as mcp_client:
        # Get available tools
        tools = await mcp_client.list_tools()
        openai_tools = mcp_tools_to_openai(tools)
        
        if not openai_tools:
            print("Warning: No tools found on MCP server!")
        else:
            print(f"Connected to MCP server with {len(openai_tools)} tools available.")
            print()
        
        # Conversation history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        while True:
            try:
                user_input = input("\n\033[1;36mYou:\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break
            
            if user_input.lower() == "tools":
                print("\n\033[1;33mAvailable MCP Tools:\033[0m")
                for tool in tools:
                    print(f"  - \033[1m{tool.name}\033[0m: {tool.description or 'No description'}")
                continue
            
            # Add user message to history
            messages.append({"role": "user", "content": user_input})
            
            # Agent loop - may need multiple turns for tool calls
            while True:
                try:
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=openai_tools if openai_tools else None,
                        tool_choice="auto" if openai_tools else None,
                    )
                except Exception as e:
                    print(f"\n\033[1;31mError calling Ollama:\033[0m {e}")
                    print("Make sure Ollama is running with: ollama serve")
                    print(f"And the model is pulled: ollama pull {MODEL}")
                    messages.pop()  # Remove the failed user message
                    break
                
                assistant_message = response.choices[0].message
                
                # Check if we need to make tool calls
                if assistant_message.tool_calls:
                    # Add assistant message to history
                    messages.append(assistant_message)
                    
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        print(f"\n\033[1;35m[Tool Call]\033[0m {tool_name}({tool_args})")
                        
                        try:
                            # Call MCP tool
                            result = await mcp_client.call_tool(tool_name, tool_args)
                            tool_result = result.content[0].text if result.content else ""
                            print(f"\033[1;32m[Result]\033[0m {tool_result[:500]}{'...' if len(tool_result) > 500 else ''}")
                        except Exception as e:
                            tool_result = f"Error: {str(e)}"
                            print(f"\033[1;31m[Error]\033[0m {tool_result}")
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        })
                    
                    # Continue the loop to get final response
                    continue
                
                # No tool calls - we have a final response
                if assistant_message.content:
                    print(f"\n\033[1;34mAssistant:\033[0m {assistant_message.content}")
                    messages.append(assistant_message)
                break


def main():
    """Entry point."""
    print("\nStarting nanocode CLI client...")
    print("Connecting to MCP server via stdio (in-process)...")
    
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()