#!/usr/bin/env python3
"""V2合同的结构与跨对象一致性检查；不执行模型、不证明业务语义或实际授权。"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts/schema/llmke-document-pipeline-v2.json"

class ContractError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise ContractError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def validate_shape(name, value):
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    selected = {"$id": schema["$id"], "$defs": schema["$defs"], "$ref": "#/$defs/" + name}
    resources = []
    for path in SCHEMA_PATH.parent.glob("*.json"):
        item = json.loads(path.read_text())
        if "$id" in item:
            resources.append((item["$id"], Resource.from_contents(item)))
    registry = Registry().with_resources(resources)
    errors = sorted(Draft202012Validator(selected, registry=registry, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        raise ContractError(str(errors[0]))

def safe_part(root, relative):
    require(isinstance(relative, str) and relative, "empty path")
    require("\\" not in relative and "%" not in relative and not re.match(r"^[A-Za-z]:", relative), "non-canonical path")
    rel = Path(relative)
    require(not rel.is_absolute() and not any(p in {".", ".."} for p in relative.split("/")), "path traversal")
    path = root / rel
    require(path.resolve().is_relative_to(root.resolve()), "path escapes snapshot")
    require(not path.is_symlink(), "symlink artifact")
    return path

def validate_artifact(artifact, root):
    validate_shape("ParseArtifact", artifact)
    require("document_ir" in artifact["quality"]["capabilities"], "IR capability required")
    singleton = ["parsed_text", "parsed_metadata", "parse_manifest", "document_ir"]
    parts = artifact["parts"]
    require(len({p["relative_path"] for p in parts}) == len(parts), "duplicate part path")
    for role in singleton:
        require(sum(p["role"] == role for p in parts) == 1, "required part missing or duplicated: " + role)
    blobs = {}
    for part in parts:
        path = safe_part(root, part["relative_path"])
        require(path.is_file(), "missing part")
        data = path.read_bytes()
        require(len(data) == part["size_bytes"] and sha(data) == part["sha256"], "part checksum/size mismatch")
        blobs[part["role"]] = data if part["role"] in singleton else blobs.get(part["role"])
    text = blobs["parsed_text"].decode("utf-8")
    require(not text.startswith("\ufeff"), "BOM needs explicit decoding profile")
    ir = json.loads(blobs["document_ir"])
    legacy = json.loads(blobs["parse_manifest"])
    metadata = json.loads(blobs["parsed_metadata"])
    require(legacy.get("status") in {"SUCCESS", "EMPTY"}, "failed legacy parse cannot publish")
    require(legacy.get("output_hash") == sha(blobs["parsed_text"]), "legacy text hash mismatch")
    require(all(x.get("content_uid") == artifact["content_uid"] for x in [ir, legacy, metadata]), "raw content identity mismatch")
    require(ir.get("schema_version") == "document-ir/1.0", "unexpected IR contract")
    blocks = ir["blocks"]
    ids = [b["block_id"] for b in blocks]
    require(len(ids) == len(set(ids)), "duplicate IR block")
    require(ir["reading_order"] == ids, "IR reading order mismatch")
    for block in blocks:
        source = block["content_ref"]
        if source["kind"] == "text_span":
            start, end = source["start_offset"], source["end_offset"]
            require(source["source"] == "parsed_text.md" and 0 <= start < end <= len(text), "invalid IR span")
            require(text[start:end] == source["text"], "IR span not exact")
    for table in ir["tables"]:
        occupied = set()
        for cell in table["cells"]:
            require(cell.get("bbox") is None and "confidence" not in cell, "IR1 cell fields cannot be extended")
            row, col, rs, cs = cell["row"], cell["col"], cell["rowspan"], cell["colspan"]
            require(row >= 0 and col >= 0 and rs >= 1 and cs >= 1, "bad table coordinates")
            require(row+rs <= table["n_rows"] and col+cs <= table["n_cols"], "table exceeds matrix")
            for r in range(row,row+rs):
                for c in range(col,col+cs):
                    require((r,c) not in occupied, "overlapping cells")
                    occupied.add((r,c))
        require(len(occupied) == table["n_rows"]*table["n_cols"], "incomplete table matrix")
    hashes = {p["sha256"] for p in parts if p["role"] == "asset"}
    legacy_hashes = {p["sha256"] for p in legacy.get("asset_files", [])}
    for figure in ir["figures"]:
        if figure["asset_path"] is not None:
            asset = safe_part(root, figure["asset_path"])
            digest = figure["asset_sha256"]
            require(asset.is_file() and sha(asset.read_bytes()) == digest, "figure asset mismatch")
            require(digest in hashes and digest in legacy_hashes, "asset manifest alignment missing")
    require(artifact["quality"]["state"] != "EMPTY" or not text.strip(), "nonempty text labeled EMPTY")
    return text, ir

def input_digest(snapshot):
    core = {"scope": snapshot["scope"], "view_kind": snapshot["view_kind"],
            "bindings": sorted(snapshot["bindings"], key=lambda b: (b["file_id"], b["document_version"]))}
    return sha(canonical(core))

def validate_snapshot(snapshot, artifacts, manifest_bytes):
    validate_shape("InputSnapshot", snapshot)
    require(snapshot["input_digest"] == input_digest(snapshot), "input digest mismatch")
    keys = [(b["file_id"], b["document_version"]) for b in snapshot["bindings"]]
    require(len(keys) == len(set(keys)), "duplicate binding")
    if snapshot["view_kind"] == "CURRENT":
        require(len({b["file_id"] for b in snapshot["bindings"]}) == len(keys), "multiple effective versions")
    for binding in snapshot["bindings"]:
        aid = binding["parse_artifact_id"]
        require(aid in artifacts and aid in manifest_bytes, "missing parse artifact")
        a = artifacts[aid]
        require(sha(manifest_bytes[aid]) == binding["artifact_manifest_hash"], "artifact manifest mismatch")
        require(binding["content_uid"] == a["content_uid"], "binding content mismatch")
        hashes = {p["role"]: p["sha256"] for p in a["parts"]}
        require(binding["parsed_text_hash"] == hashes["parsed_text"] and binding["ir_hash"] == hashes["document_ir"], "binding part hash mismatch")
        require(a["quality"]["state"] in {"COMPLETE", "EMPTY"}, "partial parse cannot enter default full release")

def validate_release(release, snapshot, builds, current_scope=None):
    validate_shape("KnowledgeRelease", release)
    require(release["scope"] == snapshot["scope"], "release scope mismatch")
    if current_scope is not None:
        require(release["scope"] == current_scope, "stale auth/resource fence")
    require(release["snapshot_id"] == snapshot["snapshot_id"] and release["input_digest"] == snapshot["input_digest"], "release snapshot mismatch")
    by_id = {b["build_id"]: b for b in builds}
    require(len(by_id) == len(builds), "duplicate build")
    for kind in ["rag", "graph", "community"]:
        state = release["readiness"][kind]
        bid = release[kind + "_build_id"]
        if state in {"READY", "READY_EMPTY"}:
            require(bid in by_id, "ready projection lacks build")
            b = by_id[bid]
            validate_shape("ProjectionBuild", b)
            require(b["kind"] == kind and b["state"] == state, "projection state mismatch")
            require(b["scope"] == release["scope"] and b["snapshot_id"] == release["snapshot_id"], "projection scope/snapshot mismatch")
            require(b["input_digest"] == release["input_digest"] and b["bindings"] == snapshot["bindings"], "mixed artifact versions")
            if kind in {"graph", "community"}:
                require(snapshot["view_kind"] == "CURRENT", "history graph not supported by this design")
            if kind == "community":
                require(release["graph_build_id"] in b["depends_on_build_ids"], "community lacks graph dependency")
                require(release["readiness"]["graph"] in {"READY", "READY_EMPTY"}, "community uses unavailable graph")
        else:
            require(bid is None or bid in by_id, "unknown nonready build")
    if release["state"] == "PUBLISHED":
        require(release["activated_at"] is not None, "publication timestamp missing")
        require(any(v in {"READY", "READY_EMPTY"} for v in release["readiness"].values()), "published release has no ready path")

def validate_source(source, snapshot, text, ir):
    validate_shape("SourceRefV2", source)
    candidates = [b for b in snapshot["bindings"] if b["file_id"] == source["file_id"] and b["document_version"] == source["document_version"]]
    require(len(candidates) == 1, "source not in authorized snapshot")
    b = candidates[0]
    for key in ["parse_artifact_id","parsed_text_hash","ir_hash"]:
        require(source[key] == b[key], "source binding mismatch")
    require(sha(text.encode("utf-8")) == source["parsed_text_hash"], "source text changed")
    block = next((v for v in ir["blocks"] if v["block_id"] == source["block_id"]), None)
    require(block is not None, "unknown source block")
    loc = source["locator"]
    if loc["kind"] == "text_span":
        start,end=loc["start_offset"],loc["end_offset"]
        require(0 <= start < end <= len(text), "source span out of bounds")
        require(sha(text[start:end].encode("utf-8")) == loc["quote_hash"], "source quote mismatch")
        if block["content_ref"]["kind"] == "text_span":
            ref = block["content_ref"]
            require(ref["start_offset"] <= start < end <= ref["end_offset"], "source outside declared block")
        else:
            raise ContractError("precise text source requires existing span or validated versioned span-map; inline text is not auto-original")
    elif loc["kind"] == "table_cell":
        t = next((v for v in ir["tables"] if v["table_id"] == loc["table_id"] and v["block_id"] == source["block_id"]), None)
        require(t is not None, "table not linked to source block")
        c = next((v for v in t["cells"] if v["row"] == loc["row"] and v["col"] == loc["col"]), None)
        require(c is not None and sha(c["text"].encode()) == loc["cell_text_hash"], "cell source mismatch")
    else:
        figure = next((v for v in ir["figures"] if v["figure_id"] == loc["figure_id"] and v["block_id"] == source["block_id"]), None)
        require(figure is not None and figure["asset_sha256"] == loc["asset_sha256"], "figure source mismatch")

def validate_report(report, assertions, snapshot, source_validator=None):
    validate_shape("CommunityReport", report)
    require(report["snapshot_id"] == snapshot["snapshot_id"], "report snapshot mismatch")
    by_id = {a["assertion_id"]: a for a in assertions}
    require(len(by_id) == len(assertions), "duplicate assertion")
    for a in assertions:
        validate_shape("Assertion", a)
    findings = {f["finding_id"]: f for f in report["findings"]}
    require(len(findings) == len(report["findings"]), "duplicate finding")
    require(set(report["summary_finding_ids"]).issubset(findings), "summary references missing finding")
    for finding in findings.values():
        complete = False
        for group in finding["support_groups"]:
            supported = True
            for term in group["all_of_terms"]:
                if term["kind"] == "assertion":
                    require(term["assertion_id"] in by_id, "missing premise")
                    assertion = by_id[term["assertion_id"]]
                    supported &= assertion["verification"] == "SUPPORTED"
                    if source_validator is not None:
                        for source in assertion["source_refs"]:
                            source_validator(source)
                else:
                    require(source_validator is not None, "raw source validator required")
                    source_validator(term["source_ref"])
            complete |= supported
        if finding["verification"] == "SUPPORTED":
            require(complete, "finding lacks a complete supported group")

def validate_example(root):
    load = lambda name: json.loads((root/name).read_text())
    artifact=load("parse-artifact.json")
    text,ir=validate_artifact(artifact,root/"artifact")
    snap=load("input-snapshot.json")
    validate_snapshot(snap,{artifact["artifact_id"]:artifact},{artifact["artifact_id"]:(root/"parse-artifact.json").read_bytes()})
    validate_release(load("release.json"),snap,load("builds.json"),snap["scope"])
    validate_source(load("source-ref.json"),snap,text,ir)
    assertions=load("assertions.json")
    for a in assertions:
        for source in a["source_refs"]:
            validate_source(source,snap,text,ir)
    validate_report(load("report.json"),assertions,snap,lambda source: validate_source(source,snap,text,ir))
    query = load("rag-query.json")
    validate_query_result(query,load("release.json"),snap,lambda source: validate_source(source,snap,text,ir))
    builds = load("builds.json")
    for kind,filename in [("graph","extraction-plan.json"),("rag","retrieval-profile-verified-synthetic.json")]:
        build = next(b for b in builds if b["kind"] == kind)
        require(build["execution_manifest_hash"]==sha((root/filename).read_bytes()),"execution manifest hash mismatch")
    validate_extraction_plan(load("extraction-plan.json"),snap,{artifact["artifact_id"]:(text,ir)},builds[1])
    validate_retrieval_profile(load("retrieval-profile.json"))
    validate_retrieval_profile(load("retrieval-profile-verified-synthetic.json"),for_publication=True)
    semantics=load("document-semantics.json")
    validate_semantics(semantics,snap,{artifact["artifact_id"]:(text,ir)})
    bundle=load("knowledge-input.json")
    validate_input_bundle(bundle,snap,{semantics["semantics_id"]:(semantics,(root/"document-semantics.json").read_bytes())})
    validate_engine_descriptor(load("engine-descriptor.json"))
    validate_engine_result(load("engine-retrieve-request.json"),load("engine-retrieve-result.json"),load("engine-input-units.json"),lambda source:validate_source(source,snap,text,ir))
    return {"status":"PASS","scope":"SYNTHETIC_CONTRACT_CONSISTENCY_ONLY","product_e2e":"NOT_EXECUTED","upstream_doc2md_ir_validator":"REQUIRED_IN_ADAPTER_SEPARATE_FROM_THIS_CHECK"}

def validate_query_result(result, release, snapshot, source_validator):
    validate_shape("QueryResult",result)
    context=result["context_manifest"]
    require(result["release_id"]==release["release_id"]==context["release_id"],"query release mismatch")
    require(result["input_digest"]==snapshot["input_digest"]==context["input_digest"],"query input mismatch")
    require(context["request_id"]==result["request_id"] and context["scope"]==snapshot["scope"],"query context mismatch")
    kind={"rag":"rag","history_compare":"rag","local":"graph","global":"community"}[result["mode"]]
    ready=release["readiness"][kind]
    if result["status"]=="OK":
        require(ready=="READY","query path not ready")
        if result["mode"]=="global":require(bool(context["selected_report_ids"]),"global did not select reports")
    elif ready not in {"READY","READY_EMPTY"}:
        require(result["status"] in {"NOT_READY","UNSUPPORTED"},"failure masquerades as no evidence")
    if ready=="READY_EMPTY":require(result["status"]=="NO_EVIDENCE","empty projection is not a supported answer")
    for source in context["selected_sources"]:source_validator(source)
    by_id={a["assertion_id"]:a for a in result["assertions"]}
    for a in by_id.values():
        for source in a["source_refs"]:source_validator(source)
    selected={sha(canonical(s)) for s in context["selected_sources"]}
    for finding in result["findings"]:
        groups=[]
        for group in finding["support_groups"]:
            terms=[]
            for term in group["all_of_terms"]:
                if term["kind"]=="source":
                    source_validator(term["source_ref"])
                    terms.append(sha(canonical(term["source_ref"])) in selected)
                else:
                    assertion=by_id.get(term["assertion_id"])
                    terms.append(bool(assertion) and assertion["verification"]=="SUPPORTED" and term["assertion_id"] in context["selected_assertion_ids"])
            groups.append(all(terms))
        if finding["verification"]=="SUPPORTED":require(any(groups),"answer lacks a complete selected support group")
    budget=context["budget"]
    require(context["actual_input_tokens"]+budget["system_reserved_tokens"]<=budget["total_input_tokens"],"context budget exceeded")
    require(budget["total_input_tokens"]+budget["output_reserved_tokens"]<=budget["model_window_tokens"],"model window exceeded")
    by_file={};by_route={};ids=set()
    for contribution in context['contributions']:
        require(contribution['contribution_id'] not in ids,'duplicate token contribution')
        ids.add(contribution['contribution_id'])
        for source in contribution['source_refs']:
            require(source['file_id']==contribution['file_id'] and sha(canonical(source)) in selected,'unselected context contribution')
        by_file[contribution['file_id']]=by_file.get(contribution['file_id'],0)+contribution['token_count']
        by_route[contribution['route']]=by_route.get(contribution['route'],0)+contribution['token_count']
    require(sum(c['token_count'] for c in context['contributions'])+context['overhead_tokens']==context['actual_input_tokens'],'token accounting mismatch')
    require(all(n<=budget['per_document_tokens'] for n in by_file.values()),'per-document token budget exceeded')
    require(all(n<=budget['per_route_tokens'].get(k,0) for k,n in by_route.items()),'per-route token budget exceeded')

def validate_extraction_plan(plan,snapshot,documents,graph_build=None):
    """只检查声明的token数；实际模型token计算、抽取质量须由运行验证。"""
    validate_shape("GraphExtractionPlan",plan)
    for key in ["snapshot_id","input_digest","scope","bindings"]:
        require(plan[key]==snapshot[key],"extraction snapshot mismatch")
    if graph_build is not None:
        require(graph_build["kind"]=="graph" and graph_build["build_id"]==plan["graph_build_id"],"extraction build mismatch")
        require(not graph_build["depends_on_build_ids"],"graph cannot depend on RAG/ES projection")
    expected={(b["parse_artifact_id"],block["block_id"]) for b in snapshot["bindings"] for block in documents[b["parse_artifact_id"]][1]["blocks"]}
    coverage={(c["parse_artifact_id"],c["block_id"]):c for c in plan["coverage"]}
    require(len(coverage)==len(plan["coverage"]) and set(coverage)==expected,"source block coverage missing/duplicated")
    windows={w["window_id"]:w for w in plan["windows"]}
    require(len(windows)==len(plan["windows"]),"duplicate extraction window")
    intervals={b["parse_artifact_id"]:[] for b in snapshot["bindings"]}
    for window in windows.values():
        aid=window["parse_artifact_id"]
        require(aid in intervals,"window artifact outside snapshot")
        text,ir=documents[aid]
        require(window["input_tokens"]+window["output_reserved_tokens"]<=plan["model_window_tokens"],"extraction context overflow")
        for span in window["md_spans"]:
            start,end=span["start_offset"],span["end_offset"]
            require(0<=start<end<=len(text),"invalid extraction MD span")
            require(span["text_hash"]==sha(text[start:end].encode()),"extraction MD span changed")
            intervals[aid].append((start,end))
        for source in window["source_refs"]:
            require(source["parse_artifact_id"]==aid,"window mixes document identities")
            validate_source(source,snapshot,text,ir)
    for (aid,bid),c in coverage.items():
        text,ir=documents[aid];block=next(b for b in ir["blocks"] if b["block_id"]==bid)
        require(c["disposition"]!="UNALIGNED","unaligned block cannot complete extraction plan")
        if c["disposition"]=="IGNORE_NONCONTENT":
            require(block["type"] in {"header","footer"} and c["reason"] and not c["window_ids"],"substantive block silently excluded")
        else:
            require(bool(c["window_ids"]),"extracted block lacks window")
            for wid in c["window_ids"]:
                require(wid in windows and windows[wid]["parse_artifact_id"]==aid,"unknown coverage window")
                require(any(s["block_id"]==bid for s in windows[wid]["source_refs"]),"window lacks declared block source")
    for aid,spans in intervals.items():
        text=documents[aid][0]
        end=0
        for start,stop in sorted(spans):
            require(not text[end:start].strip(),"extraction silently skips MD content")
            end=max(end,stop)
        require(not text[end:].strip(),"extraction silently truncates MD tail")
        whole=[w for w in windows.values() if w["parse_artifact_id"]==aid and w["mode"]=="WHOLE_DOCUMENT"]
        if whole:
            require(len(whole)==1 and sum(w["parse_artifact_id"]==aid for w in windows.values())==1,"whole-document mode is not whole")

def validate_retrieval_profile(profile,for_publication=False):
    validate_shape("RetrievalProfile",profile)
    uses_es=profile["lexical_backend"]=="es_legacy" or profile["exact_backend"]=="es_legacy"
    require(profile["es_required"]==uses_es,"hidden Elasticsearch dependency")
    if for_publication or profile["status"]=="VERIFIED":
        require(profile["status"]=="VERIFIED" and profile["backend_version"] is not None,"candidate backend cannot be published")
        require(all(v=="PASS" for v in profile["acceptance"].values()),"unverified retrieval capability")

def validate_input_bundle(bundle,snapshot,semantics):
    validate_shape("KnowledgeInputBundle",bundle)
    for key in ['snapshot_id','input_digest','scope','bindings']:
        require(bundle[key]==snapshot[key],'input bundle snapshot mismatch')
    seen=set()
    for b in bundle['semantics_bindings']:
        require(b['parse_artifact_id'] not in seen,'duplicate document semantics')
        seen.add(b['parse_artifact_id'])
        require(b['parse_artifact_id'] in {x['parse_artifact_id'] for x in snapshot['bindings']},'semantics outside authorized snapshot')
        require(b['semantics_id'] in semantics,'missing semantics companion')
        sem,blob=semantics[b['semantics_id']]
        require(sem['semantics_id']==b['semantics_id'] and sem['parse_artifact_id']==b['parse_artifact_id'],'semantics identity mismatch')
        require(sha(blob)==b['semantics_hash'],'semantics bytes changed')
        matches=[x for x in snapshot['bindings'] if x['parse_artifact_id']==b['parse_artifact_id']]
        require(all(x['enhancement_manifest_hash']==b['semantics_hash'] for x in matches),'semantics not bound into snapshot digest')
    require(seen=={b['parse_artifact_id'] for b in snapshot['bindings'] if b['enhancement_manifest_hash'] is not None},'snapshot semantics companion missing')

def validate_semantics(sem,snapshot,documents):
    validate_shape('DocumentSemantics',sem)
    aid=sem['parse_artifact_id'];bindings=[b for b in snapshot['bindings'] if b['parse_artifact_id']==aid]
    require(bool(bindings) and aid in documents,'semantics source missing')
    require(all(sem[k]==b[k] for b in bindings for k in ['parsed_text_hash','ir_hash']),'semantics source version mismatch')
    text,ir=documents[aid]
    def sources(refs):
        for source in refs:
            require(source['parse_artifact_id']==aid,'semantics mixes document identities')
            validate_source(source,snapshot,text,ir)
    def walk(node):
        if isinstance(node,dict):
            if 'source_refs' in node:sources(node['source_refs'])
            for value in node.values():walk(value)
        elif isinstance(node,list):
            for value in node:walk(value)
    walk(sem)
    tables={t['table_id']:t for t in ir['tables']}
    require(len({t['table_id'] for t in sem['tables']})==len(sem['tables']),'duplicate table semantics')
    for t in sem['tables']:
        require(t['table_id'] in tables,'semantics table not present in IR')
        cells={(c['row'],c['col']) for c in tables[t['table_id']]['cells']}
        for header in t['header_paths']:
            require(all((c['row'],c['col']) in cells for c in [header['data_cell'],*header['header_cells']]),'header path must use real anchor cells')
        for unit in t['unit_annotations']:
            require(all((c['row'],c['col']) in cells for c in unit['data_cells']),'unit annotation uses absent cell')
    figures={f['figure_id']:f for f in ir['figures']}
    require(len({f['figure_id'] for f in sem['images']})==len(sem['images']),'duplicate image understanding')
    for image in sem['images']:
        require(image['figure_id'] in figures and image['asset_sha256']==figures[image['figure_id']]['asset_sha256'],'image asset mismatch')
        if image['diagram_data'] is not None:
            nodes=[n['local_node_id'] for n in image['diagram_data']['nodes']]
            require(len(nodes)==len(set(nodes)),'duplicate diagram node')
            for edge in image['diagram_data']['edges']:
                require(edge['source'] in nodes and edge['target'] in nodes,'diagram edge has missing endpoint')

def validate_engine_descriptor(descriptor,required_capabilities=()):
    validate_shape('GraphEngineDescriptor',descriptor)
    require(set(descriptor['verified_capabilities'])<=set(descriptor['capabilities']),'verified capability not declared')
    if required_capabilities:
        require(descriptor['status']=='VERIFIED' and set(required_capabilities)<=set(descriptor['verified_capabilities']),'engine capability is not verified')

def validate_native_source_map(mapping,units):
    validate_shape('NativeSourceMap',mapping)
    known={u['unit_id'] for u in units}
    require(len(known)==len(units),'duplicate input unit')
    ids=[e['native_id'] for e in mapping['entries']]
    require(len(ids)==len(set(ids)),'duplicate native mapping key')
    mapped={u for e in mapping['entries'] for u in e['input_unit_ids']}
    require(mapped==known,'native deduplication lost or invented a source unit')

def validate_engine_result(request,result,units,source_validator):
    validate_shape('EngineRetrievalRequest',request);validate_shape('EngineRetrievalResult',result)
    for key in ['request_id','release_id','engine_index_id','snapshot_id','input_digest','scope']:
        require(request[key]==result[key],'engine result binding mismatch')
    unit_by_id={}
    for u in units:
        validate_shape('EngineInputUnit',u)
        require(u['text_hash']==sha(u['text'].encode()),'engine rendered input hash mismatch')
        require(u['unit_id'] not in unit_by_id,'duplicate input unit')
        unit_by_id[u['unit_id']]=u
        for source in u['source_refs']:source_validator(source)
    if result['status']=='OK':require(bool(result['hits']),'OK result has no hit')
    else:require(not result['hits'],'non-OK engine result exposes hits')
    if result['executed_route']=='GRAPH':
        require(result['graph_trace_hash'] is not None and result['fallback_reason'] is None,'graph route lacks execution trace')
    elif result['executed_route']=='DENSE_FALLBACK':
        require(bool(result['fallback_reason']) and result['graph_trace_hash'] is None,'hidden dense fallback')
    else:require(result['status']!='OK','route NONE cannot be OK')
    if request['require_graph_execution'] and result['executed_route']!='GRAPH':
        require(result['status'] in {'NOT_READY','UNSUPPORTED'},'dense fallback cannot satisfy required graph execution')
    require(len(result['hits'])<=request['top_k'],'engine exceeds top_k')
    for h in result['hits']:
        require(set(h['input_unit_ids'])<=set(unit_by_id),'engine returned unknown source unit')
        expected={sha(canonical(source)) for uid in h['input_unit_ids'] for source in unit_by_id[uid]['source_refs']}
        require({sha(canonical(source)) for source in h['source_refs']}==expected,'retrieval lost/invented underlying sources')
        for source in h['source_refs']:source_validator(source)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--examples",type=Path,default=ROOT/"docs/design/unified-documents-v2/examples")
    args=ap.parse_args()
    try:
        print(json.dumps(validate_example(args.examples),ensure_ascii=False))
    except (ContractError,ValueError,KeyError,OSError) as e:
        print(json.dumps({"status":"FAIL","reason":str(e)},ensure_ascii=False))
        raise SystemExit(1)
