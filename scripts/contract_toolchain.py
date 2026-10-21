#!/usr/bin/env python3
"""Clean staged generation, offline semantic validation, exact provenance linkage."""
from __future__ import annotations
import json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
from contract_registry import validate_registry
from contract_runtime import load,filehash,canonical,inside,check_refs,ContractViolation
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi
DUMMY_RE=re.compile(r'TODO|TBD|FIXME|Replace\s+with|占位|待实现|not\s+implemented',re.I)
UI_RE=re.compile(r'echarts|ag-grid|chartjs|echarts_option|render-ready',re.I)

def is_dummy_script(path):
 if not path.is_file():return 'missing file'
 text=path.read_text()
 if not text.strip() or DUMMY_RE.search(text):return 'empty or placeholder implementation'
 lines=[x.strip() for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]
 if lines and all(re.fullmatch(r'(echo\b.*|exit\s+0|true)',x) for x in lines):return 'echo-only implementation'
 return None

def fingerprints(root,contracts):
 inputs={'contracts/registry.yaml':filehash(root/'contracts/registry.yaml')}
 for c in contracts:
  inputs['contracts/'+c.path]=filehash(inside(root,'contracts/'+c.path))
  for p in [c.generator,c.checker]:
   if p and (root/p).is_file():inputs[p]=filehash(root/p)
 for rel in ['requirements.txt','requirements.lock']:
  if (root/rel).is_file():inputs[rel]=filehash(root/rel)
 for name in ['contract_toolchain.py','contract_runtime.py','contract_registry.py']:
  inputs['engine::'+name]=filehash(Path(__file__).parent/name)
 return inputs

def semantic_errors(root,contracts,layering=True):
 errors=[];schema_ids={}
 for c in contracts:
  path=root/'contracts'/c.path
  try:
   doc=load(path)
   if not isinstance(doc,dict):raise ContractViolation('contract root must be a mapping')
   check_refs(root,path,doc)
   if c.type=='schema':
    Draft202012Validator.check_schema(doc)
    sid=doc.get('$id')
    if sid in schema_ids:raise ContractViolation('duplicate schema $id: '+str(sid))
    if sid:schema_ids[sid]=c.id
   elif c.type=='api':validate_openapi(doc,base_uri=path.resolve().as_uri())
   else:
    key={'semantic':'entity_types','evidence':'evidence','evaluation':'evaluation','rules':'rules','events':'asyncapi','ontology':'ontology','skills':'skill','actions':'action'}[c.type]
    if key not in doc:raise ContractViolation('missing '+key)
   if layering and c.layer in ['domain','application'] and UI_RE.search(path.read_text()):raise ContractViolation('LAYERING: UI belongs only to BFF')
   if c.checker:
    checker=root/c.checker;reason=is_dummy_script(checker)
    if reason:raise ContractViolation('MISSING_OR_DUMMY_CHECKER: '+reason)
    p=subprocess.run([sys.executable,str(checker),'--contract',str(path),'--id',c.id],cwd=root,capture_output=True,text=True,timeout=60)
    if p.returncode:raise ContractViolation('custom checker failed: '+(p.stderr+p.stdout)[:200])
  except Exception as e:errors.append(f'{c.id}: SEMANTIC: {type(e).__name__}: {str(e)[:500]}')
 # Project-specific semantic consistency, separate from the generic registry engine.
 if any(c.id=='llmke-core' for c in contracts):
  try:
   core=load(root/'contracts/schema/llmke-core.json')
   vocabulary=load(root/'contracts/schema/llmke-error-codes.json')['$defs']['ErrorCode']['enum']
   records=load(root/'contracts/rules/llmke-error-register.yaml')['rules']['codes']
   codes=[x['code'] for x in records]
   if len(codes)!=len(set(codes)) or set(codes)!=set(vocabulary):raise ContractViolation('error register/enum mismatch or duplicate')
   from contract_runtime import validate_instance
   validate_instance(root,'schema/llmke-error-codes.json',{'codes':records})
   types=load(root/'contracts/semantic/llmke-entity-types.yaml')['entity_types']
   if len(types)!=27 or len({x['code'] for x in types})!=27:raise ContractViolation('M1 requires original 27 type codes')
   ev=load(root/'contracts/evaluation/llmke-m0-gates.yaml')['evaluation']
   if sum(ev['dataset']['quota'].values())!=100:raise ContractViolation('M0 quota total is not 100')
   if core['$defs']['Offset']['properties']['unit'].get('const')!='unicode_codepoint':raise ContractViolation('unapproved coordinate drift')
  except Exception as e:errors.append('CROSS_CONTRACT: '+str(e))
 return errors

