#!/usr/bin/env bash
# T-A1 复跑：离线 surefire 缺 junit3 provider（mvn test 跑不起来），改为直接对已编译类打私有方法。
# 用法：bash scripts/a1_reference_resolve_check/run.sh <模块target/classes> <rag-common/target/classes>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
QA_CLASSES="${1:?rag-qa-service/target/classes}"
COMMON_CLASSES="${2:?rag-common/target/classes}"
ARGS="$(mktemp)"; RARGS="$(mktemp)"
python3 - "$QA_CLASSES" "$COMMON_CLASSES" "$ARGS" "$RARGS" <<'PY'
import glob, os, sys
qa, common, args, rargs = sys.argv[1:5]
jars = glob.glob(os.path.expanduser('~/.m2/repository/**/*.jar'), recursive=True)
bad = ('-sources.jar', '-javadoc.jar', 'log4j-to-slf4j', 'slf4j-log4j12', 'log4j-slf4j2-impl')
jars = [j for j in jars if not any(b in j for b in bad)]
cp = ':'.join([qa, common] + jars)
open(args, 'w').write('-cp ' + cp + '\n')
open(rargs, 'w').write('-cp .' + ':' + qa + ':' + common + ':' + ':'.join(jars) + '\n')
PY
cd "$HERE"
javac -nowarn @"$ARGS" -d . T.java T2.java
echo "--- 单元级（4 项） ---"
java @"$RARGS" T
echo "--- 真实数据全链（6 项，需 /tmp/a1-documents_list.json 与 kb_9 id=333 的真实行） ---"
java @"$RARGS" T2 333 docx-table.docx \
  "http://127.0.0.1:19000/r12-rag/kb_9/docx-table.docx/V0/docx-table.docx" \
  "r12-rag/kb_9/docx-table.docx/V0/docx-table.docx"
