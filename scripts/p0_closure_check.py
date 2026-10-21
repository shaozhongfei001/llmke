#!/usr/bin/env python3
"""An honest register is not closure. Only verified CLOSED items pass strict."""
from pathlib import Path
import argparse,sys
from contract_runtime import load,inside,filehash,digest,ContractViolation
from baseline_support import ROOT,snapshot,verify_envelope

def check(root,mode='integrity',required=None,register=None):
 root=Path(root);policy=load(root/'docs/policies/P0-POLICY.yaml');doc=load(register or root/'docs/registers/P0-CLOSURE.yaml')
 items=doc.get('items',[]);byid={x.get('id'):x for x in items}
 expected=policy['required_items'];errors=[]
 if len(items)!=len(byid) or set(byid)!=set(expected):errors.append('P0_BASELINE_SET_MISMATCH: required IDs cannot be deleted or duplicated')
 required=list(expected) if required is None else required
 if not set(required)<=set(expected):errors.append('unknown required blocker')
 if mode=='strict' and not required:errors.append('strict requires a nonempty approved blocker set')
 for pid,rule in expected.items():
  item=byid.get(pid)
  if not item:continue
  if item.get('owner')!=rule['owner'] or set(item.get('blocks',[]))!=set(rule['blocks']):errors.append(pid+': owner/impact differs from approved baseline')
  decisions=item.get('decision_required',[])
  if not decisions or not item.get('evidence_expectation'):errors.append(pid+': missing decisions/evidence expectations')
  if item.get('status') not in ['OPEN','CLOSED','ACCEPTED_RISK']:errors.append(pid+': invalid status')
  if item.get('status')=='ACCEPTED_RISK' and not item.get('waiver_ref'):errors.append(pid+': accepted risk requires separate waiver; it never closes the blocker')
  if item.get('status')=='CLOSED':
   try:
    refs=item.get('evidence',[])
    if not refs:raise ContractViolation('CLOSED requires closure dossier')
    for rel in refs:
     p=inside(root,rel)
     if not p.is_file() or not p.stat().st_size:raise ContractViolation('missing/EMPTY closure dossier')
    closure=load(inside(root,refs[0]));body={k:v for k,v in closure.items() if k!='approvals'}
    if body.get('blocker_id')!=pid or body.get('status')!='CLOSED' or body.get('source_snapshot_sha256')!=snapshot(root):raise ContractViolation('closure baseline/source snapshot mismatch')
    expected_answers={f'D{i+1:02}' for i in range(len(decisions))}
    answers=body.get('answers',{})
    if set(answers)!=expected_answers:raise ContractViolation('not all decision items answered')
    for answer in answers.values():
     if not answer.get('conclusion') or not answer.get('evidence'):raise ContractViolation('decision answer lacks conclusion/evidence')
     for evidence in answer['evidence']:
      p=inside(root,evidence['path'])
      if not p.is_file() or not p.stat().st_size or filehash(p)!=evidence['sha256']:raise ContractViolation('closure evidence missing/empty/hash mismatch')
    tests=body.get('verified_tests',[])
    if not tests or any(t.get('result')!='PASS' for t in tests):raise ContractViolation('closure has no verified successful tests')
    approved=set()
    for approval in closure.get('approvals',[]):
     principal=verify_envelope(root,approval,purpose='P0_APPROVAL',subject_sha256=digest(body))
     approved.update(principal.get('roles',[]))
    if not {rule.get('approval_role',rule['owner']),'baseline-owner'}<=approved:raise ContractViolation('closure requires owner and baseline-owner approval')
   except Exception as e:errors.append(pid+': '+str(e))
 if mode=='strict':
  for pid in required:
   if byid.get(pid,{}).get('status')!='CLOSED':errors.append(pid+': strict requires CLOSED; OPEN/ACCEPTED_RISK is not closure')
 return errors

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--mode',choices=['integrity','strict'],default='integrity');p.add_argument('--register',type=Path);p.add_argument('--loop');a=p.parse_args()
 try:
  required=load(a.root/'docs/PROJECT-PLAN.yaml')['loops'][a.loop]['required_blockers'] if a.loop else None
  errors=check(a.root.resolve(),a.mode,required,a.register)
 except Exception as e:errors=[str(e)]
 for e in errors:print('FAIL:',e)
 print(f'p0-check: {"FAIL" if errors else "PASS"} ({a.mode})')
 return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
