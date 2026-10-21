#!/usr/bin/env python3
"""Stdlib-only, explicit overlay with complete preimage backup and guarded rollback."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile,uuid
from pathlib import Path
from datetime import datetime,timezone
RECEIPT='.llmke-baseline-applied.json'
class PatchError(RuntimeError):pass

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def safe(root,relative):
 rel=Path(relative)
 if rel.is_absolute() or '..' in rel.parts or not rel.parts:raise PatchError('unsafe relative path')
 root=Path(root).resolve();p=root/rel
 for x in [p,*p.parents]:
  if x==root:break
  if x.is_symlink():raise PatchError('symlink forbidden: '+relative)
 if not p.resolve().is_relative_to(root):raise PatchError('path escapes target')
 return p

def write_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if Path(tmp).exists():Path(tmp).unlink()

def put(source,dest):
 dest.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(dir=dest.parent,prefix='.llmke-copy-')
 try:
  with os.fdopen(fd,'wb') as out,source.open('rb') as incoming:shutil.copyfileobj(incoming,out);out.flush();os.fsync(out.fileno())
  shutil.copymode(source,temp);os.replace(temp,dest)
 finally:
  if Path(temp).exists():Path(temp).unlink()

def plan(bundle,target):
 bundle=Path(bundle).resolve();target=Path(target).resolve()
 if not target.is_dir():raise PatchError('target must be an existing project directory')
 if target==bundle or target.is_relative_to(bundle):raise PatchError('target cannot be the delivery bundle or its child')
 if (bundle/'overlay').is_symlink():raise PatchError('payload root symlink forbidden')
 mp=bundle/'PATCH-MANIFEST.json';manifest=json.loads(mp.read_text());rows=manifest['files'];seen=set();actions=[]
 regenerable=set(manifest.get('regenerable_paths',[]))
 if not regenerable<={'contracts/build/generate-report.json','contracts/build/check-report.json'}:raise PatchError('unknown regenerable cache path')
 for row in rows:
  rel=row['path']
  if rel in seen:raise PatchError('duplicate patch path')
  seen.add(rel);dest=safe(target,rel)
  if dest.exists() and not dest.is_file():raise PatchError('destination is not a regular file: '+rel)
  action=row['action']
  if action not in ['ADD','REPLACE','DELETE']:raise PatchError('unknown action')
  if action!='DELETE':
   src=safe(bundle/'overlay',rel)
   if not src.is_file() or sha(src)!=row['sha256']:raise PatchError('payload hash mismatch: '+rel)
  actions.append({'path':rel,'action':action,'before_sha256':sha(dest) if dest.exists() else None,'after_sha256':None if action=='DELETE' else row['sha256'],'regenerable':rel in regenerable,'base_drift':row.get('base_sha256') is not None and(sha(dest) if dest.exists() else None)!=row['base_sha256']})
 for prefix in manifest.get('reset_prefixes',[]):
  folder=safe(target,prefix)
  if folder.is_dir():
   for f in sorted(folder.rglob('*')):
    if f.is_symlink():raise PatchError('symlink in reset area')
    if f.is_file():
     rel=f.relative_to(target).as_posix()
     if rel not in seen:actions.append({'path':rel,'action':'DELETE','before_sha256':sha(f),'after_sha256':None,'base_drift':False});seen.add(rel)
 # Receipt is also reversible and cannot point outside the target.
 receipt=safe(target,RECEIPT)
 actions.append({'path':RECEIPT,'action':'RECEIPT','before_sha256':sha(receipt) if receipt.exists() else None,'after_sha256':None,'base_drift':False})
 return manifest,actions,sha(mp)

def rollback(target,backup):
 target=Path(target).resolve();backup=Path(backup).resolve();journal=json.loads((backup/'JOURNAL.json').read_text())
 if target!=Path(journal['target']).resolve():raise PatchError('rollback target does not match original target')
 # Validate every preimage and current file before any restore, so later user edits are not lost.
 for row in journal['actions']:
  dest=safe(target,row['path']);current=sha(dest) if dest.is_file() else None
  if dest.exists() and not dest.is_file():raise PatchError('rollback destination changed type')
  if current not in [row['before_sha256'],row.get('after_sha256')] and not row.get('regenerable'):raise PatchError('rollback conflict; current file has later edits: '+row['path'])
  if row['before_sha256'] is not None:
   saved=safe(backup/'files',row['path'])
   if not saved.is_file() or sha(saved)!=row['before_sha256']:raise PatchError('backup hash mismatch: '+row['path'])
 for row in journal['actions']:
  dest=safe(target,row['path'])
  if row.get('regenerable') and dest.is_file() and sha(dest) not in [row['before_sha256'],row.get('after_sha256')]:
   saved=safe(backup/'regenerated-before-rollback',row['path']);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
 for row in reversed(journal['actions']):
  dest=safe(target,row['path'])
  if row['before_sha256'] is None:
   if dest.is_file():dest.unlink()
  else:put(safe(backup/'files',row['path']),dest)
 journal['state']='ROLLED_BACK';write_json(backup/'JOURNAL.json',journal)
 print('ROLLBACK_OK',str(backup));return backup

def apply(bundle,target,commit=False):
 bundle=Path(bundle).resolve();target=Path(target).resolve();manifest,actions,mh=plan(bundle,target)
 receipt=target/RECEIPT
 if receipt.is_file():
  current=json.loads(receipt.read_text())
  if current.get('patch_id')==manifest['patch_id']:
   if current.get('patch_manifest_sha256')!=mh:raise PatchError('same patch ID has different bytes')
   print('ALREADY_APPLIED; runtime state and later business work preserved');return None
 print(json.dumps({'patch_id':manifest['patch_id'],'files':len(actions)-1,'base_drift_backed_up':sum(x['base_drift'] for x in actions),'mode':'APPLY' if commit else 'PLAN'},ensure_ascii=False))
 if not commit:return None
 backup=target.parent/'.llmke-baseline-backups'/(target.name+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
 backup.mkdir(parents=True,exist_ok=False)
 for row in actions:
  if row['before_sha256'] is not None:
   source=safe(target,row['path']);dest=safe(backup/'files',row['path']);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
 data={'patch_id':manifest['patch_id'],'patch_manifest_sha256':mh,'backup':str(backup)}
 receipt_bytes=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
 for row in actions:
  if row['action']=='RECEIPT':row['after_sha256']=hashlib.sha256(receipt_bytes).hexdigest()
 journal={'state':'APPLYING','target':str(target),'patch_id':manifest['patch_id'],'actions':actions}
 write_json(backup/'JOURNAL.json',journal)
 try:
  # Refuse races between preflight and mutation.
  for row in actions:
   dest=safe(target,row['path'])
   if (sha(dest) if dest.is_file() else None)!=row['before_sha256']:raise PatchError('target changed since preflight: '+row['path'])
  for row in actions:
   dest=safe(target,row['path'])
   if row['action']=='DELETE':
    if dest.is_file():dest.unlink()
   elif row['action']=='RECEIPT':
    write_json(dest,data)
   else:put(safe(bundle/'overlay',row['path']),dest)
  for row in actions:
   dest=safe(target,row['path'])
   if (sha(dest) if dest.is_file() else None)!=row['after_sha256']:raise PatchError('post-apply hash mismatch: '+row['path'])
  journal['state']='APPLIED';write_json(backup/'JOURNAL.json',journal)
 except Exception:
  rollback(target,backup);raise
 print('APPLY_OK; backup='+str(backup));return backup

def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--target',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',type=Path);a=p.parse_args()
 try:
  if a.rollback:rollback(a.target,a.rollback)
  else:apply(a.bundle,a.target,a.apply)
  return 0
 except Exception as e:print('FAIL:',e);return 1
if __name__=='__main__':raise SystemExit(main())
