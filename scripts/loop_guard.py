#!/usr/bin/env python3
"""Loop v2: state/argv/DAG/baton/budget enforcement; external QA attestation."""
from __future__ import annotations
import argparse,json,os,re,subprocess,sys
from pathlib import Path
from contract_runtime import load,inside,digest,filehash,ContractViolation
from baseline_support import ROOT,now,atomic_json,exclusive,snapshot,baseline_hash,verify_envelope
from p0_closure_check import check as p0_errors
VALID_STATES={'DRAFT','READY','IN_DEV','BLOCKED','QA_PENDING','DONE'}


def ldir(root,loop_id):
 if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',loop_id):raise ContractViolation('invalid loop ID')
 return inside(root,'loops/'+loop_id)
def read_state(d):
 state=load(d/'STATE.json')
 if state.get('status') not in VALID_STATES:raise ContractViolation('invalid state')
 return state

def spec(root,loop_id):
 d=ldir(root,loop_id);loop=load(d/'LOOP.yaml');catalog=load(Path(root)/'docs/policies/GATE-CATALOG.yaml')['gates']
 if loop.get('schema_version')!=2 or loop.get('loop_id')!=loop_id:raise ContractViolation('Loop v2 schema/ID mismatch')
 if loop.get('kind') not in ['contract','diagnostic','implementation']:raise ContractViolation('unknown batch kind')
 if not loop.get('objective') or not loop.get('implementation_principals'):raise ContractViolation('objective and implementation principals required')
 gates=loop.get('gates',[])
 if not gates or len({g['id'] for g in gates})!=len(gates):raise ContractViolation('missing/duplicate gates')
 ids={g['id'] for g in gates}
 for g in gates:
  if 'command' in g:raise ContractViolation('shell command field removed; use approved argv')
  argv=g.get('argv');known=catalog.get(g.get('catalog_id'))
  if not known or argv!=known.get('argv') or g.get('type')!=known.get('type') or loop['kind'] not in known.get('allowed_kinds',[]):raise ContractViolation('gate differs from approved command catalog')
  if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x for x in argv):raise ContractViolation('argv must contain real arguments')
  if any(re.search(r'\|\||&&|[;|`<>]|\$\(',x) for x in argv):raise ContractViolation('shell composition/failure masking is forbidden')
  if g.get('required_checks')!=known.get('required_checks'):raise ContractViolation('gate check-set mismatch')
  if not set(g.get('depends_on',[]))<=ids or g['id'] in g.get('depends_on',[]):raise ContractViolation('invalid gate dependencies')
  if g['type'] not in ['dev_self_check','qa_gate']:raise ContractViolation('invalid gate type')
  if not 1<=g.get('timeout_seconds',600)<=1800:raise ContractViolation('invalid timeout')
 def ancestors(gid,path=None):
  path=path or set()
  if gid in path:raise ContractViolation('gate dependency cycle')
  node=next(x for x in gates if x['id']==gid);out=set(node.get('depends_on',[]))
  for dep in list(out):out|=ancestors(dep,path|{gid})
  return out
 for gid in ids:ancestors(gid)
 limit=loop.get('repair_policy',{}).get('max_iterations_per_gate')
 if not isinstance(limit,int) or not 1<=limit<=5:raise ContractViolation('repair budget must be 1..5')
 if loop['kind']=='implementation':
  plan=load(Path(root)/'docs/PROJECT-PLAN.yaml')['loops'].get(loop_id)
  if not plan or set(loop.get('required_blockers',[]))!=set(plan['required_blockers']):raise ContractViolation('implementation dependency baseline mismatch')
  if 'p0_strict_gate' not in ids:raise ContractViolation('implementation batch requires p0_strict_gate')
  for g in gates:
   if g['id']!='p0_strict_gate' and 'p0_strict_gate' not in ancestors(g['id']):raise ContractViolation('implementation gate bypasses P0 prerequisite')
 return d,loop,gates

def gate_digest(root,g):
 catalog=load(Path(root)/'docs/policies/GATE-CATALOG.yaml')['gates'][g['catalog_id']]
 return digest({'gate':g,'catalog':catalog})
def manifest(d):
 p=d/'evidence/manifest.json'
 if not p.exists():return {'manifest_version':2,'gates':{}}
 value=load(p)
 if value.get('manifest_version')!=2 or not isinstance(value.get('gates'),dict):raise ContractViolation('old/corrupted evidence manifest is STALE')
 return value

