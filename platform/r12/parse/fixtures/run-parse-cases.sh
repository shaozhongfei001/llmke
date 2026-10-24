#!/usr/bin/env bash
# R12 解析服务样本回归入口（12 用例）
#
# 用途：QA/TL 一键复验 alg_doc_parse_service 的真实解析能力（不含索引）。
# 归属：parse-ops。样本来源与断言定义见 parse_cases.py 顶部（SAMPLES / CASES）。
#
# 用法：
#   ./run-parse-cases.sh                 # 默认：有 LLM 环境变量则跑全部，否则表格类记 BLOCKED
#   ./run-parse-cases.sh --skip-upload   # 服务端 MinIO 已有样本时跳过上传
#   LLM_URL=http://127.0.0.1:18092/v1/chat/completions LLM_MODEL=<模型名> ./run-parse-cases.sh
#
# 环境变量（全部可选）：
#   R12_PARSE_BASE  默认 http://127.0.0.1:12340
#   R12_MINIO       默认 127.0.0.1:19000     R12_BUCKET 默认 r12-rag
#   MINIO_AK/MINIO_SK  默认取 platform/r12/.env 的 R12_MINIO_*
#   LLM_URL/LLM_MODEL/LLM_KEY   表格摘要（必需，否则含表格用例 BLOCKED_FOR_LLM）
#   MM_URL/MM_MODEL/MM_KEY      多模态 VLM（必需，否则 docx 内嵌图片用例 BLOCKED_FOR_MM）
#                               例：MM_URL=http://127.0.0.1:18093/v1/chat/completions MM_MODEL=qwen2.5-vl-3b-instruct
#                               注意：C08 单图实测 100–500s（CPU、与 embedding/rerank 共享核），脚本内超时 900s
#                               延迟口径：VLM 会被 llama-server prompt cache 命中，重复同一张图会得到 1–10s 的假值；
#                               评估延迟必须换新图（脚本每次都复用固定样本，故 summary 里的秒数只能看"量级"）
#
# 输出：platform/r12/logs/parse/cases/<UTC时间戳>/  （每用例原始 JSON + result.json + summary.md）
# 退出码：0=无 FAIL（BLOCKED 不算 FAIL）；1=有 FAIL。
set -uo pipefail

R12=/home/szf/data/dev/llmke-r12/platform/r12
PY=$R12/venvs/parse/bin/python
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUTDIR=${CASES_OUTDIR:-$R12/logs/parse/cases/$STAMP}

# 1) 服务健康检查（避免把"服务没起"误判成"解析失败"）
BASE=${R12_PARSE_BASE:-http://127.0.0.1:12340}
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE/docs" || true)
if [ "$code" != "200" ]; then
  echo "[FATAL] $BASE/docs -> ${code:-no-response}；解析服务未就绪（见 platform/r12/status/parse.md §1 启动命令）" >&2
  exit 2
fi

# 2) 解释器与依赖自检
[ -x "$PY" ] || { echo "[FATAL] venv 缺失：$PY" >&2; exit 2; }
"$PY" - <<'PYCHK' || { echo "[FATAL] venv 依赖不完整（需 minio/PIL/openpyxl/python-pptx/reportlab）" >&2; exit 2; }
import importlib
for m in ("minio", "PIL", "openpyxl", "pptx", "reportlab", "urllib.request"):
    importlib.import_module(m)
PYCHK

echo "[run] base=$BASE out=$OUTDIR"
exec "$PY" "$SELF_DIR/parse_cases.py" --base "$BASE" --outdir "$OUTDIR" "$@"
