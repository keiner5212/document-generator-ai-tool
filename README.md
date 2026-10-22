# pdf-ai-tools

Version 0.4.0.

[![Python](https://img.shields.io/badge/python-%3E%3D3.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

PDF tools for an agent. Create, decorate, and read documents through MCP tools. Reads return text and metadata. `pdf_save_document` writes the file and closes the session.

## Install

Download the archive for your OS. No Python install. Steps, skill folder, and the MCP `command` path: [setup/INSTALL.md](setup/INSTALL.md).

The download is a folder. Point the agent at the executable inside it. The program does not unpack into `/tmp`.

Copy `setup/pdf-ai-tools/` into the agent's skills directory. The agent does not read it from this repo.

Building from source is in that same install page.

## MCP

`setup/mcp.json` is a template. The path in it is a placeholder, not a file on any one computer. Copy the `pdf-ai-tools` entry into the agent and set `command` to the executable on your machine. The install page lists where that config file goes for each agent.

Paths are the client's files. An absolute path or `~/...` is that file. A relative path uses the client working directory. Built-in palette and template names load from the install, not from that directory.

Built-in palette and template names are the JSON file stem (`ocean_blue`, `invoice`), not the display title inside the file. A value that ends in `.json`, or any path with a slash, loads that file.

`pdf_render_template` takes `variables_json` as a JSON object string. `pdf_create_document` returns `doc_id`. Every later call on that document needs it. `pdf_save_document` writes the file and closes the session.

The built-in templates are `invoice`, `contract` and `report`. When none of them fits, pass the template object inline with `template_json` and the server writes the PDF in one call, with no template file on disk. The template schema is in the `pdf_render_template` tool description.

Text uses the built-in Latin fonts by default. For any other script, `pdf_list_fonts(for_text="...")` finds the fonts installed on the machine that can draw it and `pdf_use_font` applies one. Characters the current font cannot draw fall back to another installed font automatically.

Tool list and result shapes: `setup/pdf-ai-tools/SKILL.md` and `setup/pdf-ai-tools/reference.md`. Tool results are TOON text, not JSON.

Example:

```text
pdf_create_document(output_path="/tmp/note.pdf")
pdf_apply_palette(doc_id, "corporate_slate")
pdf_add_heading(doc_id, "Note", level=1)
pdf_add_paragraph(doc_id, "Body text.")
pdf_save_document(doc_id)
```

## CLI

The same executable is the CLI. No arguments in a terminal prints help. An agent that launches it with a pipe starts the MCP server.

```bash
./pdf-ai-tools-linux-x86_64/pdf-ai-tools-linux-x86_64 list-palettes
./pdf-ai-tools-linux-x86_64/pdf-ai-tools-linux-x86_64 list-templates
./pdf-ai-tools-linux-x86_64/pdf-ai-tools-linux-x86_64 --help
```

Use the folder name for your OS. Mac and Windows names are in the install page.

Document construction stays on the MCP tools. The CLI lists palettes and templates.

## Tools

| Category | Tools |
| --- | --- |
| Session | `pdf_create_document`, `pdf_set_metadata`, `pdf_save_document`, `pdf_get_document_state`, `pdf_list_documents` |
| Palettes | `pdf_list_palettes`, `pdf_apply_palette`, `pdf_export_palette`, `pdf_create_palette_from_colors` |
| Fonts | `pdf_list_fonts`, `pdf_use_font` |
| Templates | `pdf_list_templates`, `pdf_render_template`, `pdf_save_template`, `pdf_inspect_template` |
| Page chrome | `pdf_configure_header`, `pdf_configure_footer`, `pdf_enable_page_numbers`, `pdf_set_watermark` |
| Structure | `pdf_add_table_of_contents`, `pdf_add_anchor` |
| Content | `pdf_add_heading`, `pdf_add_paragraph`, `pdf_add_bullet_list`, `pdf_add_numbered_list`, `pdf_add_spacer`, `pdf_add_horizontal_line`, `pdf_add_page_break` |
| Media | `pdf_insert_image`, `pdf_add_qr_code` |
| Layout | `pdf_add_table`, `pdf_add_colored_box`, `pdf_add_cover_page`, `pdf_add_section_divider`, `pdf_add_key_metrics`, `pdf_add_two_column`, `pdf_add_code_block`, `pdf_add_banner`, `pdf_add_signature_placeholder` |
| Read | `pdf_read_file_info`, `pdf_read_file_text`, `pdf_read_file_page_sizes` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT (c) [Keiner Alvarado](https://github.com/keiner5212)
