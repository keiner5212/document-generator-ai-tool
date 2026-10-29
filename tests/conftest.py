from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_session_dir(tmp_path_factory, monkeypatch):
    """Keep the session store out of the developer's home directory."""
    monkeypatch.setenv(
        "PDF_AI_TOOLS_SESSION_DIR", str(tmp_path_factory.mktemp("sessions"))
    )
