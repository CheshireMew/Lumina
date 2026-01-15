from typing import Any

class FrozenProxy:
    """
    A recursive proxy that enforces read-only access to the wrapped object.
    Attempts to modify attributes will raise a TypeError.
    """
    def __init__(self, wrapped: Any):
        # Use object.__setattr__ to bypass our own __setattr__ which checks for _wrapped
        object.__setattr__(self, "_wrapped", wrapped)

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._wrapped, name)
        
        # Determine if we should wrap the result recursively
        # We wrap standard mutable collections (that behave like namespaces/dicts)
        # or arbitrary objects if they are likely config nodes (SimpleNamespace, generic objects).
        # We do NOT wrap primitives, strings, numbers, booleans.
        
        if value is None or isinstance(value, (str, int, float, bool, bytes)):
            return value
            
        # If it's a dict (common in configs), wrap it?
        # But our config object might be Pydantic models or SimpleNamespace.
        # If it's a Pydantic model, it has __dict__, so we can wrap it.
        # If it's a list, we might need a FrozenList proxy (skipped for simplicity unless needed).
        
        if hasattr(value, "__dict__") or isinstance(value, dict):
            return FrozenProxy(value)
            
        return value

    def __setattr__(self, name: str, value: Any):
        if name == "_wrapped": # Should not happen via normal assignment due to __init__ logic but good safety
             raise TypeError("FrozenProxy is immutable.")
        raise TypeError(f"Configuration is read-only. Cannot set '{name}' via Plugin Context.")

    def __getitem__(self, key: Any) -> Any:
        # Support dict-like access if wrapped object supports it
        value = self._wrapped[key]
        if hasattr(value, "__dict__") or isinstance(value, dict):
            return FrozenProxy(value)
        return value

    def __setitem__(self, key: Any, value: Any):
        raise TypeError(f"Configuration is read-only. Cannot set key '{key}' via Plugin Context.")

    def __repr__(self):
        return f"<FrozenProxy for {repr(self._wrapped)}>"
