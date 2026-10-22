"""Stable source fingerprints, atomic JSON, exclusive locks and signed approvals."""
from __future__ import annotations
import base64,contextlib,json,os,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from contract_runtime import canonical,digest,filehash,inside,load,ContractViolation
ROOT=Path(__file__).resolve().parents[1]

def now():return datetime.now(timezone.utc).isoformat()
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(canonical(value)+b'\n');f.flush();os.fsync(f.fileno())
  os.replace(temp,path)
 finally:
  if Path(temp).exists():Path(temp).unlink()

@contextlib.contextmanager
def exclusive(path):
 """OS lock, released on process death; all mutable state lives in one JSON."""
 import fcntl
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError as e:raise ContractViolation('concurrent operation in progress') from e
  try:yield
  finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

def source_files(root):
 root=Path(root);out=[]
 roots=['contracts','scripts','docs','modules','apps','services','lib','frontend','tests','.codebuddy','.cursor','loops']
 for sub in roots:
  for p in (root/sub).rglob('*'):
   rel=p.relative_to(root)
   if not p.is_file():continue
   if p.is_symlink():raise ContractViolation('source symlink forbidden: '+str(rel))
   if any(x in p.parts for x in ['__pycache__','.pytest_cache','.venv','venv','node_modules','.git']):continue
   if rel.as_posix().startswith(('contracts/build/','docs/reviews/','docs/registers/closures/','docs/approvals/','docs/baseline/validation/')):continue
   if sub=='loops' and(p.name!='LOOP.yaml' or '_template' in p.parts):continue
   if p.suffix in ['.pyc','.lock','.log'] and sub=='scripts':continue
   out.append(rel.as_posix())
 for rel in ['AI_GUIDE.md','Makefile','requirements.txt','requirements.lock','VERSION','README.md','.gitignore','.security-allowlist']:
  if(root/rel).is_file():out.append(rel)
 return sorted(set(out))

def snapshot(root):return digest({rel:filehash(Path(root)/rel) for rel in source_files(root)})

# --- P-03：证据绑定范围必须等于「真实输入范围」 ---------------------------------
# 旧行为：整个源码树合成一个哈希。于是改一行说明文档，7 条开发门禁与已签 QA 全部 STALE，
# 每次推进文档都要重跑全部门禁（预算只有 3 次），这是反复返工的根因。
# 新行为：拆成两个摘要，判定 STALE 用 control_digest；
# 只有显式声明「依赖文档」的门禁（读 docs/baseline/TRACE.yaml 的 traceability_gate）
# 才额外比较 doc_digest。旧记录没有 digest_scheme，按 legacy 语义继续比较整树哈希。
DIGEST_SCHEME=3
DOC_EXCLUDED=('contracts/build/','docs/reviews/','docs/registers/closures/',
              'docs/approvals/','docs/baseline/validation/')
DOC_DEPENDENT_GATES=frozenset({'traceability_gate'})

# --- W-01：业务代码也必须被"该绑它的门禁"绑住 -----------------------------------
# 实测缺口（2026-10-21）：assembler.py 追加一行注释后整树 snapshot 变了，
# 但 control_digest 没变、evidence-check 仍 PASS —— 即 scheme=2 下没有任何门禁证据绑定业务代码。
# 处置：新增第三个摘要 code_digest，只被 CODE_DEPENDENT_GATES 比较。
# 刻意**不**把业务代码并入 control_digest：那会让每次改代码作废全部门禁，等于重演 P-03 前的返工。
CODE_ROOTS=('modules','apps','services','lib','frontend')
CODE_DEPENDENT_GATES=frozenset({'independent_qa_gate'})

def code_files(root):
 """业务实现代码集：CODE_ROOTS 下 *.py，排除 tests 目录与 __pycache__（测试强度由控制面绑定）。"""
 root=Path(root);out=[]
 for sub in CODE_ROOTS:
  for p in (root/sub).rglob('*.py'):
   if not p.is_file():continue
   parts=p.parts
   if '__pycache__' in parts or 'tests' in parts:continue
   out.append(p.relative_to(root).as_posix())
 return sorted(set(out))

