"""FastAPI composition root; import has no storage or service side effects."""
from .app import create_app

__all__ = ["create_app"]
