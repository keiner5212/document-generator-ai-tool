"""User file paths stay on the client machine. Built-in data stays in the install."""

from __future__ import annotations

from pathlib import Path


def resolve_user_path(path: str | Path) -> Path:
    """Absolute path. `~` is the home directory. A relative path uses the client cwd."""
    return Path(path).expanduser().resolve()


def resolve_installed_or_user(path: str, installed_dir: Path) -> Path:
    """A bare filename uses the installed copy when that file exists.

    An absolute path, a `~` path, or a path with a directory is the user's file.
    """
    raw = Path(path).expanduser()
    if raw.is_absolute() or raw.parent != Path("."):
        return raw.resolve()
    installed = installed_dir / raw.name
    if installed.is_file():
        return installed
    return (Path.cwd() / raw.name).resolve()
