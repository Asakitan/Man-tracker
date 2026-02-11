"""
Asset file management with obfuscated naming
"""
import os
import shutil
import random
import string
import tempfile
import atexit


class ModelManager:
    """Manages model files with randomized naming on each launch"""

    _instance = None
    _temp_dir = None
    _mapping = {}  # obfuscated_path -> {original, tag}

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="~")
        self._mapping = {}
        atexit.register(self._cleanup)

    def prepare(self, original_path: str, internal_tag: str = "") -> str:
        """
        Copy model file to temp directory with a randomized garbled name.
        Returns the new (obfuscated) path. Internally tracks the original identity.
        """
        if not os.path.isfile(original_path):
            return original_path  # fallback if file doesn't exist

        ext = os.path.splitext(original_path)[1]

        # Generate garbled filename: CJK chars + random alphanumeric
        garbled_chars = []
        for _ in range(random.randint(6, 10)):
            garbled_chars.append(chr(random.randint(0x4e00, 0x9fff)))
        garbled_chars.extend(random.choices(
            string.ascii_lowercase + string.digits, k=random.randint(3, 6)
        ))
        random.shuffle(garbled_chars)
        garbled_name = ''.join(garbled_chars) + ext

        new_path = os.path.join(self._temp_dir, garbled_name)
        shutil.copy2(original_path, new_path)

        # Internal tracking with tag
        self._mapping[new_path] = {
            "original": os.path.basename(original_path),
            "tag": internal_tag or "asset_" + os.path.splitext(os.path.basename(original_path))[0],
            "identity": f"[internal:{os.path.basename(original_path)}]",
        }

        return new_path

    def get_info(self, obfuscated_path: str) -> dict:
        """Get internal tracking info for an obfuscated path"""
        return self._mapping.get(obfuscated_path, {})

    def get_identity(self, obfuscated_path: str) -> str:
        """Get the internal identity tag"""
        info = self._mapping.get(obfuscated_path, {})
        return info.get("identity", "unknown")

    def _cleanup(self):
        """Remove temp directory and all obfuscated files"""
        if self._temp_dir and os.path.isdir(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass
