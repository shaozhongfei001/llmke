"""Legal closure must be possible; invented paths/statuses must never be sufficient."""
import copy
import pytest
from fixture_helpers import PROJECT,p0_fixture,authority,sign,dump,load
from baseline_support import snapshot
from contract_runtime import digest,filehash
from p0_closure_check import check
from freeze_baseline import run as freeze
from readiness_check import reuse_errors
from business_gate import run as business
from evaluation_gate import release

def closed_fixture(tmp_path,monkeypatch):
 root=p0_fixture(tmp_path);pid='P0-01';p=root/'docs/registers/P0-CLOSURE.yaml';d=load(p);item=next(x for x in d['items'] if x['id']==pid)
 item.update(status='CLOSED',evidence=['docs/registers/closures/P0-01.json']);dump(p,d)
 log=root/'docs/registers/closures/synthetic-case.log';log.parent.mkdir(parents=True,exist_ok=True);log.write_text('Isolated verifier fixture; not a real legacy routing result.\n')
 (root/'VERSION').write_text('1.1.1\n')
 dump(root/'docs/baseline/BASELINE-AUTHORITY.yaml',{'authority':'isolated closure fixture','authorized_by':'fixture','authorized_at':'2026-10-21','scope':['test'],'change_list':[{'id':'FIXTURE','summary':'isolated'}]})
 freeze(root,write=True)
 body={'blocker_id':pid,'status':'CLOSED','source_snapshot_sha256':snapshot(root),'answers':{f'D{i+1:02}':{'conclusion':'synthetic structural fixture','evidence':[{'path':log.relative_to(root).as_posix(),'sha256':filehash(log)}]} for i in range(len(item['decision_required']))},'verified_tests':[{'id':'synthetic-only','result':'PASS'}]}
 key,kid,principal=authority(tmp_path,root,monkeypatch,roles=['integration-agent','baseline-owner'],principal='synthetic-owner')
 closure={**body,'approvals':[sign(tmp_path,key,kid,principal,'P0_APPROVAL',body)]}
 dump(root/item['evidence'][0],closure)
 return root,pid,closure

def test_valid_signed_per_decision_closure_positive(tmp_path,monkeypatch):
 root,pid,_=closed_fixture(tmp_path,monkeypatch)
 assert check(root,'strict',[pid])==[]
 assert check(root,'strict') # other real required items remain OPEN

def test_closure_text_changed_after_signature_rejected(tmp_path,monkeypatch):
 root,pid,closure=closed_fixture(tmp_path,monkeypatch);closure['answers']['D01']['conclusion']='changed after signature';dump(root/'docs/registers/closures/P0-01.json',closure)
 assert any('bind current subject' in e for e in check(root,'strict',[pid]))

def test_closure_unconfigured_trust_is_not_approval(tmp_path,monkeypatch):
 root,pid,_=closed_fixture(tmp_path,monkeypatch);monkeypatch.delenv('LLMKE_TRUST_ROOT')
 assert any('trust root not configured' in e for e in check(root,'strict',[pid]))

def test_strict_cannot_use_empty_dependency_set(tmp_path):
 assert any('nonempty' in e for e in check(p0_fixture(tmp_path),'strict',[]))

def test_real_candidate_inventory_is_honest_but_not_ready():
 assert reuse_errors(PROJECT)==[]
 assert reuse_errors(PROJECT,['CODE-01','DB-01'],strict=True)

def test_missing_business_implementation_blocks_not_skips():
 with pytest.raises(Exception,match='NOT_IMPLEMENTED'):business(PROJECT,'L1','build')

def test_unapproved_M0_cannot_release():
 with pytest.raises(Exception,match='not available'):release(PROJECT)