def code_digest(root):return digest({r:filehash(Path(root)/r) for r in code_files(root)})

def control_files(root):
 """控制面文件集：复用 freeze_baseline 的权威定义，确保「冻结什么」与「证据绑什么」一致。"""
 from freeze_baseline import controls
 return sorted(controls(Path(root)))

def doc_files(root):
 """说明性文档集：docs/** 中不属于控制面、且不在排除前缀内的部分。"""
 root=Path(root);ctl=set(control_files(root));out=[]
 for p in (root/'docs').rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(root).as_posix()
  if rel.startswith(DOC_EXCLUDED) or rel in ctl:continue
  out.append(rel)
 return sorted(set(out))

def control_digest(root):return digest({r:filehash(Path(root)/r) for r in control_files(root)})
def doc_digest(root):return digest({r:filehash(Path(root)/r) for r in doc_files(root)})

def baseline_hash(root):
 p=Path(root)/'docs/baseline/FROZEN-MANIFEST.json'
 if not p.is_file():raise ContractViolation('baseline manifest missing')
 return filehash(p)

def verify_envelope(root,envelope,*,purpose,subject_sha256=None,required_role=None):
 """Trust root is an operational input mounted by protected CI, never supplied by an agent role flag."""
 value=os.getenv('LLMKE_TRUST_ROOT')
 if not value:raise ContractViolation('external trust root not configured; independent approval stays PENDING')
 path=Path(value).resolve();root=Path(root).resolve()
 if path.is_relative_to(root):raise ContractViolation('trust root must be outside implementation workspace')
 trust=load(path)
 from freeze_baseline import run as frozen_errors
 if frozen_errors(root):raise ContractViolation('controlled baseline files changed')
 if trust.get('environment')!='PROTECTED_RUNNER':raise ContractViolation('trust configuration is not a protected runner profile')
 if trust.get('approved_baseline_sha256')!=baseline_hash(root):raise ContractViolation('external approved baseline digest mismatch')
 keyid=envelope.get('key_id');principal=(trust.get('principals') or {}).get(keyid)
 if not principal or not principal.get('enabled'):raise ContractViolation('unknown/disabled approval key')
 if required_role and required_role not in principal.get('roles',[]):raise ContractViolation('principal lacks required approval role')
 payload=envelope.get('payload',{})
 if payload.get('purpose')!=purpose or payload.get('principal_id')!=principal.get('principal_id'):raise ContractViolation('approval purpose/principal mismatch')
 if subject_sha256 is not None and payload.get('subject_sha256')!=subject_sha256:raise ContractViolation('approval does not bind current subject')
 current=datetime.now(timezone.utc);dt=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
 try:
  issued,expires=dt(payload['issued_at']),dt(payload['expires_at'])
  if not issued-timedelta(minutes=5)<=current<expires or expires-issued>timedelta(days=7):raise ValueError('expired/future/excessive validity')
 except (KeyError,ValueError,TypeError) as e:raise ContractViolation('invalid approval validity window') from e
 public=principal.get('public_key_pem')
 if not public:raise ContractViolation('public key not configured')
 try:
  signature=base64.b64decode(envelope['signature'],validate=True)
  with tempfile.TemporaryDirectory(prefix='llmke-verify-') as d:
   d=Path(d);(d/'public.pem').write_text(public);(d/'payload').write_bytes(canonical(payload));(d/'sig').write_bytes(signature)
   proc=subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(d/'public.pem'),'-rawin','-in',str(d/'payload'),'-sigfile',str(d/'sig')],capture_output=True,timeout=10)
   if proc.returncode:raise ContractViolation('invalid Ed25519 approval signature')
 except (KeyError,ValueError,OSError,subprocess.TimeoutExpired) as e:raise ContractViolation('approval verification failed') from e
 return principal
