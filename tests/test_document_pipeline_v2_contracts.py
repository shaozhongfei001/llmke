"""设计合同反例；不替代模型/UI/目标发布测试。"""
import copy, json, sys, tempfile, shutil
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import document_pipeline_v2_validate as v
E=ROOT/"docs/design/unified-documents-v2/examples"
def load(n):return json.loads((E/n).read_text())
@pytest.fixture
def dataset():
    a=load("parse-artifact.json");s=load("input-snapshot.json")
    text,ir=v.validate_artifact(a,E/"artifact")
    return a,s,text,ir

def test_synthetic_fixture_consistent():assert v.validate_example(E)["product_e2e"]=="NOT_EXECUTED"
@pytest.mark.parametrize("role",["parsed_text","parsed_metadata","parse_manifest","document_ir"])
def test_missing_required_part_fails(dataset,role):
    a,*_=dataset;a["parts"]=[p for p in a["parts"] if p["role"]!=role]
    with pytest.raises(v.ContractError):v.validate_artifact(a,E/"artifact")
def test_part_hash_tamper(dataset):
    a,*_=dataset;a["parts"][0]["sha256"]="0"*64
    with pytest.raises(v.ContractError):v.validate_artifact(a,E/"artifact")
@pytest.mark.parametrize("path",["../escape","/absolute","assets/../../escape","C:/escape","a%2f..%2fb","a\\b"])
def test_unsafe_part_path(path):
    with pytest.raises(v.ContractError):v.safe_part(E,path)
def test_snapshot_digest_changed(dataset):
    a,s,*_=dataset;s["bindings"][0]["document_version"]="v2"
    with pytest.raises(v.ContractError):v.validate_snapshot(s,{a["artifact_id"]:a},{a["artifact_id"]:(E/"parse-artifact.json").read_bytes()})
def test_ready_release_cannot_mix_artifacts(dataset):
    a,s,*_=dataset;builds=load("builds.json");builds[1]["bindings"][0]["parse_artifact_id"]="wrong"
    with pytest.raises(v.ContractError):v.validate_release(load("release.json"),s,builds,s["scope"])
def test_rag_can_be_ready_while_graph_pending(dataset):
    a,s,*_=dataset;r=load("release.json")
    for k in ["graph","community"]:r[k+"_build_id"]=None;r["readiness"][k]="PENDING"
    v.validate_release(r,s,load("builds.json")[:1],s["scope"])
def test_stale_authorization_fenced(dataset):
    a,s,*_=dataset;current=dict(s["scope"],auth_version=2)
    with pytest.raises(v.ContractError):v.validate_release(load("release.json"),s,load("builds.json"),current)
def test_ready_without_build_fails(dataset):
    a,s,*_=dataset;r=load("release.json");r["rag_build_id"]=None
    with pytest.raises(v.ContractError):v.validate_release(r,s,load("builds.json"))
def test_span_out_of_bounds(dataset):
    a,s,text,ir=dataset;source=load("source-ref.json");source["locator"]["end_offset"]=100000
    with pytest.raises(v.ContractError):v.validate_source(source,s,text,ir)
def test_modified_markdown_cannot_keep_source(dataset):
    a,s,text,ir=dataset
    with pytest.raises(v.ContractError):v.validate_source(load("source-ref.json"),s,text.replace("30BP","-30BP"),ir)
def test_wrong_source_version(dataset):
    a,s,text,ir=dataset;source=load("source-ref.json");source["document_version"]="old"
    with pytest.raises(v.ContractError):v.validate_source(source,s,text,ir)
def test_wrong_quote_hash(dataset):
    a,s,text,ir=dataset;source=load("source-ref.json");source["locator"]["quote_hash"]="0"*64
    with pytest.raises(v.ContractError):v.validate_source(source,s,text,ir)
def test_missing_support_premise(dataset):
    a,s,*_=dataset;r=load("report.json");r["findings"][0]["support_groups"][0]["all_of_terms"].append({"kind":"assertion","assertion_id":"missing"})
    with pytest.raises(v.ContractError):v.validate_report(r,load("assertions.json"),s)
def test_unverified_premise_not_supported(dataset):
    a,s,*_=dataset;assertions=load("assertions.json");assertions[0]["verification"]="NEEDS_REVIEW"
    with pytest.raises(v.ContractError):v.validate_report(load("report.json"),assertions,s)
def test_empty_support_group_rejected():
    r=load("report.json");r["findings"][0]["support_groups"][0]["all_of_terms"]=[]
    with pytest.raises(v.ContractError):v.validate_shape("CommunityReport",r)
def test_delta_requires_baseline():
    a=load("assertions.json")[0];a["object"]["baseline_entity_id"]=None
    with pytest.raises(v.ContractError):v.validate_shape("Assertion",a)