def update_views(d,state):
 # These are views, never alternative authority. A killed renderer can be rerun safely.
 mem=d/'memory';mem.mkdir(exist_ok=True)
 board={'view_only':True,'state_revision':state['revision'],'baton':{'holder':state['baton_holder']},'status':state['status']}
 import yaml
 (mem/'ROLE_BOARD.yaml').write_text(yaml.safe_dump(board,allow_unicode=True,sort_keys=False))
 for name in ['NEXT_SESSION.md','ORCHESTRATOR.md']:
  (mem/name).write_text(f'# Generated view\n\nState revision: {state["revision"]}\n\nBaton holder: `{state["baton_holder"]}`\n\nStatus: {state["status"]}\n\nAuthoritative file: ../STATE.json\n')

def save_state(d,state):
 state['revision']=state.get('revision',0)+1;state['updated_at']=now();atomic_json(d/'STATE.json',state);update_views(d,state)

def failure(d,gate_id,reason):
 p=d/'FAILURES.md';p.parent.mkdir(exist_ok=True,parents=True)
 with p.open('a') as f:f.write(f'\n### {now()} {gate_id}\n\n{reason}\n')
 with (d/'evidence/events.jsonl').open('a') as f:f.write(json.dumps({'at':now(),'gate':gate_id,'event':'failure','reason':reason},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())

def evidence_errors(root,loop_id,require_done=False):
 d,loop,gates=spec(root,loop_id);state=read_state(d);m=manifest(d);errors=[];byid={g['id']:g for g in gates}
 from freeze_baseline import run as frozen_errors
 errors+=frozen_errors(Path(root))
 if state.get('loop_id')!=loop_id:errors.append('state loop ID mismatch')
 current=snapshot(root);bh=baseline_hash(root)
 for gid,rec in m['gates'].items():
  if gid not in byid:errors.append(gid+': undeclared gate evidence');continue
  if rec.get('status')!='pass':continue
  g=byid[gid]
  if rec.get('type')!=g['type'] or rec.get('gate_spec_sha256')!=gate_digest(root,g):errors.append(gid+': gate definition changed')
  if rec.get('source_sha256')!=current or rec.get('baseline_sha256')!=bh:errors.append(gid+': source/baseline changed; evidence STALE')
  try:
   p=inside(root,rec.get('evidence',''))
   if not p.is_file():raise ContractViolation('MISSING evidence')
   if not p.stat().st_size:raise ContractViolation('EMPTY evidence')
   if filehash(p)!=rec.get('sha256'):raise ContractViolation('evidence hash mismatch')
   if g['type']=='qa_gate':
    envelope=rec.get('attestation')
    if not envelope:raise ContractViolation('independent QA signature required')
    verify_qa(root,loop,g,rec,envelope)
  except Exception as e:errors.append(gid+': '+str(e))
 if state['status']=='DONE' or require_done:
  if loop['kind']=='implementation':errors+=p0_errors(root,'strict',loop['required_blockers'])
  for g in gates:
   if m['gates'].get(g['id'],{}).get('status')!='pass':errors.append(g['id']+': DONE requires all gates pass')
 return errors

def memory_check(root,loop_id):
 d,loop,gates=spec(root,loop_id);state=read_state(d)
 if state.get('status')=='DRAFT':raise ContractViolation('DRAFT batch not armed')
 if state.get('loop_id')!=loop_id or not state.get('baton_holder'):raise ContractViolation('missing state identity/baton')
 for rel in ['EVIDENCE.md','FAILURES.md','HANDOFF.md','SHARED_MEMORY.md']:
  if not(d/rel).is_file():raise ContractViolation('missing '+rel)
 for rel in ['memory/ROLE_BOARD.yaml','memory/NEXT_SESSION.md','memory/ORCHESTRATOR.md']:
  if not(d/rel).is_file():raise ContractViolation('missing derived view '+rel)
 board=load(d/'memory/ROLE_BOARD.yaml')
 if board.get('state_revision')!=state['revision'] or board.get('baton',{}).get('holder')!=state['baton_holder']:raise ContractViolation('baton view drift; regenerate views from STATE')
 for rel in ['memory/NEXT_SESSION.md','memory/ORCHESTRATOR.md']:
  if f'`{state["baton_holder"]}`' not in (d/rel).read_text() or f'State revision: {state["revision"]}' not in (d/rel).read_text():raise ContractViolation('session/orchestrator view drift')
 return True

def prerequisites(root,loop,state,g,m,executor):
 if state['status'] not in ['READY','IN_DEV','QA_PENDING'] or state.get('blocked'):raise ContractViolation('batch BLOCKED/DRAFT/DONE; gate execution prohibited')
 if executor!=state.get('baton_holder'):raise ContractViolation('executor does not hold baton')
 if loop['kind']=='implementation':
  errors=p0_errors(root,'strict',loop['required_blockers'])
  if errors:raise ContractViolation('business prerequisites not closed: '+'; '.join(errors))
 for dep in g.get('depends_on',[]):
  if m['gates'].get(dep,{}).get('status')!='pass':raise ContractViolation('gate prerequisite not passed: '+dep)
 if state.get('attempts',{}).get(g['id'],0)>=loop['repair_policy']['max_iterations_per_gate']:raise ContractViolation('repair budget exhausted')


def run_gate(root,loop_id,gate_id,executor,role,qa_candidate=False):
 d=ldir(root,loop_id);(d/'evidence').mkdir(exist_ok=True)
 with exclusive(d/'evidence/.runner.lock'):
  try:
   d,loop,gates=spec(root,loop_id);state=read_state(d);m=manifest(d)
   g=next((x for x in gates if x['id']==gate_id),None)
   if not g:raise ContractViolation('unknown gate')
   memory_check(root,loop_id)
   from freeze_baseline import run as frozen_errors
   frozen=frozen_errors(Path(root))
   if frozen:raise ContractViolation('; '.join(frozen))
   if g['type']=='qa_gate' and not qa_candidate:raise ContractViolation('QA cannot self-sign via --role qa; use qa-run and external signed attestation')
   if qa_candidate and g['type']!='qa_gate':raise ContractViolation('qa-run requires a QA gate')
   prerequisites(root,loop,state,g,m,executor)
   stale=evidence_errors(root,loop_id)
   if stale:raise ContractViolation('prior evidence invalid: '+'; '.join(stale))
   before=snapshot(root);bh=baseline_hash(root)
   state.setdefault('attempts',{})[gate_id]=state.get('attempts',{}).get(gate_id,0)+1
   save_state(d,state) # durable reservation; process death consumes an attempt
   argv=list(g['argv'])
   if argv[0]=='python3':argv[0]=sys.executable
   try:
    p=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=g.get('timeout_seconds',600),shell=False)
    code=p.returncode;output=p.stdout+p.stderr
   except subprocess.TimeoutExpired:code=124;output='gate timeout\n'
   after=snapshot(root)
   if after!=before:code=125;output+='\nsource changed during gate; result invalid\n'
   rel=f'loops/{loop_id}/evidence/{gate_id}.log';log=inside(root,rel)
   log.write_text(json.dumps({'argv':g['argv'],'exit_code':code,'executor':executor,'at':now()},ensure_ascii=False)+'\n'+output)
   record={'status':'fail' if code else('QA_PENDING' if qa_candidate else 'pass'),'type':g['type'],'executor':executor,'role':'LOCAL_QA_CANDIDATE' if qa_candidate else 'DEV_SELF_CHECK','evidence':rel,'sha256':filehash(log),'source_sha256':before,'baseline_sha256':bh,'gate_spec_sha256':gate_digest(root,g),'ran_at':now(),'exit_code':code,'executed_checks':g['required_checks']}
   if code:failure(d,gate_id,f'command exited {code}; evidence {rel}')
   m['gates'][gate_id]=record;atomic_json(d/'evidence/manifest.json',m)
   if not code and qa_candidate:state['status']='QA_PENDING';save_state(d,state)
   print(('FAIL' if code else record['status'])+': '+gate_id)
   return 1 if code else 0
  except Exception as e:
   failure(d,gate_id,str(e))
   # Do not preserve a prior pass after a rejected re-execution.
   try:
    m=manifest(d);m['gates'][gate_id]={'status':'blocked','reason':str(e),'ran_at':now()};atomic_json(d/'evidence/manifest.json',m)
   except Exception:pass
   print('FAIL:',e);return 1


