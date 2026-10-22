"""V2 state-machine replacements for the upstream CLI-role/shell fixtures."""
import json
import pytest
from fixture_helpers import make_loop,guard,devpass,dump,load,authority,sign
from baseline_support import atomic_json
from loop_guard import qa_subject

def test_fresh_loop_draft_cannot_run(tmp_path):
 root,d=make_loop(tmp_path,status='DRAFT')
 assert guard(root,'memory-check','--loop','T1').returncode!=0
 p=guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','dev-1')
 assert p.returncode!=0 and not(root/'.test_counter').exists()

def test_valid_loop_passes_memory_and_real_dev_gate(tmp_path):
 root,d=make_loop(tmp_path)
 assert guard(root,'memory-check','--loop','T1').returncode==0
 rec=devpass(root)
 assert len(rec['sha256'])==64 and (root/rec['evidence']).stat().st_size
 assert guard(root,'evidence-check','--loop','T1').returncode==0

@pytest.mark.parametrize('mode',['empty','deleted','changed'])
def test_log_integrity(tmp_path,mode):
 root,d=make_loop(tmp_path);rec=devpass(root);p=root/rec['evidence']
 if mode=='deleted':p.unlink()
 else:p.write_text('' if mode=='empty' else 'modified')
 assert guard(root,'evidence-check','--loop','T1').returncode!=0

def test_source_change_invalidates_evidence(tmp_path):
 root,d=make_loop(tmp_path);devpass(root);(root/'scripts/changed.py').write_text('x=1\n')
 p=guard(root,'evidence-check','--loop','T1');assert p.returncode!=0 and 'STALE' in p.stdout

def test_failure_recorded_and_old_pass_not_reused(tmp_path):
 root,d=make_loop(tmp_path);devpass(root);(root/'.fail').write_text('yes')
 p=guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','dev-1')
 assert p.returncode!=0
 assert 'command exited' in (d/'FAILURES.md').read_text()
 assert load(d/'evidence/manifest.json')['gates']['repo_structure_gate']['status']=='fail'
 assert load(d/'STATE.json')['attempts']['repo_structure_gate']==2

def test_baton_cas_and_views(tmp_path):
 root,d=make_loop(tmp_path)
 p=guard(root,'baton-transfer','--loop','T1','--to','worker-1','--executor','dev-1','--expected-revision','1')
 assert p.returncode==0,p.stdout
 assert load(d/'STATE.json')['baton_holder']=='worker-1'
 assert guard(root,'memory-check','--loop','T1').returncode==0
 assert guard(root,'baton-transfer','--loop','T1','--to','worker-2','--executor','worker-1','--expected-revision','1').returncode!=0
 assert load(d/'STATE.json')['baton_holder']=='worker-1'

def test_drifted_views_recover_only_from_state(tmp_path):
 root,d=make_loop(tmp_path);(d/'memory/NEXT_SESSION.md').write_text('wrong holder')
 assert guard(root,'memory-check','--loop','T1').returncode!=0
 assert guard(root,'render-views','--loop','T1').returncode==0
 assert guard(root,'memory-check','--loop','T1').returncode==0

def test_nonholder_may_not_execute(tmp_path):
 root,d=make_loop(tmp_path)
 assert guard(root,'run-gate','--loop','T1','--gate','repo_structure_gate','--executor','worker-1').returncode!=0
 assert not(root/'.test_counter').exists()

def test_done_cannot_be_forged_without_all_gates(tmp_path):
 root,d=make_loop(tmp_path);devpass(root);state=load(d/'STATE.json');state['status']='DONE';atomic_json(d/'STATE.json',state)
 assert guard(root,'evidence-check','--loop','T1').returncode!=0

