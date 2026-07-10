"""Kavach backend entrypoint.

Run from the backend/ directory:

    uvicorn main:app --reload --port 8000
"""
from kavach.api import app

__all__ = ["app"]
