"""PDF creation, templates, and palettes for AI agents."""

# The bidi shim has to be in place before ReportLab is imported, because
# ReportLab looks for the optional rlbidi package when it loads.
from pdf_ai_tools import _bidi_compat as _bidi_compat, palette, template, tools
from pdf_ai_tools.session import PDFSession, get_session, list_sessions

__all__ = ["PDFSession", "get_session", "list_sessions", "palette", "template", "tools"]
