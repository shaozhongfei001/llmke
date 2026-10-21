#!/usr/bin/env python3
"""One canonical policy source -> CodeBuddy/Cursor mirrors and workflow guidance."""
from pathlib import Path
import argparse
from contract_runtime import load
from baseline_support import ROOT

def rendered(root):
 policy=load(root/'docs/policies/AGENT-RULES.yaml');out={}
 for name,item in policy['rules'].items():
  head='---\ndescription: '+item['description']+'\nalwaysApply: '+str(item['always']).lower()+'\nglobs: "'+item['globs']+'"\n---\n\n'
  body='# '+item['description']+'\n\n'+item['body']+'\n\n规则来源：`docs/policies/AGENT-RULES.yaml`；不可直接改镜像。\n'
  out[f'.codebuddy/rules/{name}/RULE.mdc']=head+body
 for name,names in policy['cursor_groups'].items():
  selected=[policy['rules'][n] for n in names]
  always=any(x['always'] for x in selected)
  body='\n\n'.join('## '+x['description']+'\n\n'+x['body'] for x in selected)
  out['.cursor/rules/'+name]='---\nalwaysApply: '+str(always).lower()+'\nglobs: "'+','.join(sorted({x['globs'] for x in selected if x['globs']}))+'"\n---\n\n'+body+'\n\n来源：docs/policies/AGENT-RULES.yaml\n'
 for name,text in policy['workflows'].items():
  out[f'.cursor/skills/{name}/SKILL.md']=f'---\nname: {name}\ndescription: LLMKE V1.1.0 {name} workflow\n---\n\n# {name}\n\n'+text+'\n\n唯一合同入口 `contracts/registry.yaml`；当前批次见 `docs/PROJECT-PLAN.yaml`。\n'
 return out

def run(root,write=False):
 expected=rendered(root);errors=[]
 for rel,content in expected.items():
  p=root/rel
  if write:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
  elif not p.is_file() or p.read_text()!=content:errors.append('rule/workflow mirror drift: '+rel)
 return errors

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--write',action='store_true');a=p.parse_args()
 try:errors=run(a.root.resolve(),a.write)
 except Exception as e:errors=[str(e)]
 for e in errors:print('FAIL:',e)
 print('rule-mirror:', 'FAIL' if errors else 'PASS');return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
