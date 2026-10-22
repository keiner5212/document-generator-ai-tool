# mcp.cli calls sys.exit when the optional typer extra is absent.

from PyInstaller.utils.hooks import collect_all, is_module_or_submodule

datas, binaries, hiddenimports = collect_all(
    "mcp",
    filter_submodules=lambda name: not is_module_or_submodule(name, "mcp.cli"),
)
