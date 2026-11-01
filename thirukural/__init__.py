"""Build the Thirukural slide deck from the local corpus."""

from thirukural.build import build
from thirukural.repository import load_verses

__all__ = ["build", "load_verses"]
