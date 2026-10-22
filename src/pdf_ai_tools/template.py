"""
Template system for PDF AI Tools.

A template is a JSON object that fully describes a document. It is rendered
in one call: the server creates the document, applies the palette, fills the
{{variable}} placeholders, replays the blocks and writes the PDF.

Top level keys
--------------
name, description, version   identity strings
variables                    {placeholder: "what the value is"}; every
                             {{placeholder}} used must be declared here
document                     page size, margins, palette
metadata                     title, author, subject, keywords
header, footer               left/center/right text, font size, color, rules
page_numbers                 bool
watermark                    diagonal text or null
blocks                       ordered list of content blocks

Block
-----
{"kind": "<block kind>", "kwargs": {...}}

`describe_template_schema()` returns the block kinds with their accepted
arguments. It is generated from the tool signatures, so it never drifts.
"""

from __future__ import annotations

import inspect
import json
import re
import types
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin

from pdf_ai_tools.paths import resolve_installed_or_user, resolve_user_path

_BUILTIN_DIR = Path(__file__).resolve().parent / "templates"

MAX_TEMPLATE_BYTES = 256 * 1024
MAX_VARIABLES_BYTES = 64 * 1024
MAX_BLOCKS = 2000
MAX_TEXT_LENGTH = 100_000
MAX_ITEMS = 5000

TOP_LEVEL_KEYS = {
    "name",
    "description",
    "version",
    "variables",
    "document",
    "metadata",
    "header",
    "footer",
    "page_numbers",
    "watermark",
    "blocks",
}

# ---------------------------------------------------------------------------
# Block kinds
# ---------------------------------------------------------------------------


def _block_dispatch() -> dict[str, Any]:
    """Map every template block kind to the tool that renders it."""
    from pdf_ai_tools import tools

    return {
        "heading": tools.pdf_add_heading,
        "paragraph": tools.pdf_add_paragraph,
        "bullet_list": tools.pdf_add_bullet_list,
        "numbered_list": tools.pdf_add_numbered_list,
        "table": tools.pdf_add_table,
        "colored_box": tools.pdf_add_colored_box,
        "horizontal_line": tools.pdf_add_horizontal_line,
        "spacer": tools.pdf_add_spacer,
        "page_break": tools.pdf_add_page_break,
        "insert_image": tools.pdf_insert_image,
        "qr_code": tools.pdf_add_qr_code,
        "signature_placeholder": tools.pdf_add_signature_placeholder,
        "cover_page": tools.pdf_add_cover_page,
        "section_divider": tools.pdf_add_section_divider,
        "key_metrics": tools.pdf_add_key_metrics,
        "two_column": tools.pdf_add_two_column,
        "code_block": tools.pdf_add_code_block,
        "banner": tools.pdf_add_banner,
        "table_of_contents": tools.pdf_add_table_of_contents,
        "anchor": tools.pdf_add_anchor,
    }


def _signature_of(fn: Any) -> inspect.Signature:
    """Signature of a tool function with its annotations resolved."""
    try:
        return inspect.signature(fn, eval_str=True)
    except (NameError, TypeError):
        return inspect.signature(fn)


# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _substitute(value: Any, variables: dict[str, str], missing: set[str]) -> Any:
    """Recursively replace {{var}} in strings, dicts, and lists."""
    if isinstance(value, str):

        def _replace(m: re.Match) -> str:
            name = m.group(1)
            if name in variables:
                return variables[name]
            missing.add(name)
            return m.group(0)

        return _VAR_RE.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _substitute(v, variables, missing) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(item, variables, missing) for item in value]
    return value


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _type_name(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "any"
    if isinstance(annotation, type):
        return annotation.__name__
    origin = get_origin(annotation)
    if origin is Literal:
        return "one of " + ", ".join(repr(a) for a in get_args(annotation))
    if origin in (Union, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        return " or ".join(_type_name(a) for a in args) or "any"
    if origin is list:
        args = get_args(annotation)
        return f"list of {_type_name(args[0])}" if args else "list"
    return str(annotation)


def _value_matches(annotation: Any, value: Any) -> bool:
    """True when a JSON value fits the annotated parameter type."""
    if annotation is inspect.Parameter.empty:
        return True
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        if value is None and type(None) in get_args(annotation):
            return True
        return any(
            _value_matches(arg, value)
            for arg in get_args(annotation)
            if arg is not type(None)
        )
    if origin is Literal:
        return value in get_args(annotation)
    if origin is list:
        if not isinstance(value, list):
            return False
        args = get_args(annotation)
        if not args:
            return True
        return all(_value_matches(args[0], item) for item in value)
    if annotation is bool:
        return isinstance(value, bool)
    if annotation is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if annotation is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if annotation is str:
        return isinstance(value, str)
    if isinstance(annotation, type):
        return isinstance(value, annotation)
    return True


def _validate_template(tpl: Any) -> dict:
    """Check a template object against the schema. Raises ValueError."""
    if not isinstance(tpl, dict):
        raise TypeError("Template must be a JSON object")

    unknown = set(tpl) - TOP_LEVEL_KEYS
    if unknown:
        raise ValueError(
            f"Unknown template keys: {sorted(unknown)}. "
            f"Allowed keys: {sorted(TOP_LEVEL_KEYS)}"
        )

    if "blocks" not in tpl:
        raise ValueError("Template missing 'blocks' key")
    blocks = tpl["blocks"]
    if not isinstance(blocks, list):
        raise TypeError("Template 'blocks' must be a list")
    if len(blocks) > MAX_BLOCKS:
        raise ValueError(
            f"Template has {len(blocks)} blocks, the limit is {MAX_BLOCKS}"
        )

    variables = tpl.get("variables", {})
    if not isinstance(variables, dict):
        raise TypeError("Template 'variables' must be an object")
    for name, hint in variables.items():
        if not isinstance(name, str) or not isinstance(hint, str):
            raise TypeError("Template 'variables' must map names to strings")

    dispatch = _block_dispatch()
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise TypeError(f"Block {index} must be an object")
        kind = block.get("kind")
        if kind not in dispatch:
            raise ValueError(
                f"Block {index}: unknown kind {kind!r}. "
                f"Available kinds: {sorted(dispatch)}"
            )
        kwargs = block.get("kwargs", {})
        if not isinstance(kwargs, dict):
            raise TypeError(f"Block {index} ({kind}): 'kwargs' must be an object")
        params = _signature_of(dispatch[kind]).parameters
        accepted = {name for name in params if name != "doc_id"}
        for key, value in kwargs.items():
            if key not in accepted:
                raise ValueError(
                    f"Block {index} ({kind}): unknown argument {key!r}. "
                    f"Accepted arguments: {sorted(accepted)}"
                )
            annotation = params[key].annotation
            if not _value_matches(annotation, value):
                raise ValueError(
                    f"Block {index} ({kind}): {key!r} must be "
                    f"{_type_name(annotation)}, got {type(value).__name__}"
                )
            if isinstance(value, str) and len(value) > MAX_TEXT_LENGTH:
                raise ValueError(
                    f"Block {index} ({kind}): {key!r} is longer than "
                    f"{MAX_TEXT_LENGTH} characters"
                )
            if isinstance(value, list) and len(value) > MAX_ITEMS:
                raise ValueError(
                    f"Block {index} ({kind}): {key!r} has more than {MAX_ITEMS} items"
                )
    return tpl


# ---------------------------------------------------------------------------
# Template file I/O
# ---------------------------------------------------------------------------


def load_template(path: str) -> dict:
    """Load a template JSON from path (checks built-in dir if relative)."""
    p = resolve_installed_or_user(path, _BUILTIN_DIR)
    if not p.is_file():
        raise FileNotFoundError(f"Template not found: {path}")
    if p.stat().st_size > MAX_TEMPLATE_BYTES:
        raise ValueError(
            f"Template file is larger than {MAX_TEMPLATE_BYTES} bytes: {path}"
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return _validate_template(data)


def load_builtin_template(name: str) -> dict:
    """Load a built-in template by name (without .json)."""
    p = _BUILTIN_DIR / f"{name}.json"
    if not p.exists():
        available = [f.stem for f in sorted(_BUILTIN_DIR.glob("*.json"))]
        raise FileNotFoundError(
            f"Built-in template '{name}' not found. Available: {available}"
        )
    return load_template(str(p))


def load_inline_template(raw: str) -> dict:
    """Parse and validate a template object supplied inline as a JSON string."""
    if len(raw) > MAX_TEMPLATE_BYTES:
        raise ValueError(
            f"template_json is {len(raw)} bytes, the limit is {MAX_TEMPLATE_BYTES}. "
            "Save the template with pdf_save_template and pass the file path instead."
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"template_json is not valid JSON: {exc.msg} at line {exc.lineno}"
        ) from exc
    return _validate_template(data)


def save_template(template: dict, output_path: str) -> Path:
    """Write a template dict to a JSON file."""
    p = resolve_user_path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _template_summary(path: Path, file_label: str) -> dict | None:
    from pdf_ai_tools.palette import _read_json_object

    data = _read_json_object(path)
    if data is None:
        return None
    variables = data.get("variables")
    if not isinstance(variables, dict):
        variables = {}
    document = data.get("document", {})
    if not isinstance(document, dict):
        document = {}
    blocks = data.get("blocks")
    return {
        "id": path.stem,
        "name": data.get("name", path.stem),
        "file": file_label,
        "description": data.get("description", ""),
        "variables": variables,
        "palette": document.get("palette"),
        "page_size": document.get("page_size"),
        "block_count": len(blocks) if isinstance(blocks, list) else 0,
    }


def list_builtin_templates() -> list[dict[str, Any]]:
    if not _BUILTIN_DIR.exists():
        return []
    result = []
    for f in sorted(_BUILTIN_DIR.glob("*.json")):
        row = _template_summary(f, f.name)
        if row is not None:
            result.append(row)
    return result


def list_templates_in_dir(directory: str) -> list[dict[str, Any]]:
    d = resolve_user_path(directory)
    if not d.exists():
        return []
    result = []
    for f in sorted(d.glob("*.json")):
        row = _template_summary(f, str(f))
        if row is not None:
            result.append(row)
    return result


# ---------------------------------------------------------------------------
# Self description
# ---------------------------------------------------------------------------


def describe_builtin_templates() -> str:
    """Catalog of the built-in templates with the variables each one needs."""
    rows = list_builtin_templates()
    if not rows:
        return "No built-in templates are installed."
    lines = ["Built-in templates (pass the id to pdf_render_template):"]
    for row in rows:
        title = row["name"]
        label = row["id"] if title == row["id"] else f"{row['id']} ({title})"
        lines.append(f"  {label}: {row['description']}")
        variables = row["variables"]
        if variables:
            listed = ", ".join(f"{k} ({v})" for k, v in variables.items())
            lines.append(f"    variables: {listed}")
        else:
            lines.append("    variables: none")
        lines.append(
            f"    palette: {row['palette']}, page size: {row['page_size']}, "
            f"blocks: {row['block_count']}"
        )
    return "\n".join(lines)


def describe_template_schema() -> str:
    """The template JSON schema and every block kind with its arguments."""
    lines = [
        "Template JSON object.",
        "Top level keys:",
        "  name, description, version  identity strings",
        (
            "  variables  object of placeholder -> what the value is. Every "
            "{{placeholder}} used in the template must be declared here."
        ),
        (
            "  document  {page_size, margin_left_cm, margin_right_cm, "
            "margin_top_cm, margin_bottom_cm, palette, fonts}. palette is a "
            "built-in palette name or null. fonts is {body, heading, code} "
            "with family names or font file paths."
        ),
        "  metadata  {title, author, subject, keywords}",
        (
            "  header, footer  {left, center, right, font_size, color, "
            "show_on_first_page, line_below}"
        ),
        "  page_numbers  bool",
        "  watermark  string or null",
        '  blocks  list of {"kind": <kind>, "kwargs": {<arguments>}}',
        "",
        "Block kinds and their arguments:",
    ]
    dispatch = _block_dispatch()
    for kind in sorted(dispatch):
        fn = dispatch[kind]
        args = []
        for name, param in _signature_of(fn).parameters.items():
            if name == "doc_id":
                continue
            if param.default is inspect.Parameter.empty:
                args.append(name)
            else:
                args.append(f"{name}={param.default!r}")
        doc = (fn.__doc__ or "").strip().splitlines()
        summary = doc[0] if doc else ""
        lines.append(f"  {kind}({', '.join(args)}) - {summary}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Snapshot a session into a template
# ---------------------------------------------------------------------------


def session_to_template(
    session,
    name: str,
    description: str = "",
) -> dict:
    """Build a template dict from a live (or already-logged) session."""
    blocks = list(session._replay_log)
    cover = [b for b in blocks if b["kind"] == "cover_page"]
    if cover:
        blocks = cover + [b for b in blocks if b["kind"] != "cover_page"]
    fonts = {}
    if session.fonts["body"] != "Helvetica":
        fonts["body"] = session.fonts["body"]
    if session.fonts["heading"] != "Helvetica-Bold":
        fonts["heading"] = session.fonts["heading"]
    if session.fonts["code"] != "Courier":
        fonts["code"] = session.fonts["code"]
    document = {
        "page_size": session.page_size_name,
        "margin_left_cm": session.margins[0],
        "margin_right_cm": session.margins[1],
        "margin_top_cm": session.margins[2],
        "margin_bottom_cm": session.margins[3],
        "palette": session.palette_ref,
    }
    if fonts:
        document["fonts"] = fonts
    return {
        "name": name,
        "description": description,
        "version": "1",
        "variables": {},
        "document": document,
        "metadata": dict(session.metadata),
        "header": session.header.as_dict(),
        "footer": session.footer.as_dict(),
        "page_numbers": session.page_numbers,
        "watermark": session.watermark_text,
        "blocks": blocks,
    }


# ---------------------------------------------------------------------------
# Render engine
# ---------------------------------------------------------------------------


def _coerce_numeric_kwargs(kind: str, kwargs: dict, dispatch: dict) -> dict:
    """Turn numeric strings in numeric arguments into numbers."""
    params = _signature_of(dispatch[kind]).parameters
    for key, value in kwargs.items():
        annotation = params[key].annotation
        if annotation in (int, float) and isinstance(value, str):
            try:
                kwargs[key] = int(value) if annotation is int else float(value)
            except ValueError:
                raise ValueError(
                    f"Block '{kind}': {key!r} needs a number, got {value!r}"
                ) from None
    return kwargs


def render_template(
    template: dict,
    output_path: str,
    variables: dict[str, str] | None = None,
) -> str:
    """
    Render a template dict into a PDF file.

    Returns the path of the generated PDF as a string.
    Raises ValueError / RuntimeError on bad block kinds or tool errors.
    """
    # Lazy import to avoid circular deps at module load
    from pdf_ai_tools import tools
    from pdf_ai_tools.palette import load_builtin_palette, load_palette

    variables = variables or {}
    missing: set[str] = set()
    tpl = _substitute(template, variables, missing)
    if missing:
        raise ValueError(
            f"Template uses variables that were not filled: {sorted(missing)}. "
            "Pass them in variables_json."
        )
    _validate_template(tpl)

    doc_cfg = tpl.get("document", {})
    result = tools.pdf_create_document(
        output_path=output_path,
        page_size=doc_cfg.get("page_size", "A4"),
        margin_left_cm=doc_cfg.get("margin_left_cm", 2.5),
        margin_right_cm=doc_cfg.get("margin_right_cm", 2.5),
        margin_top_cm=doc_cfg.get("margin_top_cm", 2.5),
        margin_bottom_cm=doc_cfg.get("margin_bottom_cm", 2.5),
    )
    if not result.get("ok"):
        raise RuntimeError(f"pdf_create_document failed: {result.get('error')}")

    doc_id = result["doc_id"]

    # Apply palette if requested
    palette_ref = doc_cfg.get("palette")
    if palette_ref:
        try:
            if (
                palette_ref.endswith(".json")
                or "/" in palette_ref
                or "\\" in palette_ref
            ):
                palette_data = load_palette(palette_ref)
            else:
                palette_data = load_builtin_palette(palette_ref)
            from pdf_ai_tools.session import get_session

            get_session(doc_id).apply_palette(palette_data, palette_ref)
        except Exception as exc:
            raise ValueError(f"Cannot load palette '{palette_ref}'") from exc

    # Apply fonts if requested
    font_cfg = doc_cfg.get("fonts") or {}
    if font_cfg:
        from pdf_ai_tools import fonts as fonts_module
        from pdf_ai_tools.session import get_session

        session = get_session(doc_id)
        applied = {}
        variants: dict[str, str] = {}
        for role in ("body", "heading", "code"):
            ref = str(font_cfg.get(role, "") or "").strip()
            if not ref or fonts_module.is_registered(ref):
                continue
            if ref.lower().endswith((".ttf", ".otf", ".ttc", ".otc")):
                path = Path(ref).expanduser()
                if not path.is_file():
                    raise ValueError(f"Font file not found: {ref}")
            else:
                found = fonts_module.find_family(ref)
                if found is None:
                    raise ValueError(f"No installed font family named '{ref}'")
                path = found.path
            roles = fonts_module.register_family(path)
            applied[role] = roles.get("regular")
            variants.update({k: v for k, v in roles.items() if k != "regular"})
        if applied:
            session.apply_fonts(
                body=applied.get("body", ""),
                heading=applied.get("heading", ""),
                code=applied.get("code", ""),
                variants=variants,
            )

    # Metadata
    meta = tpl.get("metadata", {})
    if meta:
        tools.pdf_set_metadata(
            doc_id,
            title=meta.get("title", ""),
            author=meta.get("author", ""),
            subject=meta.get("subject", ""),
            keywords=meta.get("keywords", ""),
        )

    # Header
    hdr = tpl.get("header", {})
    if hdr:
        tools.pdf_configure_header(
            doc_id,
            left=hdr.get("left", ""),
            center=hdr.get("center", ""),
            right=hdr.get("right", ""),
            font_size=hdr.get("font_size", 9),
            color=hdr.get("color", "#718096"),
            show_on_first_page=hdr.get("show_on_first_page", True),
            line_below=hdr.get("line_below", False),
        )

    # Footer
    ftr = tpl.get("footer", {})
    if ftr:
        tools.pdf_configure_footer(
            doc_id,
            left=ftr.get("left", ""),
            center=ftr.get("center", ""),
            right=ftr.get("right", ""),
            font_size=ftr.get("font_size", 9),
            color=ftr.get("color", "#718096"),
            show_on_first_page=ftr.get("show_on_first_page", True),
        )

    if tpl.get("page_numbers"):
        tools.pdf_enable_page_numbers(doc_id, True)

    wm = tpl.get("watermark")
    if wm:
        tools.pdf_set_watermark(doc_id, wm)

    dispatch = _block_dispatch()
    for i, block in enumerate(tpl.get("blocks", [])):
        kind = block["kind"]
        kwargs = _coerce_numeric_kwargs(kind, dict(block.get("kwargs", {})), dispatch)
        fn = dispatch[kind]
        res = fn(doc_id, **kwargs)
        if not res.get("ok"):
            raise RuntimeError(f"Block {i} ({kind}) failed: {res.get('error')}")

    # Save
    save_res = tools.pdf_save_document(doc_id)
    if not save_res.get("ok"):
        raise RuntimeError(f"pdf_save_document failed: {save_res.get('error')}")

    return save_res["saved_to"]