@pytest.mark.parametrize("number",["30.5","-30.5","+30.5","0","-30"])
def test_decimal_signed_values_valid(number):
    q=load("assertions.json")[0]["object"];q["value_decimal"]=number;v.validate_shape("Quantity",q)
def test_schema_does_not_prove_financial_truth():
    a=load("assertions.json")[0];a["object"]["value_decimal"]="-30"
    v.validate_shape("Assertion",a)
    assert a["object"]["value_decimal"]!="30"  # 业务预期需独立核对；形状有效不代表原文为减30。
def test_failed_task_cannot_have_ready_artifact(dataset):
    a,s,*_=dataset;t={"task_id":"t","scope":s["scope"],"file_id":"f","document_version":"v1","state":"FAILED","artifact_id":"pa","error":{"code":"PARSE-201","message":"missing","retryable":True,"request_id":"r"},"updated_at":"2026-10-30T00:00:00Z"}
    with pytest.raises(v.ContractError):v.validate_shape("ParseTask",t)
def test_event_type_payload_must_match(dataset):
    a,s,*_=dataset;e={"event_id":"e","event_type":"parse.failed","request_id":"r","scope":s["scope"],"occurred_at":"2026-10-30T00:00:00Z","payload":{"task_id":"t","file_id":"f","document_version":"v","artifact_id":"a","artifact_manifest_hash":"0"*64}}
    with pytest.raises(v.ContractError):v.validate_shape("Event",e)
def test_history_snapshot_not_accepted_as_graph(dataset):
    a,s,*_=dataset;s["view_kind"]="HISTORY_COMPARISON";s["input_digest"]=v.input_digest(s)
    r=load("release.json");r["input_digest"]=s["input_digest"];builds=load("builds.json")
    for b in builds:b["input_digest"]=s["input_digest"]
    with pytest.raises(v.ContractError):v.validate_release(r,s,builds)

def check_query(q,dataset,release=None):
    a,s,text,ir=dataset
    return v.validate_query_result(q,release or load("release.json"),s,lambda source:v.validate_source(source,s,text,ir))

def test_rag_answer_does_not_require_graph_assertions(dataset):
    q=load("rag-query.json");r=load("release.json")
    r["readiness"]["graph"]="PENDING";r["readiness"]["community"]="PENDING"
    assert q["assertions"]==[]
    check_query(q,dataset,r)

def test_global_cannot_silently_fall_back_to_rag(dataset):
    q=load("rag-query.json");q["mode"]="global";r=load("release.json");r["readiness"]["community"]="PENDING"
    with pytest.raises(v.ContractError):check_query(q,dataset,r)

def test_answer_context_cannot_mix_snapshot(dataset):
    q=load("rag-query.json");q["context_manifest"]["input_digest"]="0"*64
    with pytest.raises(v.ContractError):check_query(q,dataset)

def test_non_ok_response_cannot_emit_half_an_answer():
    q=load("rag-query.json");q["status"]="NOT_READY"
    with pytest.raises(v.ContractError):v.validate_shape("QueryResult",q)

def test_context_budget_enforced(dataset):
    q=load("rag-query.json");q["context_manifest"]["actual_input_tokens"]=100000
    with pytest.raises(v.ContractError):check_query(q,dataset)

def graph_inputs(dataset):
    a,s,text,ir=dataset
    return s,{a["artifact_id"]:(text,ir)},load("builds.json")[1]

def test_graph_from_md_does_not_need_rag_or_es(dataset):
    s,docs,b=graph_inputs(dataset)
    assert b["depends_on_build_ids"]==[]
    v.validate_extraction_plan(load("extraction-plan.json"),s,docs,b)

def test_graph_cannot_reintroduce_rag_dependency(dataset):
    s,docs,b=graph_inputs(dataset);b["depends_on_build_ids"]=["rag-example"]
    with pytest.raises(v.ContractError):v.validate_extraction_plan(load("extraction-plan.json"),s,docs,b)

def test_long_document_extraction_cannot_truncate_tail(dataset):
    s,docs,b=graph_inputs(dataset);p=load("extraction-plan.json");span=p["windows"][0]["md_spans"][0]
    text=next(iter(docs.values()))[0];span["end_offset"]=10;span["text_hash"]=v.sha(text[:10].encode())
    with pytest.raises(v.ContractError):v.validate_extraction_plan(p,s,docs,b)

def test_window_context_counts_output_reservation(dataset):
    s,docs,b=graph_inputs(dataset);p=load("extraction-plan.json");p["windows"][0]["input_tokens"]=p["model_window_tokens"]
    with pytest.raises(v.ContractError):v.validate_extraction_plan(p,s,docs,b)

