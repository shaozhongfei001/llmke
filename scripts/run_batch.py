#!/usr/bin/env python3
"""Run only declared development gates; never claim independent QA."""
import argparse
import _pin  # noqa: F401  W-05b 必须在重型导入之前
from baseline_support import ROOT
from loop_guard import spec,run_gate
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--loop',required=True);p.add_argument('--executor',required=True);a=p.parse_args()
 try:
  _,loop,gates=spec(ROOT,a.loop)
  for g in gates:
   if g['type']=='qa_gate':continue
   if run_gate(ROOT,a.loop,g['id'],a.executor,'dev'):raise SystemExit(1)
  print('DEV_SELF_CHECK complete; independent QA remains PENDING. No business readiness implied.')
 except Exception as e:raise SystemExit('FAIL: '+str(e))
