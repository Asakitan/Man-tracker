"""
Obfuscate model file: rename *.pt to a random garbled name and update config.

Usage:
    python obfuscate_model.py                   # auto-find *.pt in project dir
    python obfuscate_model.py  my_model.pt      # specify a file
"""
import os
import sys
import json
import random
import string

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config_user.json")


def _gen_garbled_name(ext: str = ".pt") -> str:
    """Generate a random CJK + alphanumeric filename."""
    parts = []
    for _ in range(random.randint(5, 8)):
        parts.append(chr(random.randint(0x4E00, 0x9FFF)))
    parts.extend(random.choices(string.ascii_lowercase + string.digits, k=random.randint(3, 5)))
    random.shuffle(parts)
    return "".join(parts) + ext


def main():
    # Determine source file
    if len(sys.argv) > 1:
        src = os.path.join(PROJECT_DIR, sys.argv[1])
    else:
        # Auto-find .pt files
        pts = [f for f in os.listdir(PROJECT_DIR) if f.endswith(".pt")]
        if not pts:
            print("ERROR: No .pt model file found in project directory.")
            print("Place your model file (e.g. yolov8x-pose.pt) here and re-run.")
            return 1
        if len(pts) > 1:
            print(f"Found multiple .pt files: {pts}")
            print("Specify which one: python obfuscate_model.py <filename>")
            return 1
        src = os.path.join(PROJECT_DIR, pts[0])

    if not os.path.isfile(src):
        print(f"ERROR: File not found: {src}")
        return 1

    old_name = os.path.basename(src)
    new_name = _gen_garbled_name(os.path.splitext(old_name)[1])
    dst = os.path.join(PROJECT_DIR, new_name)

    # Rename
    os.rename(src, dst)
    print(f"Renamed: {old_name} -> {new_name}")

    # Update config_user.json
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "detector" in cfg:
            old_cfg_model = cfg["detector"].get("model_path", "")
            cfg["detector"]["model_path"] = new_name
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            print(f"Updated config_user.json: model_path '{old_cfg_model}' -> '{new_name}'")
    else:
        print(f"Warning: {CONFIG_PATH} not found, update model_path manually.")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
