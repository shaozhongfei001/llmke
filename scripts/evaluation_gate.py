#!/usr/bin/env python3
"""Conditional enablement and signed release thresholds are distinct decisions."""
from pathlib import Path
import argparse
from contract_runtime import load,digest,inside,filehash,ContractViolation
from baseline_support import ROOT,verify_envelope

def global_decision(coverage):
 if not 0<=coverage<=1:raise ContractViolation('coverage outside [0,1]')
 return 'EVALUATE_COMMUNITY' if coverage<.5 else 'LIGHTWEIGHT_THEN_REMEASURE' if coverage<.7 else 'DO_NOT_ADD_COMMUNITY'
def graph_decision(baseline,enhanced):
 if not 0<=baseline<=1 or not 0<=enhanced<=1:raise ContractViolation('coverage outside [0,1]')
 return 'ENABLE_GRAPH_AFTER_QUALITY' if enhanced-baseline>=.10-1e-12 else 'DISABLED_BY_DECISION_NOT_PLATFORM_FAILURE'

def release(root):
 register=load(root/'docs/evaluation/RELEASE-REGISTER.yaml')
 if register.get('status')!='SIGNED':raise ContractViolation('M0 dataset/threshold approvals not available')
 body=register;roles=set();approval_times=[]
 subject={'policy_version':body['version'],'dataset_sha256':body['dataset_sha256'],'thresholds':body['thresholds']}
 for envelope in register.get('approvals',[]):
  roles.update(verify_envelope(root,envelope,purpose='EVALUATION_POLICY_APPROVAL',subject_sha256=digest(subject))['roles']);approval_times.append(envelope['payload']['issued_at'])
 if not {'product-owner','algorithm-owner'}<=roles:raise ContractViolation('product+algorithm approval required before measurement')
 dataset=inside(root,body['dataset_ref']);report=inside(root,body['report_ref'])
 if filehash(dataset)!=body['dataset_sha256'] or filehash(report)!=body['report_sha256']:raise ContractViolation('dataset/report changed')
 d=load(dataset);r=load(report)
 from datetime import datetime
 dt=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
 if any(dt(x)>dt(r['measurement_started_at']) for x in approval_times):raise ContractViolation('thresholds were approved after measurement')
 if r.get('dataset_sha256')!=body['dataset_sha256'] or r.get('policy_sha256')!=digest(subject):raise ContractViolation('measurement dataset/policy binding mismatch')
 verify_envelope(root,body['result_attestation'],purpose='EVALUATION_RESULT',subject_sha256=digest(r),required_role='qa-owner')
 if len(d['questions'])!=100 or len({x['id'] for x in d['questions']})!=100:raise ContractViolation('M0 requires 100 unique questions')
 from collections import Counter
 expected=load(root/'contracts/evaluation/llmke-m0-gates.yaml')['evaluation']['dataset']['quota']
 if dict(Counter(x['type'] for x in d['questions']))!=expected:raise ContractViolation('question quota mismatch')
 t=body['thresholds'];m=r['metrics']
 for name in ['answer_accuracy_min','citation_completeness_min','coverage_min','correct_refusal_min']:
  if not isinstance(t.get(name),(int,float)) or not 0<=t[name]<=1:raise ContractViolation('missing approved threshold '+name)
  if m[name.removesuffix('_min')]<t[name]:raise ContractViolation('quality below threshold '+name)
 if m['veto_rate']>.05 or m['support_ratio']<.95 or m['route_instrumentation_completeness']!=1:raise ContractViolation('M0 hard quality gate failed')
 if m['coverage']<m['matched_budget_baseline_coverage'] or not r.get('metric_selftests_passed') or not r.get('independent_support_audit_ref'):raise ContractViolation('baseline regression or absent metric/audit evidence')
 return True

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args()
 try:release(a.root);print('evaluation-release: PASS');return 0
 except Exception as e:print('FAIL:',e);return 1
if __name__=='__main__':raise SystemExit(main())
