#!/usr/bin/env python3
from pathlib import Path
import argparse,shutil
from baseline_support import ROOT,atomic_json
from contract_runtime import load,ContractViolation
from loop_guard import ldir,update_views

def main():
 p=argparse.ArgumentParser();p.add_argument('loop_id');a=p.parse_args();dest=ldir(ROOT,a.loop_id)
 if dest.exists():raise ContractViolation('loop already exists')
 shutil.copytree(ROOT/'loops/_template',dest)
 import yaml
 doc=load(dest/'LOOP.yaml');doc['loop_id']=a.loop_id;(dest/'LOOP.yaml').write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False))
 state=load(dest/'STATE.json');state['loop_id']=a.loop_id;atomic_json(dest/'STATE.json',state);update_views(dest,state)
 print('created DRAFT; register approved plan/scope/dependencies and gates before TL arm')
if __name__=='__main__':
 try:main()
 except Exception as e:raise SystemExit('FAIL: '+str(e))
