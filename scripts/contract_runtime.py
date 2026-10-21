#!/usr/bin/env python3
"""Offline schema validation and explicit business invariants. No service/DB calls."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
from urllib.parse import urldefrag,unquote,urlparse
import yaml
from jsonschema import Draft202012Validator,FormatChecker
from referencing import Registry,Resource

class ContractViolation(ValueError):pass
class UniqueLoader(yaml.SafeLoader):pass
def _unique(loader,node,deep=False):
 out={}
 for key,value in node.value:
  k=loader.construct_object(key,deep=deep)
  if k in out:raise ContractViolation(f'duplicate mapping key: {k}')
  out[k]=loader.construct_object(value,deep=deep)
 return out
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,_unique)
def _pairs(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ContractViolation(f'duplicate JSON key: {k}')
  out[k]=v
 return out
def load(path):
 text=Path(path).read_text(encoding='utf-8')
 return json.loads(text,object_pairs_hook=_pairs) if str(path).endswith('.json') else yaml.load(text,Loader=UniqueLoader)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def filehash(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
def inside(root,rel):
 p=Path(rel)
 if p.is_absolute() or '..' in p.parts:raise ContractViolation(f'path escape: {rel}')
 resolved=(Path(root)/p).resolve()
 if not resolved.is_relative_to(Path(root).resolve()):raise ContractViolation(f'symlink escape: {rel}')
 if any(x.is_symlink() for x in [(Path(root)/p),*(Path(root)/p).parents] if x.is_relative_to(Path(root))):raise ContractViolation(f'symlink forbidden: {rel}')
 return resolved

def resources(root):
 reg=Registry()
 for path in sorted((Path(root)/'contracts/schema').glob('*.json')):
  doc=load(path);resource=Resource.from_contents(doc)
  reg=reg.with_resource(path.resolve().as_uri(),resource)
  if doc.get('$id'):reg=reg.with_resource(doc['$id'],resource)
 return reg

def validate_instance(root,schema_file,value,fragment=''):
 p=Path(root)/'contracts'/schema_file;doc=load(p)
 if fragment:
  doc={'$schema':'https://json-schema.org/draft/2020-12/schema','$ref':doc['$id']+'#'+fragment}
 validator=Draft202012Validator(doc,registry=resources(root),format_checker=FormatChecker())
 errors=sorted(validator.iter_errors(value),key=lambda x:str(x.path))
 if errors:raise ContractViolation('; '.join(f'{list(e.path)}: {e.message}' for e in errors[:4]))
 invariant_errors(value)
 return value

def invariant_errors(value):
 """Format validators cannot compare data fields; enforce these explicitly."""
 if isinstance(value,list):
  for x in value:invariant_errors(x)
  return
 if not isinstance(value,dict):return
 if {'start','end','unit'}<=value.keys() and value['unit']=='unicode_codepoint':
  if not 0<=value['start']<value['end']:raise ContractViolation('offset requires start < end')
 if {'row_start','row_end','col_start','col_end'}<=value.keys():
  if not(value['row_start']<value['row_end'] and value['col_start']<value['col_end']):raise ContractViolation('table range inverted')
 if value.get('artifact_type')=='source_chunk' and 'source_ref' in value:
  ref=value['source_ref']
  if any(value[a]!=ref[b] for a,b in [('kb_id','kb_id'),('document_version','document_version'),('chunk_id','chunk_id'),('source','file_id')]):raise ContractViolation('source hit identity/version differs from source_ref')
 if 'coverage' in value and 'hits' in value:
  requested=set(value['coverage']['requested']);served=set(value['coverage']['served']);degraded=[x['search_type'] for x in value.get('degraded',[])]
  if not served<=requested or not set(degraded)<=requested or set(degraded)&served or len(degraded)!=len(set(degraded)) or served|set(degraded)!=requested:raise ContractViolation('coverage/degraded partition mismatch')
  for h in value['hits']:
   if h['search_type'] not in served or h['generation']!=value['generation'] or h['kb_id']!=value['kb_id']:raise ContractViolation('mixed generation/scope/route hit')
 if 'actual_input_tokens' in value and 'budget' in value:
  b=value['budget']
  if value['actual_input_tokens']+b['system_reserved_tokens']>b['total_input_tokens']:raise ContractViolation('input token budget exceeded')
  if b['total_input_tokens']+b['output_reserved_tokens']>b['model_window_tokens']:raise ContractViolation('model window exceeded')
  if value['tokenizer_version']!=b['tokenizer_version'] or value['policy_id']!=b['policy_id']:raise ContractViolation('budget policy/tokenizer mismatch')
  contributions=value['contributions']
  if sum(x['token_count'] for x in contributions)+value['overhead_tokens']!=value['actual_input_tokens']:raise ContractViolation('context token accounting mismatch')
  documents={};routes={}
  source_ids={x['file_id'] for x in value['selected_source_refs']}
  for x in contributions:
   documents[x['file_id']]=documents.get(x['file_id'],0)+x['token_count'];routes[x['search_type']]=routes.get(x['search_type'],0)+x['token_count']
   if x['file_id'] not in source_ids or not set(x['evidence_ids'])<=set(value['selected_evidence_ids']):raise ContractViolation('context contribution source/evidence unresolved')
  if any(x>b['per_document_tokens'] for x in documents.values()):raise ContractViolation('per-document token budget exceeded')
  if any(x>b['per_route_tokens'].get(k,0) for k,x in routes.items()):raise ContractViolation('per-route token budget exceeded')
 if 'answer' in value and 'claims' in value:
  evidence={x['evidence_id']:x for x in value['evidence']}
  if len(evidence)!=len(value['evidence']):raise ContractViolation('duplicate evidence ID')
  claim_ids=set();citations={x['claim_id']:set(x['evidence_ids']) for x in value['citations']}
  if len(citations)!=len(value['citations']):raise ContractViolation('duplicate claim citation')
  for c in value['claims']:
   if c['claim_id'] in claim_ids:raise ContractViolation('duplicate claim ID')
   claim_ids.add(c['claim_id']);ids=set(c['evidence_ids'])
   if not ids<=evidence.keys():raise ContractViolation('unresolved evidence ID')
   span=c['answer_span']
   if not 0<=span['start']<span['end']<=len(value['answer']) or value['answer'][span['start']:span['end']]!=c['text']:raise ContractViolation('claim span/text mismatch')
   if c['verification']=='supported' and (not ids or citations.get(c['claim_id'])!=ids):raise ContractViolation('supported claim has no matching citation')
   if c['verification']=='unsupported' and c['delivery']!='annotate':raise ContractViolation('unsupported claim must be annotated')
  if not citations.keys()<=claim_ids:raise ContractViolation('citation references absent claim')
  if value['generation']!=value['context_manifest']['generation']:raise ContractViolation('QA/context generation mismatch')
 for child in value.values():invariant_errors(child)

def resolve_local(root,current,reference):
 base,pointer=urldefrag(reference)
 if not base:p=Path(current)
 elif urlparse(base).scheme:
  ids={load(x).get('$id'):x for x in (Path(root)/'contracts/schema').glob('*.json')}
  if base not in ids:raise ContractViolation(f'nonlocal reference is not permitted: {base}')
  p=ids[base]
 else:p=(Path(current).parent/unquote(base)).resolve()
 if not p.is_relative_to((Path(root)/'contracts').resolve()):raise ContractViolation('reference escapes contracts')
 node=load(p)
 if pointer:
  if not pointer.startswith('/'):raise ContractViolation('only JSON pointer fragments supported')
  for segment in pointer.split('/')[1:]:
   segment=unquote(segment).replace('~1','/').replace('~0','~')
   try:node=node[int(segment)] if isinstance(node,list) else node[segment]
   except (KeyError,IndexError,ValueError,TypeError) as e:raise ContractViolation(f'unresolved $ref {reference}') from e
 return p,node

def check_refs(root,path,doc):
 if isinstance(doc,dict):
  for key,value in doc.items():
   if key=='$ref':resolve_local(root,path,value)
   else:check_refs(root,path,value)
 elif isinstance(doc,list):
  for x in doc:check_refs(root,path,x)

def normalize_manifest(value):
 m=copy.deepcopy(value);m.pop('generation',None)
 m['documents']=sorted(m['documents'],key=lambda x:(x['file_id'],x['document_version']))
 m['artifacts']=sorted(m['artifacts'],key=lambda x:(x['backend'],x['location_ref']))
 m['derived_refs']=sorted(m['derived_refs'],key=lambda x:(x['artifact_id'],x['revision']))
 for d in m['derived_refs']:d['source_refs']=sorted(d['source_refs'],key=canonical)
 return m

def generation_for(manifest):return 'g'+digest(normalize_manifest(manifest))
def manifest_hash(manifest):return digest({**normalize_manifest(manifest),'generation':manifest['generation']})
def validate_manifest(root,manifest):
 validate_instance(root,'schema/llmke-generation-manifest.json',manifest)
 if manifest['generation']!=generation_for(manifest):raise ContractViolation('generation does not match canonical immutable content')
 if not any(x['required'] for x in manifest['artifacts']):raise ContractViolation('manifest requires at least one required artifact')
 pairs=[(x['backend'],x['location_ref']) for x in manifest['artifacts']]
 if len(pairs)!=len(set(pairs)):raise ContractViolation('duplicate artifact location')
 docs=[(x['file_id'],x['document_version']) for x in manifest['documents']]
 if len(docs)!=len(set(docs)):raise ContractViolation('duplicate document version')
 return manifest

def validate_activation(root,request,manifest,run,pointer):
 validate_instance(root,'schema/llmke-kb-operations.json',request,'/$defs/ActivationRequest');validate_manifest(root,manifest)
 validate_instance(root,'schema/llmke-generation-lifecycle.json',run)
 if request['kb_id']!=manifest['kb_id'] or run['kb_id']!=manifest['kb_id'] or run['generation']!=manifest['generation']:raise ContractViolation('activation scope/generation mismatch')
 mh=manifest_hash(manifest)
 if request['manifest_hash']!=mh or run['manifest_hash']!=mh:raise ContractViolation('activation manifest hash mismatch')
 if request['expected_pointer']!=pointer['generation'] or request['expected_pointer_version']!=pointer['version']:raise ContractViolation('pointer CAS conflict')
 if request['fencing_token']!=pointer['fencing_token'] or run['fencing_token']!=pointer['fencing_token']:raise ContractViolation('stale fencing token')
 if run['status']!='ready':raise ContractViolation('build is not ready')
 ready={(x['backend'],x['location_ref'],x['checksum']) for x in run['artifact_results'] if x['ready']}
 for x in manifest['artifacts']:
  if x['required'] and (x['backend'],x['location_ref'],x['checksum']) not in ready:raise ContractViolation('required artifact missing or checksum mismatched')
 return True

def authorize_sources(root,claims,sources,*,request_id,audience,auth_version,resource_version,now):
 from datetime import datetime
 validate_instance(root,'schema/llmke-auth-context.json',claims)
 dt=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
 if not dt(claims['issued_at'])<=now<dt(claims['expires_at']):raise ContractViolation('expired/future authorization')
 if claims['request_id']!=request_id or audience not in claims['audience'] or claims['auth_version']!=auth_version or claims['resource_version']!=resource_version:raise ContractViolation('authorization binding/version mismatch')
 scope=claims['scope']
 if scope['mode']=='files' and not scope['allowed_file_ids']:raise ContractViolation('empty file allowlist')
 for x in sources:
  if x['kb_id']!=claims['kb_id'] or x['file_id'] in scope['denied_file_ids'] or (scope['mode']=='files' and x['file_id'] not in scope['allowed_file_ids']):raise ContractViolation('unauthorized source')
 return True

def validate_stream(root,events):
 verified={};cited=set();seq=0;closed=False;request=None;failed=False
 for event in events:
  validate_instance(root,'schema/llmke-sse-events.json',event)
  if closed or event['seq']!=seq+1:raise ContractViolation('stream closed or sequence gap')
  if request is not None and event['request_id']!=request:raise ContractViolation('stream request mismatch')
  request=event['request_id'];seq+=1;t=event['type']
  if failed and t!='done':raise ContractViolation('only done is allowed after stream error')
  if t=='verification':
   cid=event['claim_id']
   if cid in verified:raise ContractViolation('duplicate verification')
   if event['verification']=='unsupported' and event['delivery']=='emit':raise ContractViolation('unsupported raw emission')
   verified[cid]=(event['verification'],event['delivery'])
  elif t=='citation':
   if event['claim_id'] not in verified or verified[event['claim_id']][0]!='supported':raise ContractViolation('citation before supported verification')
   cited.add(event['claim_id'])
  elif t=='answer':
   state=verified.get(event['claim_id'])
   if not state or state[1]=='block' or(state[0]=='supported' and event['claim_id'] not in cited):raise ContractViolation('unverified/uncited/blocked emission')
  elif t=='error':failed=True
  elif t=='done':
   if failed and event['status'] not in ['error','partial']:raise ContractViolation('error stream cannot finish complete')
   closed=True
 if not closed:raise ContractViolation('stream requires exactly one terminal done')
 return True


def resolve_text_evidence(root,text,evidence):
 validate_instance(root,'schema/llmke-core.json',evidence,'/$defs/DocumentEvidence')
 offset=evidence['source_ref']['offset']
 if hashlib.sha256(text.encode('utf-8')).hexdigest()!=offset['text_hash']:raise ContractViolation('text snapshot hash mismatch')
 if not 0<=offset['start']<offset['end']<=len(text):raise ContractViolation('offset outside exact snapshot')
 return text[offset['start']:offset['end']]
