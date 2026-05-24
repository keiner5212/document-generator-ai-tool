# Contributing to PDF AI Tools

**Maintainer:** Keiner Alvarado  
**License:** MIT

Thank you for considering a contribution. This project uses `uv` for dependency management.

## Development setup

```bash
git clone https://github.com/your-org/pdf-ai-tools.git
cd pdf-ai-tools
uv sync
```

## Running examples

```bash
uv run python examples/build_invoice.py
uv run python examples/build_modern_report.py
uv run python examples/build_certificate.py
```

## Running the MCP server locally

```bash
uv run python mcp_server/server.py
```

## Adding a palette

Create a JSON file in `palettes/` following this schema:

```json
{
  "name": "My Palette",
  "description": "One-line description",
  "colors": {
    "primary":    "#hex",
    "secondary":  "#hex",
    "accent":     "#hex",
    "muted":      "#hex",
    "border":     "#hex",
    "background": "#hex"
  },
  "fonts": { "body": "Helvetica", "heading": "Helvetica-Bold" },
  "sizes": { "body": 11, "h1": 22, "h2": 16, "h3": 13, "caption": 9 },
  "document": { "page_size": "A4", "margins_cm": [2.5,2.5,2.5,2.5], "page_numbers": true, "watermark": null }
}
```

Allowed PDF fonts: `Helvetica`, `Helvetica-Bold`, `Helvetica-Oblique`,
`Times-Roman`, `Times-Bold`, `Times-Italic`, `Courier`, `Courier-Bold`.

## Adding a template

Create a JSON file in `templates/`. Required keys: `name`, `description`,
`variables`, `document`, `header`, `footer`, `blocks`.
See an existing template for the exact block format.
Placeholder syntax: `{{variable_name}}`.

## Adding a tool

1. Add the function to `pdf_ai_tools/tools.py` with a clear docstring.
2. Register it in `mcp_server/server.py` with `mcp.tool()(tools.your_function)`.
3. Update the Cursor skill at `.cursor/skills/pdf_mcp/SKILL.md`.
4. Add an example to an existing or new `examples/` script.

## Code style

- Type hints on all function signatures.
- Docstrings on all public functions — the docstring is the MCP tool description.
- All tool functions return `str` (JSON via `_ok()` / `_err()`).
- Never swallow exceptions — always return `_err(str(e))`.

## Pull requests

- Keep PRs focused (one feature or fix per PR).
- Include a short description of what changed and why.
- Run existing examples to verify nothing is broken.
