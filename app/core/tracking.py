# app/core/tracing.py
"""
Small shim so you can write `@traceable(...)` everywhere even if LangSmith
isn't installed or tracing is disabled. If LangSmith is available, it will
decorate functions; otherwise it no-ops.
"""
try:
    # Official LangSmith helper
    from langsmith.run_helpers import traceable  # type: ignore
except Exception:
    # Fallback: no-op decorator with the same call shape
    def traceable(*_args, **_kwargs):
        def _decorator(fn):
            return fn
        return _decorator
