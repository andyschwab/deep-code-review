#!/usr/bin/env python3
"""Compatibility shim: the decision council is now Veche (`veche.py`). Forwards every argument unchanged.

Side effects: runs veche.py in-process, so its exit code (0, 3 or 4) and output are exactly Veche's.
"""
import runpy
import sys
from pathlib import Path

target = str(Path(__file__).with_name("veche.py"))
sys.argv[0] = target
runpy.run_path(target, run_name="__main__")
