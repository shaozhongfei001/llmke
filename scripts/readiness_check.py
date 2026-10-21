#!/usr/bin/env python3
"""Inventory, approved reuse plan, and completed reuse proof are separate gates."""
from pathlib import Path
import argparse,re
from contract_runtime import load,inside,filehash,digest,ContractViolation
from baseline_support import ROOT,verify_envelope

def proof(root,ref):
 if not isinstance(ref,dict) or not ref.get('path') or not ref.get('sha256'):raise ContractViolation('evidence requires path and sha256')
 p=inside(root,ref['path'])
 if not p.is_file() or not p.stat().st_size or filehash(p)!=ref['sha256']:raise ContractViolation('evidence missing/empty/hash mismatch')
 return ref

def decision_subject(root,item,baseline):
 table='legacy_table' in item
 keys=['id','decision_owner_role','approved_decision_ref']
 keys+=['legacy_table','actual_ddl_sha256','target_table_decision','field_semantics_map_ref','migration_script_ref','new_old_write_owners_ref'] if table else ['legacy_path','decision','decision_reason','proposed_target_boundary','contract_ids_and_hashes','characterization_case_ids','migration_case_ids']
 subject={'baseline':baseline,'plan':{k:item.get(k) for k in keys if k!='approved_decision_ref'},'plan_files':{}}
 refs=['actual_ddl_ref','actual_indexes_constraints_triggers_ref','field_semantics_map_ref','migration_script_ref','new_old_write_owners_ref'] if table else ['legacy_build_evidence']
 for field in refs:
  rel=item.get(field)
  if not isinstance(rel,str) or not rel:raise ContractViolation('missing plan input '+field)
  p=inside(root,rel)
  if not p.is_file() or not p.stat().st_size:raise ContractViolation('plan input missing/empty '+field)
  subject['plan_files'][rel]=filehash(p)
  if field=='actual_ddl_ref' and filehash(p)!=item.get('actual_ddl_sha256'):raise ContractViolation('actual per-table DDL hash mismatch')
 return subject

def reuse_errors(root,assets=None,strict=False,final=True):
 root=Path(root);code=load(root/'docs/reuse/SOURCE-ASSETS.yaml');db=load(root/'docs/reuse/DATABASE-ASSETS.yaml');routes=load(root/'docs/reuse/INTERFACE-ASSETS.yaml')
 errors=[];items=code['items']+db['items'];byid={x['id']:x for x in items}
 if len(code['items'])!=12 or len(db['items'])!=37 or sum(x['model_field_count'] for x in db['items'])!=482 or len(byid)!=49:errors.append('legacy inventory must contain 12 code assets, 37 tables / 482 model fields')
 rows=routes['items']
 if len(rows)!=506 or sum(x['stack']=='Java' for x in rows)!=440 or sum(x['stack']=='Python' for x in rows)!=66:errors.append('route inventory count mismatch; inventory is not runtime proof')
 if not strict:return errors
 selected=set(byid if assets is None else assets)
 if not selected:errors.append('strict reuse requires a nonempty approved asset set')
 if not selected<=byid.keys():errors.append('unknown reuse asset IDs')
 role_ids=set(load(root/'docs/roles/ROLE-MATRIX.yaml')['roles'])
 for doc,name in [(code,'source'),(db,'database')]:
  if not any(('legacy_table' in byid[x])==(name=='database') for x in selected&byid.keys()):continue
  try:
   b=doc['baseline'];digest_field='released_artifact_sha256' if name=='source' else 'ddl_snapshot_sha256';ref_field='released_artifact_ref' if name=='source' else 'ddl_snapshot_ref'
   proof(root,{'path':b.get(ref_field),'sha256':b.get(digest_field)})
   if name=='source' and not re.fullmatch('[0-9a-f]{40}',str(b.get('released_commit',''))):raise ContractViolation('released commit missing')
   if name=='database' and(not b.get('actual_db_engine_version') or b.get('source_schema_strategy') not in ['shared_db_expand_contract','new_db_migrate_cutover']):raise ContractViolation('database engine/strategy not decided')
  except Exception as e:errors.append(name+': '+str(e))
 for aid in selected&byid.keys():
  item=byid[aid];table='legacy_table' in item
  try:
   if item.get('status') not in ['APPROVED','VERIFIED']:raise ContractViolation('reuse decision not approved')
   owner=item.get('decision_owner_role')
   if owner not in role_ids:raise ContractViolation('actual decision owner role not assigned')
   if table:
    if item.get('target_table_decision') not in ['KEEP','ADAPT','REWRITE','RETIRE']:raise ContractViolation('table decision missing')
   elif item.get('decision') not in ['KEEP','ADAPT','REWRITE','RETIRE'] or not item.get('decision_reason') or not item.get('characterization_case_ids'):raise ContractViolation('source decision/characterization plan incomplete')
   subject=decision_subject(root,item,db['baseline'] if table else code['baseline'])
   envelope=load(inside(root,item['approved_decision_ref']))
   verify_envelope(root,envelope,purpose='REUSE_DECISION',subject_sha256=digest(subject),required_role=owner)
   if final:
    evidence=item.get('new_old_compatibility_evidence',[])+item.get('rollback_evidence',[]) if table else item.get('closure_evidence',[])
    if not evidence or(table and(not item.get('new_old_compatibility_evidence') or not item.get('rollback_evidence'))):raise ContractViolation('completed compatibility/rollback/characterization proof missing')
    for ref in evidence:proof(root,ref)
  except Exception as e:errors.append(aid+': '+str(e))
 return errors

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--mode',choices=['inventory','approved','strict'],default='inventory');p.add_argument('--loop');a=p.parse_args()
 try:
  plan=load(a.root/'loops'/a.loop/'LOOP.yaml') if a.loop else {}
  errors=reuse_errors(a.root,plan.get('reuse_assets'),a.mode!='inventory',a.mode=='strict')
 except Exception as e:errors=[str(e)]
 for e in errors:print('FAIL:',e)
 print('reuse-check:', 'FAIL' if errors else 'PASS',a.mode,'(inventory is not approval; plan approval is not completed migration)')
 return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
