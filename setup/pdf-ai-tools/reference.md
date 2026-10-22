# PDF AI Tools Reference

Every tool returns TOON text, not JSON. Do not `json.loads` the result.

```text
ok: true
doc_id: abc
```

`ok: false` means the call failed. Read `error`. Content tools change the open session only. `pdf_save_document` is the call that writes the PDF. It creates missing parent directories.

## Session

`pdf_create_document` returns `doc_id`. Pass that id to every later call on the same document. `pdf_save_document` writes the file and closes the session. Do not call content tools after save.

`pdf_render_template` creates, fills, saves, and closes in one call. It returns `saved_to`. It does not return a live `doc_id`.

`pdf_list_documents` lists sessions that are still open.

## Names and paths

Built-in palette names and template names are the JSON file stem: `ocean_blue`, `corporate_slate`, `invoice`, `contract`, `report`. The `name` field inside the file is a display title. Do not pass that title to `pdf_apply_palette` or `pdf_render_template`. The built-in JSON files load from the directory where the program is installed.

A value that ends in `.json`, or any value that contains `/` or `\`, is a file path. Anything else is a built-in stem.

An absolute path writes or reads that file. `~/...` is the home directory. A relative path, including a bare filename, is relative to the client working directory. The server does not change directory.

`pdf_render_template` argument `variables_json` is a JSON object string, not separate arguments:

```text
{"company_name": "Acme", "client_name": "Jane Doe"}
```

Output paths are normal filesystem paths. The tools do not invent a workspace directory. `pdf_save_document` creates missing parent directories.

## Tool list

| Tool | Role |
| --- | --- |
| `pdf_create_document` | Start a session. Returns `doc_id`. |
| `pdf_set_metadata` | Title, author, subject, keywords. |
| `pdf_save_document` | Write the PDF and close the session. |
| `pdf_get_document_state` | Inspect the open session without saving. |
| `pdf_list_documents` | List open sessions. |
| `pdf_list_palettes` | Built-in palettes. Optional `extra_dir`. |
| `pdf_apply_palette` | Apply a stem or a JSON path. |
| `pdf_export_palette` | Write the current theme to JSON. |
| `pdf_create_palette_from_colors` | Write a new palette JSON. |
| `pdf_list_templates` | Built-in templates. Optional `extra_dir`. |
| `pdf_render_template` | Fill `{{variable}}` placeholders and save. |
| `pdf_save_template` | Save the open layout as template JSON. |
| `pdf_inspect_template` | Show variables and blocks. No PDF is written. |
| `pdf_configure_header` | Left, center, right. Optional line under the header. |
| `pdf_configure_footer` | Left, center, right. |
| `pdf_enable_page_numbers` | Page numbers at the bottom. |
| `pdf_set_watermark` | Diagonal text on every page. |
| `pdf_add_heading` | Level 1, 2, or 3. Plain text. |
| `pdf_add_paragraph` | Body text. `<b>` and `<i>` are allowed. |
| `pdf_add_bullet_list` | List of strings. |
| `pdf_add_numbered_list` | List of strings. |
| `pdf_add_spacer` | Vertical gap in centimeters. |
| `pdf_add_horizontal_line` | Rule across the content width. |
| `pdf_add_page_break` | Next content starts on a new page. |
| `pdf_insert_image` | PNG, JPEG, GIF, or BMP. Optional caption. |
| `pdf_add_qr_code` | QR from a string. Optional caption. |
| `pdf_add_table` | Rows of cell strings. First row is the header when `header_row` is true. |
| `pdf_add_colored_box` | Callout. Optional title. |
| `pdf_add_signature_placeholder` | 1 to 4 dashed boxes, `row` or `column`. |
| `pdf_add_cover_page` | First content call. Styles: `stripe`, `split`, `minimal`. |
| `pdf_add_section_divider` | Styles: `line`, `bar`, `underline`, `diamond`. |
| `pdf_add_key_metrics` | List of `{value, label}` objects. |
| `pdf_add_two_column` | Two text blocks side by side. |
| `pdf_add_code_block` | Monospace block. Optional language caption. |
| `pdf_add_banner` | Full-width colored strip. |
| `pdf_read_file_info` | Metadata of an existing PDF. |
| `pdf_read_file_text` | Extracted text. `pages` is like `1,3,5`. Empty means all pages. |
| `pdf_read_file_page_sizes` | Page size of each page. |

Cover page, when used, is the first content call. Header and footer may be set before it. Set `show_on_first_page` to false on the header and footer when the first page is a cover.
