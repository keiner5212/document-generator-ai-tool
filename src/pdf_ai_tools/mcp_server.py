"""MCP server for pdf-ai-tools.

Run via:
    uv run pdf-ai-tools-mcp

Or from any MCP client (config can live anywhere; --project does not chdir):
    {
      "command": "uv",
      "args": ["run", "--project", "/path/to/repo", "pdf-ai-tools-mcp"]
    }
"""

from __future__ import annotations

from functools import wraps
from importlib.metadata import PackageNotFoundError, version

from mcp.server.mcpserver import MCPServer

from pdf_ai_tools import tools
from pdf_ai_tools.render import render


def package_version() -> str:
    try:
        return version("pdf-ai-tools")
    except PackageNotFoundError:
        return "0.1.0"


mcp = MCPServer(
    "pdf-ai-tools",
    version=package_version(),
    instructions=(
        "Create, decorate, and read PDF documents. "
        "Do not write Python or import reportlab. Use these tools. "
        "Order: pdf_create_document, then pdf_apply_palette, pdf_set_metadata, "
        "header and footer, content tools, then pdf_save_document. "
        "Keep doc_id from pdf_create_document. "
        "Built-in palette and template names are the JSON file stem "
        "(ocean_blue, invoice), not the display name inside the file. "
        "A path ending in .json, or any path with a slash, loads that file. "
        "pdf_render_template variables_json is a JSON object string. "
        "Every tool result is TOON text, not JSON. "
        "pdf_save_document closes the session."
    ),
)

_register_tool = mcp.tool


def _tool(*args, **kwargs):
    kwargs["structured_output"] = False

    def decorator(fn):
        @wraps(fn)
        def wrapped(*fn_args, **fn_kwargs):
            return render(fn(*fn_args, **fn_kwargs))

        return _register_tool(*args, **kwargs)(wrapped)

    return decorator


mcp.tool = _tool

# --- Lifecycle ---
mcp.tool()(tools.pdf_create_document)
mcp.tool()(tools.pdf_set_metadata)
mcp.tool()(tools.pdf_save_document)
mcp.tool()(tools.pdf_get_document_state)
mcp.tool()(tools.pdf_list_documents)

# --- Palettes ---
mcp.tool()(tools.pdf_list_palettes)
mcp.tool()(tools.pdf_apply_palette)
mcp.tool()(tools.pdf_export_palette)
mcp.tool()(tools.pdf_create_palette_from_colors)

# --- Templates ---
mcp.tool()(tools.pdf_list_templates)
mcp.tool()(tools.pdf_render_template)
mcp.tool()(tools.pdf_save_template)
mcp.tool()(tools.pdf_inspect_template)

# --- Layout ---
mcp.tool()(tools.pdf_configure_header)
mcp.tool()(tools.pdf_configure_footer)
mcp.tool()(tools.pdf_enable_page_numbers)
mcp.tool()(tools.pdf_set_watermark)

# --- Content ---
mcp.tool()(tools.pdf_add_heading)
mcp.tool()(tools.pdf_add_paragraph)
mcp.tool()(tools.pdf_add_bullet_list)
mcp.tool()(tools.pdf_add_numbered_list)
mcp.tool()(tools.pdf_add_spacer)
mcp.tool()(tools.pdf_add_horizontal_line)
mcp.tool()(tools.pdf_add_page_break)

# --- Media ---
mcp.tool()(tools.pdf_insert_image)
mcp.tool()(tools.pdf_add_qr_code)

# --- Tables & boxes ---
mcp.tool()(tools.pdf_add_table)
mcp.tool()(tools.pdf_add_colored_box)

# --- Advanced decoration ---
mcp.tool()(tools.pdf_add_cover_page)
mcp.tool()(tools.pdf_add_section_divider)
mcp.tool()(tools.pdf_add_key_metrics)
mcp.tool()(tools.pdf_add_two_column)
mcp.tool()(tools.pdf_add_code_block)
mcp.tool()(tools.pdf_add_banner)

# --- Signatures ---
mcp.tool()(tools.pdf_add_signature_placeholder)

# --- Read existing PDFs ---
mcp.tool()(tools.pdf_read_file_info)
mcp.tool()(tools.pdf_read_file_text)
mcp.tool()(tools.pdf_read_file_page_sizes)


# ---------------------------------------------------------------------------
# Prompt templates (guide the AI on how to use tools together)
# ---------------------------------------------------------------------------


@mcp.prompt()
def create_invoice(company: str = "Acme Corp", client: str = "Client Name") -> str:
    """Quick-start: generate a professional invoice PDF."""
    return (
        f"Create an invoice PDF for {company} billing {client}.\n\n"
        "Use pdf_render_template with template='invoice' and output_path='output/invoice.pdf'.\n"
        "Fill variables: company_name, client_name, invoice_number, date, due_date, total.\n"
        "Or build manually: pdf_create_document -> pdf_apply_palette('corporate_slate') -> "
        "pdf_configure_header -> pdf_add_table -> pdf_add_signature_placeholder -> pdf_save_document."
    )


@mcp.prompt()
def create_contract(party_a: str = "Company A", party_b: str = "Company B") -> str:
    """Quick-start: generate a service contract with two party signatures."""
    return (
        f"Create a service contract between {party_a} and {party_b}.\n\n"
        "Use pdf_render_template with template='contract' and output_path='output/contract.pdf'.\n"
        "Fill variables: party_a, party_b, address_a, address_b, service, value, start_date, end_date, governing_law.\n"
        "Palette applied automatically: legal_classic."
    )


@mcp.prompt()
def palette_guide() -> str:
    """Show how to use and combine palettes."""
    return (
        "To use a color palette:\n"
        "1. pdf_list_palettes - see the built-in palettes with descriptions\n"
        "2. pdf_create_document -> doc_id\n"
        "3. pdf_apply_palette(doc_id, 'ocean_blue') - or any palette name\n\n"
        "To create a custom palette:\n"
        "  pdf_create_palette_from_colors(output_path='palettes/my_brand.json', name='My Brand', "
        "primary='#003366', secondary='#0055a4', accent='#ff6600', ...)\n\n"
        "To save the current doc's palette for reuse:\n"
        "  pdf_export_palette(doc_id, 'palettes/my_export.json')"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
