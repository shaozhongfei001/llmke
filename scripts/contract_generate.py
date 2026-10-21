#!/usr/bin/env python3
from pathlib import Path
import argparse
from contract_toolchain import generate,is_dummy_script
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();raise SystemExit(generate(a.root.resolve()))
