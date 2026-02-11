"""Custom hook: collect torch submodules.
DLLs are collected manually in build.spec to avoid scanning overhead."""
from PyInstaller.utils.hooks import collect_submodules

# Only collect the Python submodules
hiddenimports = collect_submodules('torch', filter=lambda name: 'test' not in name and 'benchmark' not in name)

# DLLs collected manually in build.spec