def test_substantive_block_cannot_be_excluded_as_header(dataset):
    s,docs,b=graph_inputs(dataset);p=load("extraction-plan.json");p["coverage"][0].update(disposition="IGNORE_NONCONTENT",window_ids=[],reason="skip paragraph")
    with pytest.raises(v.ContractError):v.validate_extraction_plan(p,s,docs,b)

def test_backend_candidate_is_not_product_verified():
    p=load("retrieval-profile.json");v.validate_retrieval_profile(p)
    with pytest.raises(v.ContractError):v.validate_retrieval_profile(p,for_publication=True)

def test_no_es_profile_cannot_hide_legacy_es_dependency():
    p=load("retrieval-profile.json");p["lexical_backend"]="es_legacy"
    with pytest.raises(v.ContractError):v.validate_retrieval_profile(p)

def test_no_backend_names_in_v2_route_budgets():
    q=load("rag-query.json");q["context_manifest"]["budget"]["per_route_tokens"]={"es":100}
    with pytest.raises(v.ContractError):v.validate_shape("QueryResult",q)

def test_engine_fallback_is_not_graph_execution(dataset):
    a,s,text,ir=dataset;req=load('engine-retrieve-request.json');result=load('engine-retrieve-result.json')
    result.update(executed_route='DENSE_FALLBACK',fallback_reason='no seed facts',graph_trace_hash=None)
    with pytest.raises(v.ContractError):v.validate_engine_result(req,result,load('engine-input-units.json'),lambda x:v.validate_source(x,s,text,ir))

def test_engine_cannot_relabel_untraced_retrieval_as_graph(dataset):
    a,s,text,ir=dataset;result=load('engine-retrieve-result.json');result['graph_trace_hash']=None
    with pytest.raises(v.ContractError):v.validate_engine_result(load('engine-retrieve-request.json'),result,load('engine-input-units.json'),lambda x:v.validate_source(x,s,text,ir))

def test_hipporag_candidate_does_not_unlock_community():
    with pytest.raises(v.ContractError):v.validate_engine_descriptor(load('engine-descriptor.json'),['COMMUNITY_REPORTS'])

def test_content_deduplication_keeps_both_source_units():
    u=load('engine-input-units.json')[0];other=dict(u,unit_id='second-source-unit')
    mapping={'schema_version':'llmke-native-source-map/1.0','engine_index_id':'idx','bundle_hash':'1'*64,'input_units_hash':'2'*64,'entries':[{'native_id':'same-content-hash','input_unit_ids':[u['unit_id'],other['unit_id']]}]}
    v.validate_native_source_map(mapping,[u,other])
    mapping['entries'][0]['input_unit_ids'].pop()
    with pytest.raises(v.ContractError):v.validate_native_source_map(mapping,[u,other])

def multimodal():
    p=E/'multimodal';read=lambda n:json.loads((p/n).read_text())
    a=read('parse-artifact.json');s=read('input-snapshot.json');text,ir=v.validate_artifact(a,p/'artifact')
    return a,s,text,ir,read('document-semantics.json')

def test_standard_tables_and_images_have_resolvable_sources():
    a,s,text,ir,sem=multimodal();v.validate_semantics(sem,s,{a['artifact_id']:(text,ir)})
    assert ir['tables'][0]['cells'][-1]['text']=='-20'
    assert sem['images'][0]['chart_data']['series'][0]['points'][1]['y']=='-20'
    assert sem['images'][0]['description']['verification']=='CANDIDATE'

def test_image_understanding_cannot_point_to_another_asset():
    a,s,text,ir,sem=multimodal();sem['images'][0]['asset_sha256']='0'*64
    with pytest.raises(v.ContractError):v.validate_semantics(sem,s,{a['artifact_id']:(text,ir)})

def test_table_header_path_cannot_invent_a_cell():
    a,s,text,ir,sem=multimodal();sem['tables'][0]['header_paths'][0]['header_cells'][0]['col']=99
    with pytest.raises(v.ContractError):v.validate_semantics(sem,s,{a['artifact_id']:(text,ir)})

def test_semantics_change_must_change_snapshot_binding():
    a,s,text,ir,sem=multimodal();blob=(E/'multimodal/document-semantics.json').read_bytes()
    bundle={'schema_version':'llmke-knowledge-input/1.0','bundle_id':'bundle','snapshot_id':s['snapshot_id'],'input_digest':s['input_digest'],'scope':s['scope'],'bindings':s['bindings'],'semantics_bindings':[{'parse_artifact_id':a['artifact_id'],'semantics_id':sem['semantics_id'],'semantics_hash':v.sha(blob)}]}
    v.validate_input_bundle(bundle,s,{sem['semantics_id']:(sem,blob)})
    s['bindings'][0]['enhancement_manifest_hash']=None
    with pytest.raises(v.ContractError):v.validate_input_bundle(bundle,s,{sem['semantics_id']:(sem,blob)})