def qa_subject(loop_id,g,rec):
 return {'loop_id':loop_id,'gate_id':g['id'],'gate_spec_sha256':rec['gate_spec_sha256'],'source_sha256':rec['source_sha256'],'baseline_sha256':rec['baseline_sha256'],'log_sha256':rec['sha256'],'result':'PASS','executed_checks':rec['executed_checks']}
def verify_qa(root,loop,g,rec,envelope):
 subject=qa_subject(loop['loop_id'],g,rec);payload=envelope.get('payload',{})
 if any(payload.get(k)!=v for k,v in subject.items()):raise ContractViolation('QA attestation subject differs from executed evidence')
 if subject['executed_checks']!=g['required_checks']:raise ContractViolation('QA expected check-set differs')
 principal=verify_envelope(root,envelope,purpose='QA_ATTESTATION',subject_sha256=digest(subject),required_role='qa-owner')
 if principal['principal_id'] in loop['implementation_principals']:raise ContractViolation('independent QA principal participated in implementation')
 return principal

def accept_qa(root,loop_id,gate_id,envelope_path):
 d,loop,gates=spec(root,loop_id)
 with exclusive(d/'evidence/.runner.lock'):
  g=next(x for x in gates if x['id']==gate_id);state=read_state(d);m=manifest(d);rec=m['gates'].get(gate_id,{})
  if g['type']!='qa_gate' or rec.get('status')!='QA_PENDING' or rec.get('exit_code')!=0:raise ContractViolation('no successful current QA candidate run')
  if rec.get('source_sha256')!=snapshot(root) or rec.get('gate_spec_sha256')!=gate_digest(root,g) or rec.get('baseline_sha256')!=baseline_hash(root):raise ContractViolation('QA candidate evidence STALE')
  log=inside(root,rec['evidence'])
  if not log.is_file() or filehash(log)!=rec['sha256']:raise ContractViolation('QA log hash mismatch')
  envelope=load(envelope_path);principal=verify_qa(root,loop,g,rec,envelope)
  rec.update(status='pass',role='VERIFIED_QA',executor=principal['principal_id'],attestation=envelope);atomic_json(d/'evidence/manifest.json',m)
  print('QA accepted for exact signed source/baseline/gate/log; DONE still requires finish')
 return 0

