#!/usr/bin/env python3
"""Retrieval/QA phases need signed M0; auth/index phases do not depend on graph enablement."""
import argparse
from evaluation_gate import release
from baseline_support import ROOT
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--profile',choices=['L1','L2','L3','L4'],required=True);a=p.parse_args()
 try:
  if a.profile in ['L3','L4']:release(ROOT);print('evaluation: PASS')
  else:print('evaluation: NOT_APPLICABLE for auth/index; not a graph/QA quality approval')
 except Exception as e:raise SystemExit('FAIL: '+str(e))
