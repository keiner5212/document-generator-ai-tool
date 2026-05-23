# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [0.3.0] — 2026-05-23

### Added
- **Cover page** (`pdf_add_cover_page`) — full-bleed canvas cover with stripe, split, and minimal styles
- **Section divider** (`pdf_add_section_divider`) — four styles: line, bar, underline, diamond
- **Key metrics** (`pdf_add_key_metrics`) — row(s) of highlighted KPI boxes
- **Two-column layout** (`pdf_add_two_column`) — side-by-side paragraph blocks
- **Code block** (`pdf_add_code_block`) — monospace code with background, border, and caption
- **Banner** (`pdf_add_banner`) — full-width colored strip with centered text
- **5 new palettes**: Golden Luxury, Nordic Ice, Warm Cream, Cyber Neon, Wine Deep (total: 17)
- **Cursor skill file** (`.cursor/skills/pdf_mcp/SKILL.md`) — AI decoration playbook
- **GitHub project files**: `.gitignore`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, CI workflow
- Examples: `build_modern_report.py`, `build_certificate.py`

### Changed
- `session.py`: added `cover_page` state, `CoverPageFlowable`, `SectionDivider`, `BannerFlowable`, `CodeBlockFlowable`
- `styles.py`: converted THEMES colors from objects to hex strings for easier serialization
- MCP server instructions updated to reflect new tools

## [0.2.0] — 2026-05-23

### Added
- **uv project** (`pyproject.toml`) replaces `requirements.txt`
- **Template system** — save/load/render JSON templates with `{{variable}}` substitution
- **Color palette system** — 12 built-in palette JSON files
- New tools: `pdf_list_palettes`, `pdf_apply_palette`, `pdf_export_palette`, `pdf_create_palette_from_colors`
- New tools: `pdf_list_templates`, `pdf_render_template`, `pdf_save_template`, `pdf_inspect_template`
- `_replay_log` in `PDFSession` for template serialization
- Built-in templates: Invoice, Service Contract, Executive Report
- `.cursor/mcp.json` using `uv run`

## [0.1.0] — 2026-05-23

### Added
- Initial MCP server with FastMCP
- `PDFSession` with ReportLab backend
- Tools: create/save/inspect document, header, footer, watermark, page numbers
- Content tools: heading, paragraph, bullet/numbered list, table, colored box, spacer, horizontal line, page break
- Media tools: insert image, QR code
- Signature placeholder (1–4 boxes, row/column layout)
- PDF reader: metadata, text extraction, page dimensions
- 4 built-in themes: default, corporate, minimal, elegant
