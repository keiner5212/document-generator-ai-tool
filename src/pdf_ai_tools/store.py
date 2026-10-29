"""
Disk-backed session store.

The session registry lives in the server process. A client that does not keep
one process alive between tool calls loses it, and the next call with the same
doc_id fails with "No active document". This store writes the session state to
disk after every change and rebuilds it on demand, so a doc_id survives a
server restart.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

ENV_SESSION_DIR = "PDF_AI_TOOLS_SESSION_DIR"
SESSION_TTL_SECONDS = 24 * 60 * 60


def session_dir() -> Path:
    """Where the session snapshots are kept."""
    raw = os.environ.get(ENV_SESSION_DIR, "").strip()
    base = (
        Path(raw).expanduser()
        if raw
        else Path.home() / ".cache" / "pdf-ai-tools" / "sessions"
    )
    base.mkdir(parents=True, exist_ok=True)
    try:
        base.chmod(0o700)
    except OSError:
        pass
    return base


def _snapshot_path(doc_id: str) -> Path:
    safe = "".join(c for c in doc_id if c.isalnum() or c in "-_")
    return session_dir() / f"{safe}.json"


def snapshot(session) -> dict[str, Any]:
    """The part of a session that can be written to disk and replayed."""
    return {
        "doc_id": session.doc_id,
        "output_path": str(session.output_path),
        "page_size": session.page_size_name,
        "margins_cm": list(session.margins),
        "palette": session.palette,
        "palette_ref": session.palette_ref,
        "fonts": dict(session.fonts),
        "metadata": dict(session.metadata),
        "header": session.header.as_dict(),
        "footer": session.footer.as_dict(),
        "page_numbers": session.page_numbers,
        "page_number_format": session.page_number_format,
        "watermark": session.watermark_text,
        "toc_levels": list(session.toc_levels),
        "elements": [dict(entry) for entry in session._element_log],
        "blocks": [dict(block) for block in session._replay_log],
    }


def save(session) -> None:
    """Write the session state to disk."""
    path = _snapshot_path(session.doc_id)
    payload = json.dumps(snapshot(session), default=str, ensure_ascii=False)
    handle, tmp_name = tempfile.mkstemp(dir=session_dir(), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    remove_expired()


def load(doc_id: str) -> dict[str, Any] | None:
    """The stored state of a session, or None when there is none."""
    path = _snapshot_path(doc_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def remove(doc_id: str) -> None:
    """Forget the stored state of a session."""
    _snapshot_path(doc_id).unlink(missing_ok=True)


def remove_expired(ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
    """Delete snapshots older than the time to live."""
    cutoff = time.time() - ttl_seconds
    for path in session_dir().glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            continue


def stored_sessions() -> list[dict[str, Any]]:
    """The snapshots that are on disk."""
    sessions = []
    for path in sorted(session_dir().glob("*.json")):
        data = load(path.stem)
        if data and data.get("doc_id"):
            sessions.append(data)
    return sessions
