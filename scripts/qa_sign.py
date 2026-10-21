#!/usr/bin/env python3
"""Use on the external QA/approval runner; no private keys in the implementation workspace."""
from pathlib import Path
import argparse,base64,json,subprocess,tempfile
from contract_runtime import canonical,load,ContractViolation
from baseline_support import ROOT,atomic_json

def main():
 p=argparse.ArgumentParser();p.add_argument('--key-file',type=Path,required=True);p.add_argument('--key-id',required=True);p.add_argument('--payload',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.key_file.resolve().is_relative_to(ROOT):raise ContractViolation('private key must remain outside implementation workspace')
 payload=load(a.payload)
 with tempfile.TemporaryDirectory() as d:
  f=Path(d)/'payload';f.write_bytes(canonical(payload));sig=Path(d)/'signature'
  subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(a.key_file),'-rawin','-in',str(f),'-out',str(sig)],check=True,capture_output=True)
  envelope={'key_id':a.key_id,'payload':payload,'signature':base64.b64encode(sig.read_bytes()).decode()}
 atomic_json(a.out,envelope);print('signed approval written; verify in protected runner before acceptance')
if __name__=='__main__':
 try:main()
 except Exception as e:raise SystemExit('FAIL: '+str(e))
