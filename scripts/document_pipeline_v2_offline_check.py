#!/usr/bin/env python3
"""本地合同核验：仅仓内解析并内存打包OpenAPI，验证阶段禁止网络。

不调用通用contract_generate/check，不生成或冒充其证据。
"""
import argparse, copy, json, socket, urllib.request
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urldefrag

from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi
from contract_registry import validate_registry
from contract_runtime import load, check_refs, resolve_local

ROOT=Path(__file__).resolve().parents[1]

def bundle_api(path):
    """把所有schema引用先解析到仓内；未知URL立即失败，绝不fetch。"""
    external={};names={}
    def rewrite(node,current):
        if isinstance(node,list):return [rewrite(v,current) for v in node]
        if not isinstance(node,dict):return node
        out={k:rewrite(v,current) for k,v in node.items() if k not in {'$ref','$id'}}
        if '$ref' in node:
            target,selected=resolve_local(ROOT,current,node['$ref'])
            key=(str(target),urldefrag(node['$ref'])[1])
            if key not in names:
                name='local_'+str(len(names));names[key]=name;external[name]={}
                external[name]=rewrite(selected,target)
            out['$ref']='#/components/schemas/'+names[key]
        return out
    result=rewrite(load(path),path)
    result.setdefault('components',{}).setdefault('schemas',{}).update(external)
    def assert_local(node):
        if isinstance(node,dict):
            if '$ref' in node:
                ref=node['$ref'];assert ref.startswith('#/components/schemas/')
                assert ref.split('/')[-1] in result['components']['schemas']
            for value in node.values():assert_local(value)
        elif isinstance(node,list):
            for value in node:assert_local(value)
    assert_local(result)
    return result,len(external)

def run():
    attempts=[]
    def denied(*args,**kwargs):
        attempts.append('NETWORK_DENIED')
        raise RuntimeError('offline contract validation prohibits all network access')
    with ExitStack() as stack:
        for target in ['socket.create_connection','socket.getaddrinfo','socket.socket.connect','socket.socket.connect_ex','urllib.request.urlopen']:
            stack.enter_context(patch(target,denied))
        contracts,errors=validate_registry(ROOT)
        assert not errors,errors
        records=[]
        for c in contracts:
            path=ROOT/'contracts'/c.path;doc=load(path);check_refs(ROOT,path,doc)
            count=0
            if c.type=='schema':Draft202012Validator.check_schema(doc)
            elif c.type=='api':
                bundled,count=bundle_api(path)
                validate_openapi(bundled)
            records.append({'id':c.id,'type':c.type,'result':'PASS','local_schema_targets':count})
        assert not attempts,'validator attempted network access'
    return {'status':'PASS','scope':'LOCAL_REGISTRY_SCHEMA_REFS_AND_BUNDLED_OPENAPI_ONLY','contract_count':len(records),'network_attempts':len(attempts),'generic_generate_check':'NOT_RUN_AFTER_AUTO_REVIEW_REJECTION','records':records,'product_e2e':'NOT_EXECUTED'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path);args=p.parse_args()
    result=run()
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},ensure_ascii=False))