def transfer(root,loop_id,to,executor,expected_revision,arm=False):
 d,loop,gates=spec(root,loop_id)
 with exclusive(d/'evidence/.runner.lock'):
  state=read_state(d)
  if state['revision']!=expected_revision:raise ContractViolation('baton CAS revision conflict')
  if executor not in [state['baton_holder'],loop['tech_lead_principal']]:raise ContractViolation('transfer requires current holder or declared TL')
  if to not in loop['allowed_holders']:raise ContractViolation('unknown target holder')
  if arm:
   if executor!=loop['tech_lead_principal']:raise ContractViolation('only TL may arm')
   if loop['kind']=='implementation':
    errors=p0_errors(root,'strict',loop['required_blockers'])
    if errors:raise ContractViolation('; '.join(errors))
    from readiness_check import reuse_errors
    errors=reuse_errors(root,loop.get('reuse_assets',[]),strict=True,final=False)
    if errors:raise ContractViolation('; '.join(errors))
   state.update(status='IN_DEV',blocked=False)
  state['baton_holder']=to;save_state(d,state)
  print('baton committed in STATE; derived views regenerated')
 return 0

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);subs=p.add_subparsers(dest='sub',required=True)
 for name in ['memory-check','evidence-check','finish','render-views']:
  q=subs.add_parser(name);q.add_argument('--loop',required=True)
 for name in ['run-gate','qa-run']:
  q=subs.add_parser(name);q.add_argument('--loop',required=True);q.add_argument('--gate',required=True);q.add_argument('--executor',required=True);q.add_argument('--role',default='dev')
 q=subs.add_parser('accept-qa');q.add_argument('--loop',required=True);q.add_argument('--gate',required=True);q.add_argument('--attestation',type=Path,required=True)
 for name in ['baton-transfer','arm']:
  q=subs.add_parser(name);q.add_argument('--loop',required=True);q.add_argument('--to',required=True);q.add_argument('--executor',required=True);q.add_argument('--expected-revision',type=int,required=True)
 a=p.parse_args();root=a.root.resolve()
 try:
  if a.sub in ['run-gate','qa-run']:return run_gate(root,a.loop,a.gate,a.executor,a.role,a.sub=='qa-run')
  if a.sub=='accept-qa':return accept_qa(root,a.loop,a.gate,a.attestation)
  if a.sub in ['arm','baton-transfer']:return transfer(root,a.loop,a.to,a.executor,a.expected_revision,a.sub=='arm')
  d=ldir(root,a.loop)
  if a.sub=='render-views':update_views(d,read_state(d));return 0
  if a.sub=='memory-check':memory_check(root,a.loop)
  else:
   errors=evidence_errors(root,a.loop,a.sub=='finish')
   if errors:raise ContractViolation('; '.join(errors))
   if a.sub=='finish':
    with exclusive(d/'evidence/.runner.lock'):
     # Revalidate under lock to avoid committing a stale decision.
     errors=evidence_errors(root,a.loop,True)
     if errors:raise ContractViolation('; '.join(errors))
     state=read_state(d)
     if state['status'] not in ['IN_DEV','QA_PENDING']:raise ContractViolation('cannot finish current state')
     state['status']='DONE';save_state(d,state)
  print(a.sub+': PASS ('+a.loop+')');return 0
 except Exception as e:print('FAIL:',e);return 1
if __name__=='__main__':raise SystemExit(main())