def test_signed_independent_qa_positive_finish(tmp_path,monkeypatch):
 root,d=make_loop(tmp_path);devpass(root)
 p=guard(root,'baton-transfer','--loop','T1','--to','qa-independent','--executor','dev-1','--expected-revision','2');assert p.returncode==0,p.stdout
 p=guard(root,'qa-run','--loop','T1','--gate','e2e_smoke_gate','--executor','qa-independent');assert p.returncode==0,p.stdout
 rec=load(d/'evidence/manifest.json')['gates']['e2e_smoke_gate'];assert rec['status']=='QA_PENDING'
 assert guard(root,'finish','--loop','T1').returncode!=0
 key,kid,principal=authority(tmp_path,root,monkeypatch)
 g=load(d/'LOOP.yaml')['gates'][1];envelope=sign(tmp_path,key,kid,principal,'QA_ATTESTATION',qa_subject('T1',g,rec));dump(tmp_path/'approval.json',envelope)
 p=guard(root,'accept-qa','--loop','T1','--gate','e2e_smoke_gate','--attestation',str(tmp_path/'approval.json'));assert p.returncode==0,p.stdout
 p=guard(root,'finish','--loop','T1');assert p.returncode==0,p.stdout
 assert load(d/'STATE.json')['status']=='DONE'
 assert guard(root,'evidence-check','--loop','T1').returncode==0

def test_qa_wrong_signature_rejected(tmp_path,monkeypatch):
 root,d=make_loop(tmp_path);devpass(root)
 guard(root,'baton-transfer','--loop','T1','--to','qa-independent','--executor','dev-1','--expected-revision','2')
 assert guard(root,'qa-run','--loop','T1','--gate','e2e_smoke_gate','--executor','qa-independent').returncode==0
 rec=load(d/'evidence/manifest.json')['gates']['e2e_smoke_gate'];g=load(d/'LOOP.yaml')['gates'][1]
 key,kid,pid=authority(tmp_path,root,monkeypatch);e=sign(tmp_path,key,kid,pid,'QA_ATTESTATION',qa_subject('T1',g,rec));e['signature']='AA=='
 dump(tmp_path/'approval.json',e)
 assert guard(root,'accept-qa','--loop','T1','--gate','e2e_smoke_gate','--attestation',str(tmp_path/'approval.json')).returncode!=0

def test_transfer_does_not_unblock(tmp_path):
 root,d=make_loop(tmp_path,status='BLOCKED')
 assert guard(root,'baton-transfer','--loop','T1','--to','worker-1','--executor','tech-lead','--expected-revision','1').returncode==0
 assert load(d/'STATE.json')['blocked'] is True


def test_stale_qa_candidate_rejected_even_with_valid_signature(tmp_path,monkeypatch):
    """W-04：签名有效 ≠ 可以接受过期候选。

    `accept_qa` 里 stale 检查必须先于签名校验；顺序被调换或检查被删掉时，
    "过期候选 + 有效签名"会被接受，而现有测试都发现不了。
    """
    root,d=make_loop(tmp_path);devpass(root)
    assert guard(root,'baton-transfer','--loop','T1','--to','qa-independent','--executor','dev-1','--expected-revision','2').returncode==0
    assert guard(root,'qa-run','--loop','T1','--gate','e2e_smoke_gate','--executor','qa-independent').returncode==0
    rec=load(d/'evidence/manifest.json')['gates']['e2e_smoke_gate'];g=load(d/'LOOP.yaml')['gates'][1]
    key,kid,principal=authority(tmp_path,root,monkeypatch)
    envelope=sign(tmp_path,key,kid,principal,'QA_ATTESTATION',qa_subject('T1',g,rec))
    (root/'scripts'/'extra.py').write_text('x = 1\n')      # 候选过期：控制面变了
    dump(tmp_path/'approval.json',envelope)
    p=guard(root,'accept-qa','--loop','T1','--gate','e2e_smoke_gate','--attestation',str(tmp_path/'approval.json'))
    assert p.returncode!=0,p.stdout+p.stderr
    assert 'STALE' in (p.stdout+p.stderr)
