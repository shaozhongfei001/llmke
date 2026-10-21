#!/usr/bin/env python3
"""Export an unsigned, exact QA subject for a separate protected signer."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse
from baseline_support import ROOT,atomic_json,snapshot,baseline_hash
from contract_runtime import digest,load,filehash,inside,ContractViolation
from loop_guard import spec,manifest,qa_subject,gate_digest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--loop',required=True);p.add_argument('--gate',required=True);p.add_argument('--principal-id',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:
  d,loop,gates=spec(ROOT,a.loop);g=next(x for x in gates if x['id']==a.gate);rec=manifest(d)['gates'][a.gate]
  if g['type']!='qa_gate' or rec.get('status')!='QA_PENDING' or rec.get('exit_code')!=0:raise ContractViolation('successful QA candidate run required')
  if rec['source_sha256']!=snapshot(ROOT) or rec['baseline_sha256']!=baseline_hash(ROOT) or rec['gate_spec_sha256']!=gate_digest(ROOT,g) or rec['sha256']!=filehash(inside(ROOT,rec['evidence'])):raise ContractViolation('candidate evidence changed')
  subject=qa_subject(a.loop,g,rec);now=datetime.now(timezone.utc)
  payload={**subject,'purpose':'QA_ATTESTATION','principal_id':a.principal_id,'issued_at':now.isoformat(),'expires_at':(now+timedelta(hours=1)).isoformat(),'subject_sha256':digest(subject)}
  atomic_json(a.out,payload);print('UNSIGNED_QA_PAYLOAD; no QA approval granted')
 except Exception as e:raise SystemExit('FAIL: '+str(e))
