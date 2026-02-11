"""
Runtime obfuscation for class and function identifiers.

When activated, this module walks through all project modules and replaces
__name__ / __qualname__ attributes of classes and functions with random
strings.  This prevents external tools (memory scanners, process inspectors)
from discovering meaningful identifier names at runtime.

Usage (call once at application startup, after all modules are imported):
    from utils.runtime_obf import obfuscate_runtime
    obfuscate_runtime()
"""
import sys
import types
import random
import string
import inspect

# Modules whose members should be obfuscated (top-level package names)
_TARGET_PACKAGES = ("config", "core", "gui", "app", "utils")

# Names / base classes to NEVER rename (framework internals that must stay)
_SKIP_NAMES = frozenset({
    "__init__", "__del__", "__repr__", "__str__", "__hash__", "__eq__",
    "__lt__", "__le__", "__gt__", "__ge__", "__ne__",
    "__getattr__", "__setattr__", "__delattr__", "__getattribute__",
    "__get__", "__set__", "__delete__",
    "__call__", "__len__", "__getitem__", "__setitem__", "__delitem__",
    "__iter__", "__next__", "__contains__", "__reversed__",
    "__enter__", "__exit__",
    "__add__", "__sub__", "__mul__", "__truediv__",
    "__bool__", "__int__", "__float__",
    "__new__", "__init_subclass__", "__class_getitem__",
    # Qt slots / signals must keep original names
    "run", "paintEvent", "mousePressEvent", "mouseReleaseEvent",
    "mouseMoveEvent", "keyPressEvent", "keyReleaseEvent",
    "resizeEvent", "closeEvent", "showEvent", "hideEvent",
    "timerEvent", "event", "eventFilter",
})

# Prefixes used in generated names (look like compiler-generated mangled names)
_CHARSET = string.ascii_letters + string.digits + "_"


def _rand_id(length: int = 12) -> str:
    """Generate a random identifier that looks like a mangled symbol."""
    first = random.choice(string.ascii_letters + "_")
    rest = "".join(random.choices(_CHARSET, k=length - 1))
    return first + rest


def _should_process_module(mod_name: str) -> bool:
    """Return True if the module belongs to our project."""
    parts = mod_name.split(".")
    return len(parts) > 0 and parts[0] in _TARGET_PACKAGES


def _obfuscate_function(func: types.FunctionType, name_map: dict):
    """Replace __name__ and __qualname__ of a function with random ids."""
    orig = func.__qualname__
    if orig in name_map:
        new_name = name_map[orig]
    else:
        new_name = _rand_id()
        name_map[orig] = new_name
    try:
        func.__name__ = new_name
        func.__qualname__ = new_name
    except (AttributeError, TypeError):
        pass


def _obfuscate_class(cls, name_map: dict):
    """Replace __name__ and __qualname__ of a class and its methods."""
    orig_qual = getattr(cls, "__qualname__", cls.__name__)
    if orig_qual in name_map:
        new_cls_name = name_map[orig_qual]
    else:
        new_cls_name = _rand_id()
        name_map[orig_qual] = new_cls_name
    try:
        cls.__name__ = new_cls_name
        cls.__qualname__ = new_cls_name
    except (AttributeError, TypeError):
        pass

    # Obfuscate methods
    for attr_name in list(vars(cls)):
        if attr_name in _SKIP_NAMES:
            continue
        obj = vars(cls).get(attr_name)
        if isinstance(obj, types.FunctionType):
            _obfuscate_function(obj, name_map)
        elif isinstance(obj, staticmethod):
            inner = obj.__func__ if hasattr(obj, "__func__") else None
            if inner and isinstance(inner, types.FunctionType):
                _obfuscate_function(inner, name_map)
        elif isinstance(obj, classmethod):
            inner = obj.__func__ if hasattr(obj, "__func__") else None
            if inner and isinstance(inner, types.FunctionType):
                _obfuscate_function(inner, name_map)
        elif isinstance(obj, property):
            for accessor in (obj.fget, obj.fset, obj.fdel):
                if accessor and isinstance(accessor, types.FunctionType):
                    _obfuscate_function(accessor, name_map)


def obfuscate_runtime():
    """
    Walk all imported project modules and randomize class/function names.
    Call this ONCE after all modules are imported and before entering the
    main event loop.
    """
    name_map: dict = {}

    modules = [
        (name, mod)
        for name, mod in list(sys.modules.items())
        if mod is not None and _should_process_module(name)
    ]

    for mod_name, mod in modules:
        for attr_name in list(dir(mod)):
            obj = getattr(mod, attr_name, None)
            if obj is None:
                continue

            # Obfuscate classes
            if isinstance(obj, type):
                # Only process classes defined in our project
                defining_mod = getattr(obj, "__module__", "")
                if _should_process_module(defining_mod):
                    _obfuscate_class(obj, name_map)

            # Obfuscate standalone functions
            elif isinstance(obj, types.FunctionType):
                defining_mod = getattr(obj, "__module__", "")
                if _should_process_module(defining_mod) and attr_name not in _SKIP_NAMES:
                    _obfuscate_function(obj, name_map)

    return name_map
