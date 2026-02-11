"""
Runtime hook: Setup environment for torch in PyInstaller frozen app.
This must run BEFORE any torch imports.
"""
import os
import sys
import glob
import ctypes

# Debug check - should always print
_HOOK_DEBUG = os.environ.get('MANTRACKER_DEBUG', '0') == '1'
if _HOOK_DEBUG:
    print("[HOOK] pyi_rth_torch.py STARTING")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. ENVIRONMENT VARIABLES - Disable torch features that need source code
# ═══════════════════════════════════════════════════════════════════════════════

# Disable torch.compile (requires source code inspection)
os.environ['TORCH_COMPILE_DISABLE'] = '1'
os.environ['TORCHDYNAMO_DISABLE'] = '1'

# Disable inductor (also needs source)
os.environ['TORCH_INDUCTOR_DISABLE'] = '1'

# Set PyTorch to prefer CUDA
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')

# ═══════════════════════════════════════════════════════════════════════════════
# 2. DLL PATH SETUP - Register DLL directories for Windows FIRST
# ═══════════════════════════════════════════════════════════════════════════════

def _setup_dll_paths():
    """Add ALL DLL directories before any DLL loading."""
    if sys.platform != 'win32':
        return
    
    meipass = getattr(sys, '_MEIPASS', None)
    if not meipass:
        meipass = os.path.dirname(sys.executable)
    
    exe_dir = os.path.dirname(sys.executable)
    
    # Collect ALL directories containing DLLs
    dll_dirs = set()
    dll_dirs.add(meipass)
    dll_dirs.add(exe_dir)
    dll_dirs.add(os.path.join(meipass, 'torch', 'lib'))
    dll_dirs.add(os.path.join(meipass, 'torch'))
    
    # Find all directories with DLLs
    for root, dirs, files in os.walk(meipass):
        for f in files:
            if f.lower().endswith('.dll'):
                dll_dirs.add(root)
                break
    
    # Register ALL directories
    for dll_dir in dll_dirs:
        if not os.path.isdir(dll_dir):
            continue
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(dll_dir)
            except (OSError, FileNotFoundError):
                pass
    
    # Build comprehensive PATH
    path_parts = list(dll_dirs)
    path_parts.append(os.environ.get('PATH', ''))
    os.environ['PATH'] = os.pathsep.join(path_parts)

_setup_dll_paths()

# ═══════════════════════════════════════════════════════════════════════════════
# 3. PRE-LOAD ALL CUDA DLLs IN CORRECT ORDER
# ═══════════════════════════════════════════════════════════════════════════════

def _preload_cuda_dlls():
    """Pre-load CUDA DLLs in dependency order before torch imports them."""
    if sys.platform != 'win32':
        return
    
    _DEBUG = os.environ.get('MANTRACKER_DEBUG', '0') == '1'
    
    meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    
    if _DEBUG:
        print(f"[PRELOAD] MEIPASS: {meipass}")
        print(f"[PRELOAD] torch/lib exists: {os.path.isdir(os.path.join(meipass, 'torch', 'lib'))}")
    
    # Order matters! Load dependencies first
    dll_load_order = [
        # VC++ runtime (should be loaded)
        'vcruntime140.dll',
        'msvcp140.dll',
        'vcruntime140_1.dll',
        # CUDA runtime
        'cudart64_*.dll',
        # Core CUDA libs
        'cublas64_*.dll',
        'cublasLt64_*.dll',
        'cufft64_*.dll',
        'curand64_*.dll',
        'cusolver64_*.dll',
        'cusparse64_*.dll',
        # cuDNN
        'cudnn64_*.dll',
        'cudnn_ops64_*.dll',
        'cudnn_cnn64_*.dll',
        'cudnn_adv64_*.dll',
        'cudnn_graph64_*.dll',
        'cudnn_heuristic64_*.dll',
        'cudnn_engines_precompiled64_*.dll',
        'cudnn_engines_runtime_compiled64_*.dll',
        # NVRTC
        'nvrtc*.dll',
        'nvJitLink*.dll',
        # OpenMP
        'libiomp5md.dll',
        # Torch core (these depend on CUDA)
        'c10.dll',
        'c10_cuda.dll',
        'torch_cpu.dll',
        'torch_cuda.dll',
        'torch.dll',
        'torch_python.dll',
    ]
    
    search_dirs = [
        meipass,
        os.path.join(meipass, 'torch', 'lib'),
    ]
    
    loaded = set()
    
    for pattern in dll_load_order:
        for search_dir in search_dirs:
            if '*' in pattern:
                matches = glob.glob(os.path.join(search_dir, pattern))
            else:
                match_path = os.path.join(search_dir, pattern)
                matches = [match_path] if os.path.isfile(match_path) else []
            
            for dll_path in matches:
                dll_name = os.path.basename(dll_path).lower()
                if dll_name in loaded:
                    continue
                try:
                    ctypes.CDLL(dll_path)
                    loaded.add(dll_name)
                    if _DEBUG:
                        print(f"[PRELOAD] OK: {dll_name}")
                except OSError as e:
                    if _DEBUG:
                        print(f"[PRELOAD] FAILED: {dll_name}: {e}")
    
    if _DEBUG:
        print(f"[PRELOAD] Total loaded: {len(loaded)}")

_preload_cuda_dlls()

# ═══════════════════════════════════════════════════════════════════════════════
# 4. MONKEY-PATCH INSPECT.GETSOURCE - Prevent crashes when torch tries to read source
# ═══════════════════════════════════════════════════════════════════════════════

def _patch_inspect():
    """Patch inspect module to handle missing source files gracefully."""
    try:
        import inspect
        _original_getsource = inspect.getsource
        _original_getsourcefile = inspect.getsourcefile
        _original_getsourcelines = inspect.getsourcelines
        _original_findsource = inspect.findsource
        
        def _safe_getsource(obj):
            try:
                return _original_getsource(obj)
            except (OSError, TypeError, IndentationError):
                return ""
        
        def _safe_getsourcefile(obj):
            try:
                return _original_getsourcefile(obj)
            except (OSError, TypeError):
                return None
        
        def _safe_getsourcelines(obj):
            try:
                return _original_getsourcelines(obj)
            except (OSError, TypeError, IndentationError):
                return ([], 0)
        
        def _safe_findsource(obj):
            try:
                return _original_findsource(obj)
            except (OSError, TypeError, IndentationError):
                return ([], 0)
        
        inspect.getsource = _safe_getsource
        inspect.getsourcefile = _safe_getsourcefile
        inspect.getsourcelines = _safe_getsourcelines
        inspect.findsource = _safe_findsource
    except Exception:
        pass

_patch_inspect()

# ═══════════════════════════════════════════════════════════════════════════════
# 5. PATCH LINECACHE - Prevent crashes when torch tries to read source lines
# ═══════════════════════════════════════════════════════════════════════════════

def _patch_linecache():
    """Patch linecache to handle missing files gracefully."""
    try:
        import linecache
        _original_getlines = linecache.getlines
        
        def _safe_getlines(filename, module_globals=None):
            try:
                return _original_getlines(filename, module_globals)
            except Exception:
                return []
        
        linecache.getlines = _safe_getlines
    except Exception:
        pass

_patch_linecache()

if _HOOK_DEBUG:
    print("[HOOK] pyi_rth_torch.py COMPLETED")