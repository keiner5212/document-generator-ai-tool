# PDF AI Tools

AI-powered PDF toolkit. An MCP server exposes **35+ tools** to Cursor so an AI agent can create, style, template, and read PDF documents from a plain-language prompt.

## Features at a glance

| Category | What it does |
|---|---|
| **Document** | Create, inspect, save sessions with any page size |
| **Palettes** | 12 built-in color themes; create/export custom palettes |
| **Templates** | Save layouts as JSON; render with `{{variable}}` substitution |
| **Header / Footer** | Left / center / right zones, line, color, first-page control |
| **Content** | Headings (H1–H3), paragraphs (HTML), bullets, numbered lists |
| **Tables** | Zebra stripes, header row, custom column widths |
| **Callout boxes** | Colored border + background info boxes |
| **Media** | Inline images (PNG/JPEG), auto-generated QR codes |
| **Signatures** | Dashed placeholder boxes, 1–4 in row or column layout |
| **Decoration** | Watermark, horizontal rules, spacers, page breaks, page numbers |
| **Read PDFs** | Metadata, text extraction per page, page dimensions |

## Installation (uv)

```bash
cd /home/keiner5212/Descargas/docs
uv sync          # creates .venv and installs all deps
```

## Connect to Cursor

`.cursor/mcp.json` is already configured. After `uv sync`:

1. Open Cursor **Settings → MCP** and confirm `pdf-ai-tools` is listed.
2. Reload or restart Cursor if needed.
3. Ask the AI in natural language — it will call the right tools automatically.

## Prompt examples

```
"Create a corporate invoice for Acme Corp billing Jane Doe $4,800, save to output/invoice.pdf"

"Render the contract template for Party A='Corp X' and Party B='Client Y' with governing law of California"

"List all built-in palettes"

"Apply the ocean_blue palette and create a report PDF with a table of 3 metrics and a signature"

"Read the text from pages 1 and 2 of output/contract.pdf"

"Create a custom palette with primary=#003366, accent=#ff6600 and save to palettes/my_brand.json"
```

## Palettes (12 built-in)

| File | Name | Best for |
|---|---|---|
| `ocean_blue.json` | Ocean Blue | Professional docs, proposals |
| `corporate_slate.json` | Corporate Slate | Enterprise reports |
| `forest_green.json` | Forest Green | Sustainability, nature |
| `royal_purple.json` | Royal Purple | Luxury, creative |
| `sunset_warm.json` | Sunset Warm | Marketing, briefs |
| `midnight_dark.json` | Midnight Dark | Technical docs |
| `minimal_ink.json` | Minimal Ink | Print-ready, clean |
| `rose_gold.json` | Rose Gold | Certificates, events |
| `legal_classic.json` | Legal Classic | Contracts, legal |
| `teal_modern.json` | Teal Modern | SaaS, tech startups |
| `academic_serif.json` | Academic Serif | Papers, theses |
| `vibrant_startup.json` | Vibrant Startup | Pitch decks |

A palette JSON controls: primary/secondary/accent/muted/border/background colors, body and heading fonts, font sizes for body/H1–H3/caption, default page size and margins.

## Templates (3 built-in)

| File | Name | Variables |
|---|---|---|
| `templates/invoice.json` | Invoice | company_name, client_name, invoice_number, date, due_date, total, … |
| `templates/contract.json` | Service Contract | party_a, party_b, service, value, start_date, end_date, governing_law, … |
| `templates/report.json` | Executive Report | title, subtitle, author, department, date, summary, conclusion |

### Create your own template

```python
from pdf_ai_tools import tools
import json

# Build a document normally
r = json.loads(tools.pdf_create_document("output/draft.pdf"))
did = r["doc_id"]
tools.pdf_apply_palette(did, "teal_modern")
tools.pdf_add_heading(did, "Report: {{title}}", level=1)
tools.pdf_add_paragraph(did, "Prepared by {{author}} on {{date}}.")
tools.pdf_add_signature_placeholder(did, label="Approved by")

# Save as template (captures all blocks for replay)
tools.pdf_save_template(did, "templates/my_template.json", name="My Report")
tools.pdf_save_document(did)   # also save the actual PDF

# Later, render the template with concrete values
tools.pdf_render_template(
    "templates/my_template.json",
    "output/report_q3.pdf",
    json.dumps({"title": "Q3 Results", "author": "Alice", "date": "2026-09-30"})
)
```

## Run the server manually

```bash
uv run python mcp_server/server.py
```

## Project structure

```
pdf_ai_tools/
  __init__.py      — Public exports
  session.py       — PDFSession (mutable build state)
  styles.py        — Theme + palette style builders
  tools.py         — 35+ AI-callable tool functions
  palette.py       — Palette CRUD
  template.py      — Template save / load / render
  reader.py        — Read existing PDFs (pypdf)
palettes/          — 12 built-in color palette JSON files
templates/         — Built-in template JSON files
mcp_server/
  server.py        — FastMCP server (registers all tools)
examples/
  build_invoice.py — Direct Python usage example
.cursor/
  mcp.json         — Cursor MCP configuration (uv run)
pyproject.toml     — uv project (deps: reportlab, pypdf, fastmcp, qrcode, Pillow)
```
