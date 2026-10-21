#!/usr/bin/env python3
"""Actual build/JUnit/coverage/case gate; missing implementations block, never skip-pass."""
from pathlib import Path
import argparse,subprocess,sys,tempfile,xml.etree.ElementTree as ET
from contract_runtime import load,inside,ContractViolation
from baseline_support import ROOT

def execute(root,argv):
 p=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=900,shell=False)
 print(p.stdout);print(p.stderr,file=sys.stderr)
 if p.returncode:raise ContractViolation('business command failed: '+argv[0])

def run(root,profile,stage):
 data=load(root/'docs/acceptance/CASE-REGISTRY.yaml')['profiles'][profile]
 expected=load(root/'docs/policies/ACCEPTANCE-BASELINE.yaml')['profiles'][profile]['required_cases']
 if len(data['cases'])!=len(expected) or {x['id']:x['expected'] for x in data['cases']}!=expected:raise ContractViolation('business acceptance obligations changed')
 if data.get('implementation_status')!='READY':raise ContractViolation(profile+': real business cases/build inputs NOT_IMPLEMENTED; delivery blocked')
 if stage=='build':
  if not(root/'pom.xml').is_file() or not any((root/'services').rglob('*.py')):raise ContractViolation('real Java/Python implementation missing')
  execute(root,['mvn','-o','-B','-q','-DskipTests','package'])
  execute(root,[sys.executable,'-m','compileall','-q','services','lib']);return
 cases=data['cases'];nodes=[]
 for case in cases:
  node=case.get('pytest_node')
  if case.get('status')!='READY' or not node or not(root/node.split('::')[0]).is_file():raise ContractViolation('missing real case '+case['id'])
  nodes.append(node)
 consumers=data.get('consumer_contract_cases',[])
 if not consumers:raise ContractViolation('consumer contract tests missing')
 nodes+=consumers+data.get('python_test_nodes',[])
 if len(nodes)!=len(set(nodes)):raise ContractViolation('duplicate test selectors')
 execute(root,['mvn','-o','-B','-q','verify','-Pllmke-quality'])
 report=inside(root,data['java_coverage_xml'])
 if not report.is_file() or not data.get('java_domain_packages'):raise ContractViolation('domain coverage report/package scope missing')
 tree=ET.parse(report);selected=[p for p in tree.findall('.//package') if any(p.attrib['name'].startswith(x) for x in data['java_domain_packages'])]
 counters=[c for p in selected for c in p.findall('counter') if c.attrib.get('type')=='LINE'];covered=sum(int(x.attrib['covered']) for x in counters);missed=sum(int(x.attrib['missed']) for x in counters)
 if not covered+missed or covered/(covered+missed)<.85:raise ContractViolation('Java domain line coverage below 85% or empty')
 with tempfile.TemporaryDirectory(prefix='llmke-junit-') as d:
  junit=Path(d)/'result.xml';execute(root,[sys.executable,'-m','pytest','--strict-markers','-q','--junitxml',str(junit),*nodes])
  cases_xml=ET.parse(junit).findall('.//testcase')
  if len(cases_xml)<len(nodes) or any(c.find('skipped') is not None or c.find('failure') is not None or c.find('error') is not None for c in cases_xml):raise ContractViolation('required cases skipped, failed or not executed')

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--profile',choices=['L1','L2','L3','L4'],required=True);p.add_argument('--stage',choices=['build','test'],required=True);a=p.parse_args()
 try:run(a.root,a.profile,a.stage);print('business-gate: PASS',a.profile,a.stage);return 0
 except Exception as e:print('FAIL:',e);return 1
if __name__=='__main__':raise SystemExit(main())
