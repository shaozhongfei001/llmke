"""Shared wire/domain sample and boundary tests; no live business service implied."""
import copy,hashlib
from datetime import datetime,timezone,timedelta
import pytest
from fixture_helpers import PROJECT,load
from contract_runtime import (validate_instance,ContractViolation,resolve_text_evidence,authorize_sources,validate_stream,generation_for,manifest_hash,validate_manifest,validate_activation)
from evaluation_gate import global_decision,graph_decision
TEXT='A𠀀中B'
H=hashlib.sha256(TEXT.encode()).hexdigest()

def source():return {'kb_id':'kb-a','file_id':'file-a','document_version':'v1','chunk_id':'chunk-a','content_hash':H,'offset':{'start':2,'end':3,'unit':'unicode_codepoint','text_hash':H,'parser_version':'p1'}}
def evidence():return {'evidence_id':'ev1','type':'document_text','source_ref':source()}
def hit():return {'chunk_id':'chunk-a','source':'file-a','kb_id':'kb-a','generation':'g1','document_version':'v1','search_type':'es','rank':0,'auth_scope_id':'scope-a','artifact_type':'source_chunk','source_ref':source()}
def claims():
 now=datetime.now(timezone.utc)
 return {'issuer':'auth-service','audience':['retrieval'],'subject':'user-a','service_identity':'qa-service','kb_id':'kb-a','scope':{'mode':'files','allowed_file_ids':['file-a'],'denied_file_ids':[]},'auth_version':'auth-v1','resource_version':1,'request_id':'request-0001','issued_at':(now-timedelta(seconds=1)).isoformat(),'expires_at':(now+timedelta(seconds=60)).isoformat(),'key_id':'issuer1','policy_id':'file-policy'},now

def manifest():
 x={'schema_version':'1.1.0','kb_id':'kb-a','generation':'g'+'a'*64,'documents':[{'file_id':'file-a','document_version':'v1','content_hash':H,'parsed_text_hash':H}],'build_config':{'parser_version':'p1','chunking_version':'c1','embedding_version':'e1','type_system_version':'M1-v1'},'artifacts':[{'backend':'es','location_ref':'es/g1','checksum':H,'required':True},{'backend':'milvus','location_ref':'milvus/g1','checksum':H,'required':True}],'derived_refs':[]}
 x['generation']=generation_for(x);return x

def test_source_hit_is_same_shared_domain_and_wire_model():
 validate_instance(PROJECT,'schema/llmke-retrieval-model.json',hit())
 validate_instance(PROJECT,'schema/llmke-core.json',hit(),'/$defs/RetrievalHit')

def test_non_bmp_codepoints_resolve_exact_text():assert resolve_text_evidence(PROJECT,TEXT,evidence())=='中'
def test_wrong_text_hash_rejected():
 with pytest.raises(ContractViolation):resolve_text_evidence(PROJECT,TEXT+'!',evidence())
def test_inverted_offset_rejected():
 x=hit();x['source_ref']['offset'].update(start=3,end=2)
 with pytest.raises(ContractViolation):validate_instance(PROJECT,'schema/llmke-retrieval-model.json',x)
def test_empty_community_lineage_rejected():
 x=hit();x.pop('source_ref');x.pop('document_version');x.update(artifact_id='report-1',artifact_type='community_report',artifact_revision='r1',source_refs=[],auth_version_at_build='a1',publish_state='published',lineage_complete=True)
 with pytest.raises(ContractViolation):validate_instance(PROJECT,'schema/llmke-retrieval-model.json',x)
def test_forbidden_client_perm_scope_rejected():
 x={'query':'q','kb_id':'kb-a','search_type':['es'],'perm_scope':{'subjects':['admin']}}
 with pytest.raises(ContractViolation):validate_instance(PROJECT,'schema/llmke-core.json',x,'/$defs/RetrievalRequest')
def test_unknown_error_code_rejected():
 x={'code':'GRAPH-999','http_status':500,'message':'unknown','request_id':'r1','retryable':False}
 with pytest.raises(ContractViolation):validate_instance(PROJECT,'schema/llmke-core.json',x,'/$defs/ErrorEnvelope')

@pytest.mark.parametrize('mutation',['file','deny','auth_version','audience','request_id','expired'])
def test_authorization_binding_negative(mutation):
 c,now=claims();sources=[source()];kw={'request_id':'request-0001','audience':'retrieval','auth_version':'auth-v1','resource_version':1,'now':now}
 if mutation=='file':sources[0]['file_id']='file-secret'
 elif mutation=='deny':c['scope']['denied_file_ids']=['file-a']
 elif mutation=='expired':c['expires_at']=(now-timedelta(seconds=1)).isoformat()
 else:kw[mutation]='wrong'
 with pytest.raises(ContractViolation):authorize_sources(PROJECT,c,sources,**kw)
def test_authorized_source_positive():
 c,now=claims();assert authorize_sources(PROJECT,c,[source()],request_id='request-0001',audience='retrieval',auth_version='auth-v1',resource_version=1,now=now)

