#!/usr/bin/env python3
"""Run the thirteen independent regression roots; nonzero child exit is never masked."""
import subprocess,sys
from pathlib import Path
if __name__=='__main__':
 root=Path(__file__).resolve().parents[1]
 raise SystemExit(subprocess.run([sys.executable,'-m','pytest','tests/test_review_regressions.py','-q'],cwd=root).returncode)
