"""
Debug script: Check torch DLL dependencies
Run this in the dist\ManTracker folder to diagnose c10.dll loading issues.
"""
import os
import sys

print("=" * 60)
print("Torch DLL Debug Script")
print("=" * 60)

# Check paths
print(f"\nPython executable: {sys.executable}")
print(f"Frozen: {getattr(sys, 'frozen', False)}")

if getattr(sys, 'frozen', False):
    base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    print(f"_MEIPASS: {base}")
else:
    base = os.path.dirname(os.path.abspath(__file__))
    print(f"Script dir: {base}")

# Check torch/lib
torch_lib = os.path.join(base, 'torch', 'lib')
print(f"\nLooking for torch/lib at: {torch_lib}")
print(f"Exists: {os.path.isdir(torch_lib)}")

if os.path.isdir(torch_lib):
    dlls = [f for f in os.listdir(torch_lib) if f.endswith('.dll')]
    print(f"DLLs found: {len(dlls)}")
    for dll in sorted(dlls)[:10]:
        print(f"  - {dll}")
    if len(dlls) > 10:
        print(f"  ... and {len(dlls) - 10} more")
    
    # Check c10.dll specifically
    c10_path = os.path.join(torch_lib, 'c10.dll')
    print(f"\nc10.dll exists: {os.path.isfile(c10_path)}")
    if os.path.isfile(c10_path):
        print(f"c10.dll size: {os.path.getsize(c10_path)} bytes")

# Check PATH
print(f"\nPATH contains torch/lib: {torch_lib in os.environ.get('PATH', '')}")

# Try to add DLL directory
print("\nAttempting to add DLL directory...")
if hasattr(os, 'add_dll_directory'):
    try:
        os.add_dll_directory(torch_lib)
        print("  os.add_dll_directory: SUCCESS")
    except Exception as e:
        print(f"  os.add_dll_directory: FAILED - {e}")

# Add to PATH
os.environ['PATH'] = torch_lib + os.pathsep + os.environ.get('PATH', '')
print("  Added to PATH: SUCCESS")

# Try importing torch
print("\n" + "=" * 60)
print("Attempting to import torch...")
print("=" * 60)

try:
    import torch
    print(f"SUCCESS! torch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    
    # Try to get more info
    import ctypes
    print("\nTrying to load c10.dll directly with ctypes...")
    try:
        c10 = ctypes.CDLL(os.path.join(torch_lib, 'c10.dll'))
        print("  c10.dll loaded successfully")
    except Exception as e2:
        print(f"  c10.dll failed: {e2}")

print("\n" + "=" * 60)
print("Debug complete")
print("=" * 60)
input("Press Enter to exit...")
