# PDF AI Tools

> **Author:** [Keiner Alvarado](https://github.com/keiner5212) · **License:** MIT

AI-powered PDF creation toolkit. An MCP server exposes **40+ tools** to Cursor so an agent can build beautiful, modern, or strictly professional PDFs from a plain-language prompt — with cover pages, palettes, templates, decoration, images, QR codes, and signature blocks.

[![CI](https://github.com/your-org/pdf-ai-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/pdf-ai-tools/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Features

| Category | Tools |
|---|---|
| **Document lifecycle** | Create, inspect, save, list sessions |
| **Cover page** | Full-bleed canvas cover (stripe / split / minimal styles) |
| **Palettes** | 17 built-in color themes; create, export, import custom palettes |
| **Templates** | Save layouts as JSON; render with `{{variable}}` substitution |
| **Header / Footer** | Left/center/right zones, line decoration, first-page control |
| **Typography** | H1–H3 headings, paragraphs (HTML), bullet/numbered lists |
| **Tables** | Header row, zebra stripes, custom column widths |
| **Decoration** | Section dividers (4 styles), banners, callout boxes, code blocks |
| **Layout** | Two-column text, key metrics row, watermark, page numbers |
| **Media** | Inline images (PNG/JPEG), auto-generated QR codes |
| **Signatures** | Dashed placeholder boxes, 1–4 per row or column |
| **Read PDFs** | Metadata, text extraction per page, page dimensions |

---

## Installation

```bash
git clone https://github.com/your-org/pdf-ai-tools.git
cd pdf-ai-tools
uv sync          # creates .venv, installs all dependencies
```

---

## Cursor MCP Integration

`.cursor/mcp.json` is already configured. After `uv sync`:

1. Open **Cursor Settings → MCP** — confirm `pdf-ai-tools` appears.
2. Restart Cursor if needed.
3. Chat with the AI in natural language.

The AI reads `.cursor/skills/pdf_mcp/SKILL.md` automatically — it contains the full decoration playbook including palette-to-document-type matching, design principles, and tool combination recipes.

**Example prompts:**
```
"Create a modern startup pitch deck cover with the vibrant_startup palette"

"Generate a legal contract between Acme Corp and Client LLC with two signatures"

"Build an executive report with cover page, KPI metrics row, and financial table"

"Create an award certificate with golden luxury styling"

"Read the text from pages 1–3 of my contract.pdf and summarize it"
```

---

## 17 Built-in Palettes

| Palette | Personality | Best for |
|---|---|---|
| `ocean_blue` | Professional, calm | Proposals, reports |
| `corporate_slate` | Formal, modern | Enterprise, invoices |
| `forest_green` | Earthy, natural | Sustainability, ESG |
| `royal_purple` | Luxury, creative | Premium reports |
| `sunset_warm` | Energetic, warm | Marketing, briefs |
| `midnight_dark` | Technical, dark | Dev docs, terminals |
| `minimal_ink` | Ultra-clean, print | Legal, academic |
| `rose_gold` | Elegant, feminine | Certificates, events |
| `legal_classic` | Serif, formal | Contracts, legal |
| `teal_modern` | Fresh, tech | SaaS, startups |
| `academic_serif` | Scholarly | Papers, theses |
| `vibrant_startup` | Bold, indigo/fuchsia | Pitch decks |
| `golden_luxury` | Gold/dark | Awards, certificates |
| `nordic_ice` | Pale, Scandinavian | Clean minimalism |
| `warm_cream` | Beige, artisan | Editorial, zines |
| `cyber_neon` | Dark, electric green | Cyberpunk, gaming |
| `wine_deep` | Burgundy, serif | Restaurants, menus |

---

## 3 Built-in Templates

| Template | Variables | Palette |
|---|---|---|
| `invoice` | company_name, client_name, invoice_number, date, due_date, total… | corporate_slate |
| `contract` | party_a, party_b, service, value, start_date, end_date, governing_law… | legal_classic |
| `report` | title, subtitle, author, department, date, summary, conclusion | ocean_blue |

### Render a template

```bash
# From Cursor chat:
"Render the invoice template for Acme Corp billing Jane Doe $4,800 as output/invoice.pdf"

# Or in Python:
uv run python -c "
from pdf_ai_tools import tools
import json
tools.pdf_render_template('invoice', 'output/invoice.pdf', json.dumps({
    'company_name': 'Acme Corp',
    'client_name': 'Jane Doe',
    'invoice_number': 'INV-042',
    'date': '2026-05-23',
    'due_date': '2026-06-23',
    'total': '\$4,800',
}))
"
```

---

## Run Examples

```bash
uv run python examples/build_invoice.py        # corporate invoice
uv run python examples/build_modern_report.py  # full report with cover + KPIs
uv run python examples/build_certificate.py    # golden luxury award certificate
```

---

## Run the MCP Server Manually

```bash
uv run python mcp_server/server.py
```

---

## Project Structure

```
pdf_ai_tools/
  session.py    — PDFSession + Flowables (CoverPage, SectionDivider, Banner, CodeBlock)
  styles.py     — Theme + palette style builders
  tools.py      — 40+ AI-callable tool functions
  palette.py    — Palette CRUD (17 built-in JSON files)
  template.py   — Template save / load / render engine
  reader.py     — Read existing PDFs (pypdf)

palettes/       — 17 built-in color palette JSON files
templates/      — 3 built-in template JSON files
examples/       — build_invoice.py, build_modern_report.py, build_certificate.py
mcp_server/
  server.py     — FastMCP server (40+ tools registered)

.cursor/
  mcp.json                    — Cursor MCP config (uv run)
  skills/pdf_mcp/SKILL.md     — AI decoration playbook

.github/workflows/ci.yml  — GitHub Actions CI
pyproject.toml             — uv project definition
CHANGELOG.md               — Version history
CONTRIBUTING.md            — How to add palettes, templates, tools
LICENSE                    — MIT
```

---

## Decoration Tools Reference

### New in v0.3

| Tool | Description |
|---|---|
| `pdf_add_cover_page` | Full-bleed canvas cover with title, subtitle, logo (stripe/split/minimal) |
| `pdf_add_section_divider` | Decorative divider: line, bar, underline, or diamond style |
| `pdf_add_key_metrics` | Row(s) of KPI boxes showing value + label |
| `pdf_add_two_column` | Side-by-side paragraph blocks |
| `pdf_add_code_block` | Monospace code with background and caption |
| `pdf_add_banner` | Full-width colored strip with centered text |

### Core tools

`pdf_add_heading` · `pdf_add_paragraph` · `pdf_add_table` · `pdf_add_colored_box`
`pdf_add_bullet_list` · `pdf_add_numbered_list` · `pdf_add_signature_placeholder`
`pdf_insert_image` · `pdf_add_qr_code` · `pdf_set_watermark`
`pdf_configure_header` · `pdf_configure_footer` · `pdf_enable_page_numbers`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Author

**Keiner Alvarado** — [github.com/keiner5212](https://github.com/keiner5212)

MIT License — see [LICENSE](LICENSE).
