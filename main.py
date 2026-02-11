"""
Application entry point
"""
import os
import sys
import traceback

# Global exception handler for frozen app
def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch all unhandled exceptions and log them."""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"[FATAL ERROR]\n{error_msg}", flush=True)
    # Also write to a log file
    try:
        log_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else '.', 'crash.log')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        print(f"[FATAL] Crash log written to: {log_path}", flush=True)
    except:
        pass
    # Show message box on Windows
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"ManTracker crashed:\n\n{exc_value}\n\nSee crash.log for details", "Error", 0x10)
        except:
            pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _global_exception_handler

# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL: Set up DLL paths BEFORE any other imports (especially torch)
# ═══════════════════════════════════════════════════════════════════════════════
def _early_dll_setup():
    """Must run before ANY import that might load torch."""
    if sys.platform != 'win32':
        return
    
    if getattr(sys, 'frozen', False):
        # PyInstaller frozen app
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        exe_dir = os.path.dirname(sys.executable)
        dll_dirs = [base, exe_dir]
        
        for dll_dir in dll_dirs:
            if os.path.isdir(dll_dir):
                # Python 3.8+ DLL directory registration
                if hasattr(os, 'add_dll_directory'):
                    try:
                        os.add_dll_directory(dll_dir)
                    except Exception:
                        pass
                # PATH fallback
                path = os.environ.get('PATH', '')
                if dll_dir not in path:
                    os.environ['PATH'] = dll_dir + os.pathsep + path

_early_dll_setup()
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
from pathlib import Path

# --- Project path setup (works for dev and PyInstaller frozen) ---
if getattr(sys, 'frozen', False):
    _base = os.path.dirname(sys.executable)
    sys.path.insert(0, _base)
    # Also add _MEIPASS for bundled modules
    _meipass = getattr(sys, '_MEIPASS', None)
    if _meipass and _meipass not in sys.path:
        sys.path.insert(0, _meipass)
else:
    sys.path.insert(0, str(Path(__file__).parent))

# Early debug output (before any complex imports)
print("[STARTUP] ManTracker initializing...", flush=True)
print(f"[STARTUP] Python: {sys.version}", flush=True)
print(f"[STARTUP] Frozen: {getattr(sys, 'frozen', False)}", flush=True)
if getattr(sys, 'frozen', False):
    print(f"[STARTUP] _MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}", flush=True)
    print(f"[STARTUP] Executable: {sys.executable}", flush=True)

# --- Stealth: hide console window & randomize process name ---
# Set MANTRACKER_DEBUG=1 to see console output
from utils.process_hider import setup_stealth
setup_stealth()

# Fix Windows CUDA PyTorch DLL loading (works in dev, venv, and PyInstaller frozen)
def _fix_torch_dll():
    """Register all DLL search directories needed by PyTorch / CUDA before
    ``import torch`` runs.  On Python 3.8+ Windows uses
    ``os.add_dll_directory`` **and** falls back to PATH for older loaders."""
    if sys.platform != "win32":
        return

    _dirs_to_add: list[str] = []          # unique, ordered
    _seen: set[str] = set()

    def _add(d: str):
        d = os.path.normpath(d)
        if d not in _seen and os.path.isdir(d):
            _seen.add(d)
            _dirs_to_add.append(d)

    # ---- 0) Project directory itself (DLLs copied here) -----------------
    _project_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        _project_dir = os.path.dirname(sys.executable)
    _add(_project_dir)

    # ---- locate torch/lib ------------------------------------------------
    torch_lib: str | None = None

    # a) importlib (most accurate – works in venv / system / conda)
    try:
        import importlib.util
        spec = importlib.util.find_spec("torch")
        if spec and spec.origin:
            _candidate = os.path.join(os.path.dirname(spec.origin), "lib")
            if os.path.isdir(_candidate):
                torch_lib = os.path.normpath(_candidate)
    except Exception:
        pass

    # b) brute-force candidates
    if not torch_lib:
        _candidates = []
        _meipass = getattr(sys, '_MEIPASS', None)
        if _meipass:
            _candidates.append(os.path.join(_meipass, "torch", "lib"))
        exe_dir = os.path.dirname(sys.executable)
        _candidates.append(os.path.join(exe_dir, "torch", "lib"))
        _candidates.append(os.path.join(exe_dir, "Lib", "site-packages", "torch", "lib"))
        _candidates.append(os.path.join(exe_dir, "lib", "site-packages", "torch", "lib"))
        for sp in sys.path:
            _candidates.append(os.path.join(sp, "torch", "lib"))
        for c in _candidates:
            c = os.path.normpath(c)
            if os.path.isdir(c) and any(
                os.path.isfile(os.path.join(c, n))
                for n in ("c10.dll", "torch_cpu.dll", "torch.dll")
            ):
                torch_lib = c
                break

    if not torch_lib:
        return  # torch not installed – nothing to fix

    # ---- gather all DLL directories --------------------------------------
    _add(torch_lib)
    # parent of lib (torch/ root) – some DLLs next to __init__.py
    _add(os.path.dirname(torch_lib))

    # nvidia pip packages: site-packages/nvidia/<pkg>/bin  AND  .../lib
    site_packages = os.path.normpath(os.path.join(torch_lib, "..", ".."))
    nvidia_root = os.path.join(site_packages, "nvidia")
    if os.path.isdir(nvidia_root):
        for pkg_name in os.listdir(nvidia_root):
            pkg_dir = os.path.join(nvidia_root, pkg_name)
            if not os.path.isdir(pkg_dir):
                continue
            for sub in ("bin", "lib"):
                d = os.path.join(pkg_dir, sub)
                if os.path.isdir(d):
                    _add(d)
            # some packages have DLLs directly in the package root
            if any(f.lower().endswith(".dll") for f in os.listdir(pkg_dir) if os.path.isfile(os.path.join(pkg_dir, f))):
                _add(pkg_dir)

    # CUDA Toolkit from environment
    for env_var in ("CUDA_PATH", "CUDA_HOME"):
        cuda = os.environ.get(env_var)
        if cuda:
            _add(os.path.join(cuda, "bin"))
            _add(os.path.join(cuda, "lib", "x64"))

    # CUDA_PATH_V* (e.g. CUDA_PATH_V12_1)
    for k, v in os.environ.items():
        if k.startswith("CUDA_PATH_V"):
            _add(os.path.join(v, "bin"))

    # cuDNN – sometimes separate
    cudnn = os.environ.get("CUDNN_PATH") or os.environ.get("CUDNN_HOME")
    if cudnn:
        _add(os.path.join(cudnn, "bin"))

    # ---- apply -----------------------------------------------------------
    # 1. os.add_dll_directory  (Python 3.8+ safe DLL search)
    for d in _dirs_to_add:
        try:
            os.add_dll_directory(d)
        except (OSError, AttributeError):
            pass

    # 2. Prepend to PATH (fallback for legacy LoadLibrary calls)
    existing_path = os.environ.get("PATH", "")
    new_parts = [d for d in _dirs_to_add if d not in existing_path]
    if new_parts:
        os.environ["PATH"] = os.pathsep.join(new_parts) + os.pathsep + existing_path

    # 3. Try to pre-load c10.dll so its transitive deps are resolved while
    #    all search dirs are active
    try:
        import ctypes
        ctypes.CDLL(os.path.join(torch_lib, "c10.dll"))
    except Exception:
        pass

_fix_torch_dll()

# Wrap imports in try/except for debugging
print("[STARTUP] Importing config...", flush=True)
try:
    from config import AppConfig, SkeletonPoint, DetectorConfig, TrackerConfig, MouseConfig, VideoConfig
    print("[STARTUP] config imported successfully", flush=True)
except Exception as e:
    print(f"[ERROR] Failed to import config: {e}", flush=True)
    traceback.print_exc()
    raise

print("[STARTUP] Importing utils.resource_path...", flush=True)
try:
    from utils.resource_path import resource_path, app_dir, config_dir
    print("[STARTUP] utils.resource_path imported successfully", flush=True)
except Exception as e:
    print(f"[ERROR] Failed to import utils.resource_path: {e}", flush=True)
    traceback.print_exc()
    raise


def parse_args():
    parser = argparse.ArgumentParser(description="Application")

    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode",
    )

    parser.add_argument(
        "-s", "--source",
        type=str,
        default="0",
        help="Video source: file path or camera index (default: 0)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output video path (optional)"
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Disable preview window"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="model-pose-x.pt",
        help="Model path (default: model-pose-x.pt)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=["cuda", "cpu"],
        help="Inference device (default: cuda)"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.5,
        help="Detection confidence threshold (default: 0.5)"
    )

    parser.add_argument(
        "--no-mouse",
        action="store_true",
        help="Disable mouse control"
    )
    parser.add_argument(
        "--target-point",
        type=str,
        default="NOSE",
        choices=[p.name for p in SkeletonPoint],
        help="Target skeleton point (default: NOSE)"
    )
    parser.add_argument(
        "--target-id",
        type=int,
        default=None,
        help="Target track ID (default: track first person)"
    )
    parser.add_argument(
        "--smoothing",
        type=float,
        default=0.3,
        help="Mouse smoothing factor 0-1 (default: 0.3)"
    )

    return parser.parse_args()


def run_gui(config: AppConfig | None = None):
    from PyQt6.QtWidgets import QApplication
    from gui import MainWindow

    # Obfuscate all class/function names at runtime
    from utils.runtime_obf import obfuscate_runtime
    obfuscate_runtime()

    app = QApplication(sys.argv)
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


def run_cli(args):
    from app import VideoProcessor

    # Obfuscate all class/function names at runtime
    from utils.runtime_obf import obfuscate_runtime
    obfuscate_runtime()

    # Resolve model path for packaged environment
    model_path = args.model
    resolved = resource_path(model_path)
    if os.path.isfile(resolved):
        model_path = resolved

    config = AppConfig(
        detector=DetectorConfig(
            model_path=model_path,
            device=args.device,
            conf_threshold=args.conf,
        ),
        tracker=TrackerConfig(),
        mouse=MouseConfig(
            enable_mouse_control=not args.no_mouse,
            target_skeleton_point=SkeletonPoint[args.target_point],
            target_track_id=args.target_id,
            smoothing_factor=args.smoothing,
        ),
        video=VideoConfig(
            source=args.source,
            output_path=args.output,
            show_preview=not args.no_preview,
        ),
    )

    processor = VideoProcessor(config)
    try:
        processor.run(args.source, args.output)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1
    return 0


def main():
    args = parse_args()

    if args.cli:
        return run_cli(args)
    else:
        run_gui()
        return 0


if __name__ == "__main__":
    sys.exit(main())
