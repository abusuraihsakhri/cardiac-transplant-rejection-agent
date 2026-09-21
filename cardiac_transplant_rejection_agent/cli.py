"""Compatibility entry point for the repository CLI."""

from cli import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())
