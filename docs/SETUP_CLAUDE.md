# Connecting to Claude Desktop

Claude Desktop reads MCP server configuration from:

| OS | Config path |
|---|---|
| Linux | `~/.config/claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

## Setup

1. Install dependencies:

```bash
cd /home/keiner5212/Descargas/docs
uv sync
```

2. Add the server to Claude's config (replace the path with your actual project path):

```json
{
  "mcpServers": {
    "pdf-ai-tools": {
      "command": "uv",
      "args": ["run", "python", "mcp_server/server.py"],
      "cwd": "/home/keiner5212/Descargas/docs"
    }
  }
}
```

3. Restart Claude Desktop. The `pdf-ai-tools` server should appear in the tool list.

## Quick test

Ask Claude:

> "List all available PDF palettes"

It should call `pdf_list_palettes` and return the 17 built-in palettes.

---

# Connecting to OpenCode

`opencode.json` is already configured at the project root. Run:

```bash
cd /home/keiner5212/Descargas/docs
opencode
```

OpenCode will automatically pick up the `opencode.json` and start the MCP server.

Ask:

> "Create a modern report PDF with the ocean_blue palette and save it to output/report.pdf"