def stream():return [{'type':'verification','seq':1,'request_id':'r1','claim_id':'c1','verification':'supported','delivery':'emit'},{'type':'citation','seq':2,'request_id':'r1','claim_id':'c1','evidence':[evidence()]},{'type':'answer','seq':3,'request_id':'r1','claim_id':'c1','text':'中'},{'type':'done','seq':4,'request_id':'r1','status':'complete','generation':'g1'}]
def test_valid_stream_positive():assert validate_stream(PROJECT,stream())
@pytest.mark.parametrize('mode',['early_answer','no_citation','after_done','blocked','error_then_answer'])
def test_stream_negative(mode):
 x=stream()
 if mode=='early_answer':x=[x[2],*x[:2],x[3]]
 elif mode=='no_citation':x.pop(1)
 elif mode=='after_done':x.append(copy.deepcopy(x[2]))
 elif mode=='blocked':x[0].update(verification='unsupported',delivery='block')
 else:x.insert(2,{'type':'error','seq':3,'request_id':'r1','error':{'code':'AUTH-001','http_status':401,'message':'denied','request_id':'r1','retryable':False}})
 for i,e in enumerate(x,1):e['seq']=i
 with pytest.raises(ContractViolation):validate_stream(PROJECT,x)

def activation():
 m=manifest();p={'generation':None,'version':0,'fencing_token':1};q={'kb_id':'kb-a','manifest_hash':manifest_hash(m),'expected_pointer':None,'expected_pointer_version':0,'fencing_token':1}
 run={'kb_id':'kb-a','generation':m['generation'],'manifest_hash':manifest_hash(m),'status':'ready','created_at':'2026-10-20T00:00:00Z','artifact_results':[{'backend':a['backend'],'location_ref':a['location_ref'],'checksum':a['checksum'],'ready':True} for a in m['artifacts']],'resource_version':1,'fencing_token':1}
 return q,m,run,p

def test_immutable_manifest_and_first_activation_positive():
 q,m,r,p=activation();validate_manifest(PROJECT,m);assert validate_activation(PROJECT,q,m,r,p)
@pytest.mark.parametrize('mode',['missing_artifact','stale_pointer','stale_fence','changed_content','status_in_manifest','all_optional','client_required_subset'])
def test_activation_negative(mode):
 q,m,r,p=activation()
 if mode=='missing_artifact':r['artifact_results'].pop()
 elif mode=='stale_pointer':p['version']=1
 elif mode=='stale_fence':q['fencing_token']=2
 elif mode=='changed_content':m['documents'][0]['document_version']='v2'
 elif mode=='status_in_manifest':m['status']='active'
 elif mode=='client_required_subset':q['required_artifacts']=['es']
 else:
  for a in m['artifacts']:a['required']=False
  m['generation']=generation_for(m);q['manifest_hash']=r['manifest_hash']=manifest_hash(m);r['generation']=m['generation']
 with pytest.raises(ContractViolation):validate_activation(PROJECT,q,m,r,p)

@pytest.mark.parametrize('x,expected',[(.49,'EVALUATE_COMMUNITY'),(.5,'LIGHTWEIGHT_THEN_REMEASURE'),(.699,'LIGHTWEIGHT_THEN_REMEASURE'),(.7,'DO_NOT_ADD_COMMUNITY')])
def test_global_decision_boundaries(x,expected):assert global_decision(x)==expected

def test_no_graph_gain_is_valid_disable_decision():
 assert graph_decision(.4,.49)=='DISABLED_BY_DECISION_NOT_PLATFORM_FAILURE'
 assert graph_decision(.4,.5)=='ENABLE_GRAPH_AFTER_QUALITY'


def context():
 b={'policy_id':'b1','tokenizer_version':'t1','total_input_tokens':10,'model_window_tokens':20,'system_reserved_tokens':1,'output_reserved_tokens':5,'per_document_tokens':5,'per_route_tokens':{'es':5}}
 return {'request_id':'r1','kb_id':'kb-a','generation':'g1','auth_version':'a1','resource_version':1,'policy_id':'b1','tokenizer_version':'t1','budget':b,'actual_input_tokens':5,'overhead_tokens':1,'selected_evidence_ids':['ev1'],'selected_source_refs':[source()],'contributions':[{'candidate_id':'c1','file_id':'file-a','search_type':'es','token_count':4,'evidence_ids':['ev1']}],'dropped':[],'context_hash':H}

def test_context_token_accounting_positive():validate_instance(PROJECT,'schema/llmke-context-manifest.json',context())
@pytest.mark.parametrize('mode',['total','document','route','accounting'])
def test_context_budget_negative(mode):
 x=context()
 if mode=='total':x['budget']['total_input_tokens']=5
 elif mode=='document':x['budget']['per_document_tokens']=3
 elif mode=='route':x['budget']['per_route_tokens']['es']=3
 else:x['actual_input_tokens']=4
 with pytest.raises(ContractViolation):validate_instance(PROJECT,'schema/llmke-context-manifest.json',x)

def test_source_identity_cannot_conflict():
 x=hit();x['source_ref']['file_id']='other'
 with pytest.raises(ContractViolation):validate_instance(PROJECT,'schema/llmke-retrieval-model.json',x)

def test_derived_multi_source_positive():
 x=hit();x.pop('source_ref');x.pop('document_version');x.update(artifact_type='community_report',artifact_id='report-a',artifact_revision='v1',source_refs=[source()],auth_version_at_build='a1',publish_state='published',lineage_complete=True)
 validate_instance(PROJECT,'schema/llmke-retrieval-model.json',x)
