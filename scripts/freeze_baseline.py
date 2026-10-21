#!/usr/bin/env python3
"""Freeze/check the technical control files. This is not business/QA approval."""
from pathlib import Path
import argparse,json
from contract_runtime import filehash,load,ContractViolation
from baseline_support import ROOT,atomic_json,now
MANIFEST='docs/baseline/FROZEN-MANIFEST.json'
AUTHORITY='docs/baseline/BASELINE-AUTHORITY.yaml'
AUTHORITY_FIELDS=['authority','authorized_by','authorized_at','scope','change_list']

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

def baseline_version(root):
 """版本号唯一来源是 VERSION 文件；脚本内不得另存一份（旧实现硬编码 '1.1.0'）。"""
 p=Path(root)/'VERSION'
 if not p.is_file():raise ContractViolation('VERSION missing')
 v=p.read_text(encoding='utf-8').strip()
 if not v:raise ContractViolation('VERSION empty')
 return v

def baseline_authority(root):
 """冻结元数据唯一来源是 BASELINE-AUTHORITY.yaml；缺失即拒绝，不得静默沿用旧文案。"""
 p=Path(root)/AUTHORITY
 if not p.is_file():
  raise ContractViolation(AUTHORITY+' missing; refuse to freeze with legacy/hardcoded authority text')
 value=load(p)
 missing=[k for k in AUTHORITY_FIELDS if not value.get(k)]
 if missing:raise ContractViolation(AUTHORITY+' missing fields: '+', '.join(missing))
 return value

def run(root,write=False):
 root=Path(root);files=controls(root);current={x:filehash(root/x) for x in files}
 if write:
  auth=baseline_authority(root)
  old=load(root/MANIFEST) if (root/MANIFEST).is_file() else {}
  revision=int(old.get('manifest_revision',0))+1
  atomic_json(root/MANIFEST,{'baseline_version':baseline_version(root),
   'authority':auth['authority'],'authorized_by':auth['authorized_by'],
   'authorized_at':auth['authorized_at'],'frozen_at':now(),
   'manifest_revision':revision,'change_list':auth['change_list'],
   'technical_status':'FROZEN_ARTIFACT','business_status':'BLOCKED_BY_REAL_P0',
   'independent_qa':'PENDING','files':current});return []
 old=load(root/MANIFEST)
 if old.get('baseline_version')!=baseline_version(root):return ['wrong baseline version']
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
