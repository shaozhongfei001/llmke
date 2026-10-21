"""Thirteen review roots: each mutation must be rejected for the intended reason."""
import json
from pathlib import Path
from fixture_helpers import make_loop,p0_fixture,guard,devpass,dump,load
from p0_closure_check import check
from conftest import run_script

def test_P01_accepted_risk_never_strict(tmp_path):
 root=p0_fixture(tmp_path);p=root/'docs/registers/P0-CLOSURE.yaml';d=load(p)
 for x in d['items']:x.update(status='ACCEPTED_RISK',waiver_ref='separate-waiver')
 dump(p,d);assert any('strict requires CLOSED' in e for e in check(root,'strict'))

def test_P02_empty_closed_evidence_rejected(tmp_path):
 root=p0_fixture(tmp_path);(root/'empty.json').write_text('');p=root/'docs/registers/P0-CLOSURE.yaml';d=load(p)
 for x in d['items']:x.update(status='CLOSED',evidence=['empty.json'])
 dump(p,d);assert any('EMPTY' in e for e in check(root,'strict'))

def test_P03_deleted_blocker_rejected(tmp_path):
 root=p0_fixture(tmp_path);p=root/'docs/registers/P0-CLOSURE.yaml';d=load(p);d['items']=d['items'][:-1];dump(p,d)
 assert any('BASELINE_SET' in e for e in check(root,'integrity'))

def test_P04_noop_cannot_certify_stale_output(contract_sandbox):
 root=contract_sandbox;assert run_script('contract_generate.py',root).returncode==0
 gen=root/'scripts/generators/openapi_types.py';gen.write_text("print('generation finished')\n")
 d=load(root/'contracts/api/example-openapi.json');d['components']['schemas']['Item']['properties']['new_field']={'type':'integer'};dump(root/'contracts/api/example-openapi.json',d)
 p=run_script('contract_generate.py',root);assert p.returncode!=0 and 'EMPTY_OUTPUT' in p.stdout

def test_P05_empty_output_report_rejected(contract_sandbox):
 root=contract_sandbox;assert run_script('contract_generate.py',root).returncode==0
 p=root/'contracts/build/generate-report.json';d=load(p)
 for e in d['contracts']:e['outputs']={}
 dump(p,d)
 for f in(root/'generated').rglob('*.json'):f.unlink()
 p=run_script('contract_check.py',root);assert p.returncode!=0 and 'LINKAGE' in p.stdout

def test_P06_unresolvable_ref_rejected(contract_sandbox):
 root=contract_sandbox;p=root/'contracts/api/example-openapi.json';d=load(p);d['components']['schemas']['Item']['properties']['id']={'$ref':'#/components/schemas/NoSuchType'};dump(p,d)
 r=run_script('contract_generate.py',root);assert r.returncode!=0 and 'unresolved $ref' in r.stdout

def test_P07_changed_gate_definition_invalidates_old_evidence(tmp_path):
 root,d=make_loop(tmp_path);devpass(root);p=d/'LOOP.yaml';l=load(p);l['gates'][0]['timeout_seconds']=11;dump(p,l)
 r=guard(root,'evidence-check','--loop','T1');assert r.returncode!=0 and 'definition changed' in r.stdout

def test_P08_changed_qa_type_invalidates_dev_evidence(tmp_path):
 root,d=make_loop(tmp_path);devpass(root);p=d/'LOOP.yaml';l=load(p);l['gates'][0]['type']='qa_gate';l['gates'][0]['catalog_id']='fixture.qa';dump(p,l)
 r=guard(root,'evidence-check','--loop','T1');assert r.returncode!=0 and ('definition changed' in r.stdout or 'QA' in r.stdout)

def test_P09_role_qa_does_not_self_sign(tmp_path):
 root,d=make_loop(tmp_path);devpass(root)
 r=guard(root,'run-gate','--loop','T1','--gate','e2e_smoke_gate','--executor','dev-1','--role','qa')
 assert r.returncode!=0 and 'cannot self-sign' in r.stdout
 assert load(d/'evidence/manifest.json')['gates']['e2e_smoke_gate']['status']!='pass'

def test_P10_failure_masking_is_not_executed(tmp_path):
 root,d=make_loop(tmp_path);p=d/'LOOP.yaml';l=load(p);l['gates'][0]['argv']+=['||','true'];dump(p,l)
 p=root/'docs/policies/GATE-CATALOG.yaml';c=load(p);c['gates']['fixture.dev']['argv']=l['gates'][0]['argv'];dump(p,c)
 r=guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','dev-1')
 assert r.returncode!=0 and 'shell composition' in r.stdout and not(root/'.test_counter').exists()

def test_P11_blocked_batch_does_not_execute(tmp_path):
 root,d=make_loop(tmp_path,status='BLOCKED')
 r=guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','dev-1')
 assert r.returncode!=0 and 'BLOCKED' in r.stdout and not(root/'.test_counter').exists()

def test_P12_implementation_requires_p0_gate(tmp_path):
 root,d=make_loop(tmp_path,kind='implementation')
 dump(root/'docs/PROJECT-PLAN.yaml',{'loops':{'T1':{'required_blockers':[]}}})
 r=guard(root,'memory-check','--loop','T1');assert r.returncode!=0 and 'requires p0_strict_gate' in r.stdout

def test_P13_retry_budget_prevents_second_execution(tmp_path):
 root,d=make_loop(tmp_path,limit=1);(root/'.fail').write_text('yes')
 assert guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','dev-1').returncode!=0
 assert(root/'.test_counter').read_text()=='1'
 r=guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','dev-1')
 assert r.returncode!=0 and 'budget exhausted' in r.stdout
 assert(root/'.test_counter').read_text()=='1'
