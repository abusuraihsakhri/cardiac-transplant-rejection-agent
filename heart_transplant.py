#!/usr/bin/env python3
"""Compatibility forwarder for the cardiac transplant surveillance tool."""

from cardiac_transplant_rejection import *  # noqa: F403
from cli import main

if __name__ == "__main__":
    raise SystemExit(main())
