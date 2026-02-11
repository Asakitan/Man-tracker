"""Custom hook: collect torchvision submodules."""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('torchvision', filter=lambda name: 'test' not in name)
