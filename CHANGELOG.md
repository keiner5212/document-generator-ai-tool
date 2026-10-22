# Changelog

**Author / maintainer:** Keiner Alvarado  
All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [0.4.1] - 2026-10-23

### Fixed
- The font tests skip with a reason when the machine has no font for the script, so a
  machine without the Noto and CJK fonts no longer fails the run.

## [0.4.0] - 2026-10-22

### Added
- **Template catalog in the MCP instructions**: the server now describes the built-in
  templates (id, purpose, variables, palette) at startup, so the agent knows they exist
  without calling a tool.
- **Inline templates**: `pdf_render_template` and `pdf_inspect_template` accept
  `template_json`, a complete template object passed inline. A layout that no built-in
  template covers no longer needs a template file on disk.
- **Template schema in the tool description**: `pdf_render_template` documents the
  template JSON and every block kind with its arguments, generated from the tool
  signatures so it cannot drift.
- **Table of contents and PDF bookmarks**: `pdf_add_table_of_contents` builds a TOC from
  the document headings and creates the outline entries.
- **Cover page is always first**: `pdf_add_cover_page` places the cover at the start of
  the document even when it is called after other content, so a late call no longer
  leaves the document in a state it cannot recover from.
- **Host fonts**: `pdf_list_fonts` lists the fonts installed on the machine, filtered by
  name or by the text they can draw. `pdf_use_font` applies a family name or a font file
  to the body text, the headings and the code blocks, and picks up the bold, italic and
  bold-italic members of the family.
- **Automatic font fallback**: characters the current font cannot draw are drawn with an
  installed font that has them, so a document that mixes scripts keeps working. When no
  installed font covers a character, the tool fails and names it.
- **Language support**: `pdf_set_metadata(language=...)` writes the document language as a
  BCP 47 tag, which screen readers use. Chinese, Japanese and Korean text wraps per
  character. Complex scripts are shaped with HarfBuzz, and right to left text is put in
  the right order by the bidirectional algorithm.
- **Template fonts**: a template can carry `document.fonts`, so a saved layout keeps the
  fonts it was built with.
- `pdf_create_document` rejects an unknown `page_size` instead of silently using A4.
- **Link targets are checked**: a link to an anchor that does not exist is reported with the
  name of the missing target instead of failing the whole save with a ReportLab error.
  The session stays open, so the anchor can still be added.
- **Bullet lists show a bullet**: the marker was a character that the built-in fonts do
  not have, so it printed as a blank box. The section divider diamond is now drawn as a
  shape for the same reason.
- Documents with a cover page, a table of contents and `page_of_total` page numbers
  build correctly. The two pass build no longer trips over layout state left by the
  first pass.
- Saving a document with no content fails instead of writing an empty PDF.
- **Internal links**: `pdf_add_anchor` creates a named target for `<a href="#name">`.
- **Page count in the footer**: `pdf_enable_page_numbers(format="page_of_total")` writes
  "Page 2 of 8".
- **Table controls**: `pdf_add_table` takes `column_alignments` and `repeat_header`.
- **Image fitting**: `pdf_insert_image` keeps the aspect ratio when both width and height
  are given, and checks that the file really is a PNG, JPEG, GIF or BMP.
- `pdf_read_file_info` reports the PDF keywords.

### Changed
- Source layout is now `src/pdf_ai_tools`. Palettes and templates ship inside the package.
- MCP entry point is `pdf-ai-tools-mcp`. The skill and install notes live in `setup/`.
- Package version is 0.4.0. Tool results are TOON text. The MCP server uses `mcp.server.mcpserver.MCPServer` with `structured_output` off.
- `uharfbuzz` and `python-bidi` are dependencies, so complex scripts are shaped with
  HarfBuzz and right to left text is reordered. ReportLab looks for an optional `rlbidi`
  package that is not on PyPI, so the package provides the small part of that interface
  ReportLab needs, on top of `python-bidi`.
- `pdf_save_document` takes `pages` to keep only some pages, e.g. `1-3,5`.
- **Breaking**: `pdf_create_document` lost the `theme` argument. Palettes are the styling
  mechanism; the four legacy themes and the unused `quote` style are gone.
- **Breaking**: `pdf_inspect_template` takes `template_name_or_path` and `template_json`
  instead of `path`.
- Templates are validated before they render: unknown keys, unknown block kinds, unknown
  arguments and wrong argument types are reported instead of failing halfway. An unfilled
  `{{placeholder}}` is an error, not literal text in the PDF.
- `pdf_save_template` keeps the palette of the document it was saved from.
- Removed the `src/pdf_ai_tools/templates/my_*.json` ignore rule. Agent-made templates
  belong in the project, not in the MCP install folder.
