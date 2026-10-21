#!/usr/bin/env python3
"""Freeze/check the technical control files. This is not business/QA approval."""
from pathlib import Path
import argparse,json
from contract_runtime import filehash,load,ContractViolation
from baseline_support import ROOT,atomic_json
MANIFEST='docs/baseline/FROZEN-MANIFEST.json'

def controls(root):
 out=[]
 for base in ['scripts','contracts','.codebuddy','.cursor','generated','docs/policies','docs/roles','docs/baseline','docs/upstream']:
  for p in (root/base).rglob('*'):
   if not p.is_file() or p.suffix in ['.pyc','.log'] or '__pycache__' in p.parts:continue
   rel=p.relative_to(root).as_posix()
   if rel==MANIFEST or rel.startswith(('contracts/build/','docs/baseline/validation/')):continue
   out.append(rel)
 for p in (root/'loops').glob('*/LOOP.yaml'):out.append(p.relative_to(root).as_posix())
 for p in (root/'tests').glob('*.py'):out.append(p.relative_to(root).as_posix())
 for p in (root/'tests/fixtures').rglob('*'):
  if p.is_file():out.append(p.relative_to(root).as_posix())
 for rel in ['tests/conftest.py','Makefile','AI_GUIDE.md','README.md','VERSION','requirements.txt','requirements.lock','docs/PROJECT-PLAN.yaml','docs/PROJECT-BRIEF.md','docs/DESIGN-TRACE.md','docs/SDD-ENGINEERING.md','docs/LOOP-ENGINEERING.md','docs/SHARED-MEMORY.md','docs/MULTI-CONTRACT.md','docs/API-LAYERING.md','.gitignore','.security-allowlist','docs/adr/ADR-INDEX.md']:
  if(root/rel).is_file():out.append(rel)
 return sorted(set(out))

def run(root,write=False):
 root=Path(root);files=controls(root);current={x:filehash(root/x) for x in files}
 if write:
  atomic_json(root/MANIFEST,{'baseline_version':'1.1.0','authority':'user requested overlay baseline patch on 2026-10-20','technical_status':'FROZEN_ARTIFACT','business_status':'BLOCKED_BY_REAL_P0','independent_qa':'PENDING','files':current});return []
 old=load(root/MANIFEST)
 if old.get('baseline_version')!='1.1.0':return ['wrong baseline version']
 recorded=old.get('files',{});errors=[]
 if set(recorded)!=set(current):errors.append('frozen control file set changed')
 errors.extend('frozen control changed: '+k for k in current.keys()&recorded.keys() if current[k]!=recorded[k])
 return errors

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--write',action='store_true');a=p.parse_args()
 try:errors=run(a.root.resolve(),a.write)
 except Exception as e:errors=[str(e)]
 for e in errors:print('FAIL:',e)
 print('baseline:', 'FAIL' if errors else 'PASS', '(technical artifact only; independent QA/business readiness separate)')
 return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
