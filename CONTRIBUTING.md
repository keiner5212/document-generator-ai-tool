# Contributing to pdf-ai-tools

Thank you for your interest. All contributions go through pull requests and are reviewed by the maintainer.

## Author

This project is maintained solely by **Keiner Alvarado**. All commits, releases, and authorship records must attribute **Keiner Alvarado** as the original author.

---

## Getting started

```bash
git clone https://github.com/keiner5212/document-generator-ai-tool.git
cd document-generator-ai-tool
uv sync
```

## Development workflow

1. Fork the repository.
2. Create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature
   ```
3. Make focused, minimal changes.
4. Verify all checks pass:
   ```bash
   uv run ruff check src/
   uv run ruff format --check src/
   uv run python -m pytest
   ```
5. Open a pull request against `main`.

## Code standards

- **Correctness first** - no silent failures, no swallowed exceptions. Tool functions return `_err` instead of raising into the agent.
- **Minimal diffs** - change only what the issue requires.
- **No decorative edits** - no style-only refactors unless the PR is explicitly about style.
- **Python >= 3.13** - use modern type syntax (`X | Y`, `list[str]`, etc.).
- **TOON result contract** - every MCP tool returns TOON text, not JSON. `ok` is true or false. Errors stay in that text.

## Adding a palette

Add a JSON file under `src/pdf_ai_tools/palettes/`. The file stem is the name agents pass to `pdf_apply_palette`.

```json
{
  "name": "My Palette",
  "description": "One-line description",
  "colors": {
    "primary": "#112233",
    "secondary": "#334455",
    "accent": "#667788",
    "muted": "#99aabb",
    "border": "#ccddee",
    "background": "#f7fafc"
  },
  "fonts": { "body": "Helvetica", "heading": "Helvetica-Bold" },
  "sizes": { "body": 11, "h1": 22, "h2": 16, "h3": 13, "caption": 9 },
  "document": { "page_size": "A4", "margins_cm": [2.5, 2.5, 2.5, 2.5], "page_numbers": true, "watermark": null }
}
```

Allowed PDF fonts: `Helvetica`, `Helvetica-Bold`, `Helvetica-Oblique`, `Times-Roman`, `Times-Bold`, `Times-Italic`, `Courier`, `Courier-Bold`.

## Adding a template

Add a JSON file under `src/pdf_ai_tools/templates/`. Required keys: `name`, `description`, `variables`, `document`, `header`, `footer`, `blocks`. The file stem is the name passed to `pdf_render_template`. Placeholder syntax: `{{variable_name}}`.

## Adding a tool

1. Add the function to `src/pdf_ai_tools/tools.py`. The docstring is the MCP description.
2. Register it in `src/pdf_ai_tools/mcp_server.py` with `mcp.tool()(tools.your_function)`.
3. Update `setup/pdf-ai-tools/SKILL.md` and `setup/pdf-ai-tools/reference.md`.

## Commit messages

Use conventional commits:

```
feat: add pdf_add_callout border width
fix: keep invoice template total on one line
docs: update SKILL.md cover-page order
chore: bump reportlab
```

## Reporting bugs

Open an issue using the **Bug report** template. Include:

- Command or tool call (sanitize any sensitive paths)
- Full `stderr` output
- Python version (`python --version`)
- `uv` version (`uv --version`)

## Requesting features

Open an issue using the **Feature request** template. Describe the use case clearly, not only the proposed API.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE) and that copyright remains with **Keiner Alvarado**.
