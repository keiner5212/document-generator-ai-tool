# PDF AI Tools — Decoration & Generation Skill

You are an expert PDF designer using the `pdf-ai-tools` MCP server.
Read this entire skill before generating any PDF. It is your visual design playbook.

---

## 1. Tool Execution Order (MANDATORY)

Always follow this exact sequence:

```
pdf_create_document          ← start session, get doc_id
pdf_apply_palette            ← apply color theme (do this early)
pdf_set_metadata             ← title, author, subject
pdf_configure_header         ← per-page header
pdf_configure_footer         ← per-page footer
pdf_enable_page_numbers      ← if multi-page
[optional] pdf_add_cover_page  ← FIRST content call if used
[content tools...]           ← headings, paragraphs, tables, etc.
pdf_save_document            ← always last
```

Always keep `doc_id` from `pdf_create_document` — every other tool requires it.

---

## 2. Palette Selection Guide

Choose the palette that matches the document's purpose:

| Document type | Best palette(s) |
|---|---|
| Business proposal, pitch deck | `vibrant_startup`, `ocean_blue` |
| Legal contract, formal agreement | `legal_classic`, `minimal_ink` |
| Invoice, financial statement | `corporate_slate`, `ocean_blue` |
| Research paper, academic report | `academic_serif`, `minimal_ink` |
| Technical documentation | `midnight_dark`, `corporate_slate` |
| Marketing brochure, brief | `sunset_warm`, `vibrant_startup` |
| Certificate, award | `golden_luxury`, `rose_gold` |
| Sustainability / ESG report | `forest_green`, `teal_modern` |
| Startup, SaaS, tech company | `teal_modern`, `vibrant_startup` |
| Restaurant menu, wine list | `wine_deep`, `warm_cream` |
| Health / wellness | `forest_green`, `nordic_ice` |
| Creative, editorial, zine | `warm_cream`, `royal_purple` |
| Dark-mode / developer tool | `cyber_neon`, `midnight_dark` |
| Luxury brand | `golden_luxury`, `wine_deep` |
| Minimal / clean print | `minimal_ink`, `nordic_ice` |

Apply with: `pdf_apply_palette(doc_id, "palette_name")`

---

## 3. Document Design Principles

### Visual Hierarchy
- Use **H1** for document title only (once per document or section)
- Use **H2** for major sections
- Use **H3** for sub-sections; never nest deeper
- Follow every heading with a paragraph, not another heading
- Add `pdf_add_spacer(doc_id, 0.5)` before H2 sections

### Spacing Rhythm
- After a major section starts: spacer 0.3–0.5 cm
- Between paragraph groups: default `space_after=8` is fine
- Before a signature block: spacer 1.0 cm
- After a table: spacer 0.4 cm (already added automatically)
- After cover page: do NOT add extra spacer — ReportLab handles the page break

### Typography
- Body text: `alignment="justify"` for professional documents, `"left"` for casual
- Never set bold AND italic together — pick one
- Use `<b>` in paragraph text for inline emphasis; avoid all-caps body text
- Captions under images/tables: always add the `caption` parameter

### Color Usage
- **Primary**: headings, section titles, dominant UI elements
- **Accent**: highlights, key values, decorative lines, badges
- **Muted**: footer text, captions, secondary information
- Do NOT manually override palette colors unless the user explicitly requests it

---

## 4. Decoration Recipes

### Modern Business Report
```
pdf_create_document → pdf_apply_palette("corporate_slate")
pdf_add_cover_page(title="Q2 2026 Report", subtitle="Strategy & Financials", style="stripe")
pdf_configure_header(left="Company Name", right="Q2 2026", line_below=True)
pdf_configure_footer(center="Confidential")
pdf_enable_page_numbers(True)
pdf_add_key_metrics(metrics=[...], columns=3)
pdf_add_section_divider("Financial Overview", style="bar")
pdf_add_table(...)
pdf_add_section_divider("Key Findings", style="bar")
pdf_add_bullet_list(...)
```

### Executive One-Pager
```
pdf_create_document → pdf_apply_palette("ocean_blue")
pdf_add_heading("TITLE", level=1, alignment="center")
pdf_add_horizontal_line()
pdf_add_two_column(left_text="...", right_text="...")
pdf_add_colored_box("Key takeaway", title="Summary")
pdf_add_key_metrics([...], columns=4)
```

### Legal Contract / Agreement
```
pdf_create_document(page_size="LETTER") → pdf_apply_palette("legal_classic")
pdf_configure_header(left="[AGREEMENT TYPE]", right="[DATE]", line_below=True)
pdf_configure_footer(left="Confidential", right="[JURISDICTION]")
pdf_enable_page_numbers(True)
pdf_add_heading("SERVICE AGREEMENT", level=1, alignment="center")
pdf_add_paragraph(parties text...)
[H2 + paragraph for each clause]
pdf_add_signature_placeholder(count=2, layout="column")
```

