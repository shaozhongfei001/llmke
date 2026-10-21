"""Isolated engine fixtures; never real business evidence or QA authority."""
from pathlib import Path
import base64,json,shutil,subprocess,sys
from datetime import datetime,timezone,timedelta
import yaml
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'scripts'))
from baseline_support import atomic_json,baseline_hash
from contract_runtime import canonical,digest,load
from loop_guard import update_views

def dump(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,indent=2)+'\n' if path.suffix=='.json' else yaml.safe_dump(value,sort_keys=False))

def make_loop(tmp,kind='contract',status='IN_DEV',limit=3):
 root=Path(tmp)/'project';d=root/'loops/T1';d.mkdir(parents=True)
 (root/'scripts').mkdir();(root/'scripts/probe_gate.py').write_text("from pathlib import Path\np=Path('.test_counter');p.write_text(str(int(p.read_text())+1 if p.exists() else 1))\nprint('isolated engine fixture, no business assertion')\nraise SystemExit(7 if Path('.fail').exists() else 0)\n")
 catalog={}
 for name,typ in [('fixture.dev','dev_self_check'),('fixture.qa','qa_gate')]:catalog[name]={'argv':['python3','scripts/probe_gate.py'],'type':typ,'required_checks':['isolated_engine_fixture'],'allowed_kinds':['contract','implementation','diagnostic']}
 dump(root/'docs/policies/GATE-CATALOG.yaml',{'gates':catalog})
 gates=[{'id':'repo_structure_gate','catalog_id':'fixture.dev','type':'dev_self_check','argv':catalog['fixture.dev']['argv'],'required_checks':['isolated_engine_fixture'],'depends_on':[],'timeout_seconds':10},{'id':'e2e_smoke_gate','catalog_id':'fixture.qa','type':'qa_gate','argv':catalog['fixture.qa']['argv'],'required_checks':['isolated_engine_fixture'],'depends_on':['repo_structure_gate'],'timeout_seconds':10}]
 loop={'schema_version':2,'loop_id':'T1','kind':kind,'objective':['isolated controller regression'],'implementation_principals':['dev-1'],'tech_lead_principal':'tech-lead','allowed_holders':['dev-1','worker-1','worker-2','qa-independent','tech-lead'],'required_blockers':[],'reuse_assets':[],'gates':gates,'repair_policy':{'max_iterations_per_gate':limit}}
 dump(d/'LOOP.yaml',loop)
 state={'schema_version':2,'loop_id':'T1','revision':1,'status':status,'blocked':status in ['DRAFT','BLOCKED'],'baton_holder':'dev-1','attempts':{}}
 atomic_json(d/'STATE.json',state)
 for rel in ['EVIDENCE.md','FAILURES.md','HANDOFF.md','SHARED_MEMORY.md']:(d/rel).write_text('# Isolated fixture\n')
 dump(d/'evidence/manifest.json',{'manifest_version':2,'gates':{}});update_views(d,state)
 from freeze_baseline import run as freeze
 freeze(root,write=True)
 return root,d

def guard(root,*args):
 return subprocess.run([sys.executable,str(PROJECT/'scripts/loop_guard.py'),'--root',str(root),*args],cwd=root,text=True,capture_output=True,timeout=25)
def devpass(root):
 p=guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','dev-1')
 assert p.returncode==0,p.stdout+p.stderr
 return load(root/'loops/T1/evidence/manifest.json')['gates']['repo_structure_gate']

def p0_fixture(tmp):
 root=Path(tmp)/'project';(root/'docs/policies').mkdir(parents=True,exist_ok=True)
 for rel in ['docs/policies/P0-POLICY.yaml','docs/registers/P0-CLOSURE.yaml']:
  p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/rel,p)
 return root

def authority(tmp,root,monkeypatch,roles=None,principal='qa-independent'):
 outside=Path(tmp)/'external-trust';outside.mkdir(exist_ok=True)
 key=outside/'private.pem';pub=outside/'public.pem'
 subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(key)],check=True,capture_output=True)
 subprocess.run(['openssl','pkey','-in',str(key),'-pubout','-out',str(pub)],check=True,capture_output=True)
 trust=outside/'trust.json';dump(trust,{'environment':'PROTECTED_RUNNER','approved_baseline_sha256':baseline_hash(root),'principals':{'fixture-key':{'enabled':True,'principal_id':principal,'roles':roles or ['qa-owner'],'public_key_pem':pub.read_text()}}})
 monkeypatch.setenv('LLMKE_TRUST_ROOT',str(trust))
 return key,'fixture-key',principal

def sign(tmp,key,keyid,principal,purpose,subject):
 stamp=datetime.now(timezone.utc)
 payload={'purpose':purpose,'principal_id':principal,'issued_at':stamp.isoformat(),'expires_at':(stamp+timedelta(minutes=5)).isoformat(),'subject_sha256':digest(subject)}
 if purpose=='QA_ATTESTATION':payload.update(subject)
 body=Path(tmp)/'sign-body';sig=Path(tmp)/'sign-sig';body.write_bytes(canonical(payload))
 subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(key),'-rawin','-in',str(body),'-out',str(sig)],check=True,capture_output=True)
 return {'key_id':keyid,'payload':payload,'signature':base64.b64encode(sig.read_bytes()).decode()}
