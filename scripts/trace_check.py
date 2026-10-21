#!/usr/bin/env python3
"""Validate exact contract/loop sets, packaged upstream hashes and generated mirrors."""
from pathlib import Path
from contract_registry import validate_registry
from contract_runtime import load,filehash,ContractViolation
from baseline_support import ROOT
from sync_rules import run as rules_check

def errors(root):
 cs,out=validate_registry(root)
 trace=load(root/'docs/baseline/TRACE.yaml')
 records=trace.get('contracts',[])
 if len(records)!=len(cs) or {x['id'] for x in records}!={x.id for x in cs}:out.append('trace contract set mismatch')
 byid={x['id']:x for x in records}
 for c in cs:
  if byid.get(c.id,{}).get('path')!='contracts/'+c.path or not byid.get(c.id,{}).get('decision_id'):out.append('contract trace missing: '+c.id)
 plan=load(root/'docs/PROJECT-PLAN.yaml')['loops']
 actual={p.parent.name for p in (root/'loops').glob('*/LOOP.yaml') if p.parent.name!='_template'}
 if set(plan)!=actual:out.append('planned/actual loop set mismatch')
 for name,p in plan.items():
  loop=load(root/'loops'/name/'LOOP.yaml')
  if loop.get('kind')!=p['kind'] or set(loop.get('required_blockers',[]))!=set(p['required_blockers']):out.append('loop/plan dependency drift: '+name)
 sources=load(root/'docs/baseline/UPSTREAM-SOURCES.yaml')['sources']
 for src in sources:
  file=root/src['path']
  if not file.is_file() or filehash(file)!=src['sha256']:out.append('upstream source hash mismatch: '+src['path'])
 case=load(root/'docs/acceptance/CASE-REGISTRY.yaml')['profiles']
 fixed=load(root/'docs/policies/ACCEPTANCE-BASELINE.yaml')['profiles']
 if set(case)!=set(fixed):out.append('acceptance profile set drift')
 for name,policy in fixed.items():
  actual=case.get(name,{}).get('cases',[])
  if len(actual)!=len(policy['required_cases']) or {x['id']:x['expected'] for x in actual}!=policy['required_cases']:out.append('acceptance obligations drift: '+name)
 out+=rules_check(root)
 return out

def main():
 try:out=errors(ROOT)
 except Exception as e:out=[str(e)]
 for e in out:print('FAIL:',e)
 print('trace-check:', 'FAIL' if out else 'PASS');return int(bool(out))
if __name__=='__main__':raise SystemExit(main())