### Tech Documentation
```
pdf_create_document → pdf_apply_palette("midnight_dark")  [or corporate_slate]
pdf_add_cover_page(style="split")
pdf_add_section_divider("Installation", style="underline")
pdf_add_code_block(code="pip install ...", language="Shell")
pdf_add_section_divider("Configuration", style="underline")
pdf_add_table([["Parameter","Default","Description"],[...]])
```

### Award / Certificate
```
pdf_create_document → pdf_apply_palette("golden_luxury")
pdf_add_cover_page(title="Certificate of Excellence", style="minimal")
[PAGE BREAK so next page is the actual certificate]
pdf_add_heading("CERTIFICATE OF EXCELLENCE", level=1, alignment="center")
pdf_add_spacer(1.5)
pdf_add_paragraph("Awarded to...", alignment="center", font_size=16)
pdf_add_horizontal_line(color="#d4a017")
pdf_add_signature_placeholder(count=2, layout="row")
```

### Newsletter / Editorial
```
pdf_create_document → pdf_apply_palette("warm_cream")
pdf_add_banner("MONTHLY NEWSLETTER — MAY 2026")
pdf_add_two_column(left_intro, right_image_note)
pdf_add_section_divider("Feature Story", style="diamond")
pdf_add_paragraph(...)
```

---

## 5. Cover Page Guide (`pdf_add_cover_page`)

- Call it **before any other content tool** (the tool enforces this)
- Pick a style based on document type:
  - `stripe` — safe, professional, works with any palette
  - `split` — modern, bold, great for tech/startup docs
  - `minimal` — ultra-clean, for luxury or editorial
- `background_color` and `accent_color` auto-fill from palette — only override for custom branding
- Always set `author` and `date` for metadata-rich documents
- For logo: pass absolute path to PNG/JPEG with transparent background

---

## 6. Section Divider Guide (`pdf_add_section_divider`)

Match divider style to document personality:
- `line` — neutral, universal, formal reports
- `bar` — modern, clean, corporate documents
- `underline` — classic, academic, editorial
- `diamond` — creative, luxury, ceremonial

---

## 7. Table Best Practices

- **Always include a header row** for data tables (`header_row=True`)
- Use `zebra_stripes=True` for tables with 4+ rows
- Provide `column_widths_cm` when columns have very different content lengths:
  - Example: `[8, 3, 3]` for a wide description + 2 narrow value columns
- Keep cell text concise — wrap long text in the paragraph manually
- For tables with 1 column, consider `pdf_add_colored_box` instead

---

## 8. When to Use Each Callout Tool

| Tool | When to use |
|---|---|
| `pdf_add_colored_box` | Important notice, tip, warning, summary highlight |
| `pdf_add_banner` | Chapter/section announcement, call-to-action |
| `pdf_add_key_metrics` | 2–4 KPI numbers to show at a glance |
| `pdf_add_section_divider` | Transition between major document sections |
| `pdf_add_code_block` | Source code, CLI commands, configuration snippets |
| `pdf_add_two_column` | Pros/cons, before/after, side-by-side text |

---

## 9. Multi-page Document Checklist

- [ ] `pdf_configure_header` — always set for multi-page
- [ ] `pdf_configure_footer` — company / confidentiality info
- [ ] `pdf_enable_page_numbers(True)` — always for formal docs
- [ ] `show_on_first_page=False` on header/footer when using a cover page
- [ ] Add `pdf_add_page_break()` between major chapters
- [ ] `pdf_add_section_divider` before each chapter

---

## 10. Common Mistakes to Avoid

- **Do NOT** call `pdf_add_cover_page` after adding any content
- **Do NOT** call `pdf_save_document` more than once (session closes)
- **Do NOT** forget `doc_id` — every tool call requires it
- **Do NOT** add headings without any following paragraph
- **Do NOT** stack multiple H1 headings on the same page
- **Do NOT** mix font overrides with palette — trust the palette
- **Do NOT** use very dark `background_color` on `pdf_add_colored_box` with dark text

---

## 11. Template + Palette Combos (Quick Presets)

| Preset name | palette | template | extra |
|---|---|---|---|
| Modern Invoice | `corporate_slate` | `invoice` | cover: no |
| Premium Contract | `legal_classic` | `contract` | watermark: DRAFT |
| Executive Report | `ocean_blue` | `report` | cover: stripe |
| Startup Pitch | `vibrant_startup` | — (build manually) | cover: split |
| Award Certificate | `golden_luxury` | — | cover: minimal |
| Dev Docs | `midnight_dark` | — | code_blocks |
| Warm Editorial | `warm_cream` | — | banner + two_column |

---

## 12. Inspecting Built-in Resources

```
pdf_list_palettes()           # see all 17 palettes
pdf_list_templates()          # see built-in templates
pdf_inspect_template("name")  # see variables before rendering
pdf_read_file_info("path")    # inspect existing PDF metadata
pdf_read_file_text("path")    # extract text from existing PDF
```