def _write_report(root,name,report):
 p=root/'contracts/build'/name;p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p)

def generate(root):
 contracts,errors=validate_registry(root)
 if not errors:errors+=semantic_errors(root,contracts,layering=False)
 report={'report_version':2,'stage':'generate','ran_at':datetime.now(timezone.utc).isoformat(),'contracts':[],'failures':errors}
 if not errors:
  report['fingerprints']=fingerprints(root,contracts)
  try:
   with tempfile.TemporaryDirectory(prefix='llmke-generate-') as temp:
    stage=Path(temp)
    for c in contracts:
     entry={'id':c.id,'input_sha256':filehash(root/'contracts'/c.path),'outputs':{}}
     report['contracts'].append(entry)
     if not c.generator:continue
     gen=inside(root,c.generator);reason=is_dummy_script(gen)
     if reason:raise ContractViolation(f'{c.id}: MISSING_OR_DUMMY_GENERATOR: {reason}')
     p=subprocess.run([sys.executable,str(gen),'--contract',str(root/'contracts'/c.path),'--outdir',str(stage),'--id',c.id],cwd=root,capture_output=True,text=True,timeout=90)
     if p.returncode:raise ContractViolation(f'{c.id}: generator exited {p.returncode}: {(p.stderr+p.stdout)[:300]}')
     for rel in c.outputs:
      file=inside(stage,rel)
      if not file.is_file() or not file.stat().st_size:raise ContractViolation(f'{c.id}: EMPTY_OUTPUT: {rel}')
      entry['outputs'][rel]=filehash(file)
    expected={x for c in contracts for x in c.outputs}
    actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
    if actual!=expected:raise ContractViolation('OUTPUT_SET: generated files do not match registry')
    if report['fingerprints']!=fingerprints(root,contracts):raise ContractViolation('DRIFT: generation inputs changed during execution')
    for rel in sorted(expected):
     dest=inside(root,rel);dest.parent.mkdir(parents=True,exist_ok=True)
     tmp=dest.with_name('.'+dest.name+'.publishing');shutil.copyfile(stage/rel,tmp);os.replace(tmp,dest)
  except Exception as e:report['failures'].append(str(e))
 _write_report(root,'generate-report.json',report)
 for e in report['failures']:print('FAIL:',e)
 print('generate:', 'FAIL' if report['failures'] else 'PASS',f'({len(contracts)} contracts, clean staged outputs)')
 return 1 if report['failures'] else 0

def check(root):
 contracts,errors=validate_registry(root)
 report={'report_version':2,'stage':'check','contracts':[],'failures':errors}
 if not errors:
  errors+=semantic_errors(root,contracts)
  try:
   generated=load(root/'contracts/build/generate-report.json')
   if generated.get('report_version')!=2 or generated.get('failures'):raise ContractViolation('LINKAGE: missing successful v2 generate report')
   if generated.get('fingerprints')!=fingerprints(root,contracts):errors.append('DRIFT: inputs/generators/registry/toolchain/dependencies changed')
   entries=generated.get('contracts',[])
   if len(entries)!=len(contracts) or {x['id'] for x in entries}!={c.id for c in contracts}:raise ContractViolation('LINKAGE: report contract set mismatch')
   byid={x['id']:x for x in entries}
   for c in contracts:
    g=byid[c.id]
    if g.get('input_sha256')!=filehash(root/'contracts'/c.path):errors.append(c.id+': DRIFT: contract input changed')
    if set(g.get('outputs',{}))!=set(c.outputs):errors.append(c.id+': LINKAGE: output set mismatch')
    for rel in c.outputs:
     p=inside(root,rel)
     if not p.is_file() or not p.stat().st_size or filehash(p)!=g.get('outputs',{}).get(rel):errors.append(c.id+': LINKAGE: missing/changed output '+rel)
   expected={x for c in contracts for x in c.outputs}
   actual={p.relative_to(root).as_posix() for p in (root/'generated').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
   if actual!=expected:errors.append('LINKAGE: undeclared/missing generated files')
  except Exception as e:errors.append('LINKAGE: '+str(e))
 report['failures']=errors
 _write_report(root,'check-report.json',report)
 for e in errors:print('FAIL:',e)
 print('check:', 'FAIL' if errors else 'PASS',f'({len(contracts)} contracts, semantic + exact linkage)')
 return 1 if errors else 0
