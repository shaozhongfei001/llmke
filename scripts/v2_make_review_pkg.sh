#!/bin/bash
# 出下一评审包（runbook 第 6 步）。只读仓库，不推送；产物到 /home/szf/data/dev/delivery。
# 用法：bash scripts/v2_make_review_pkg.sh [--dry-run]
set -u
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
cd "$(dirname "$0")/.."
HEAD=$(git rev-parse --short=7 HEAD)
OUT=/home/szf/data/dev/delivery/llmke-v2-offline-review-${HEAD}
mkdir -p "$OUT/01_全量代码与设计"
echo "== 01 全量树（git 跟踪文件）=="
git archive HEAD | tar -x -C "$OUT/01_全量代码与设计"
N1=$(find "$OUT/01_全量代码与设计" -type f | wc -l)
echo "01 files=$N1"
echo "== 02 相对 origin/main 的改动 =="
mkdir -p "$OUT/02_相对main的改动"
git diff --name-only origin/main..HEAD | while read -r f; do
  [ -f "$f" ] || continue
  mkdir -p "$OUT/02_相对main的改动/$(dirname "$f")"
  cp "$f" "$OUT/02_相对main的改动/$f"
done
N2=$(find "$OUT/02_相对main的改动" -type f | wc -l)
echo "02 files=$N2"
echo "== 00/03/04/05 =="
cp -r docs/v2-tasks "$OUT/04_长程任务与完成度"
mkdir -p "$OUT/05_验收与进度"
cp docs/v2-tasks/evidence/*.md "$OUT/05_验收与进度/" 2>/dev/null || true
ls scripts/v2_q_acceptance.py >/dev/null 2>&1 && echo "Q 入口存在（真机跑后把 JSON 拷入 05）"
cat > "$OUT/00_评审说明.md" <<MD
# LLMKE V2 外部评审包（本会话接管开发期）

- 仓库：git@github.com:shaozhongfei001/llmke.git（origin；推送待用户确认）
- 分支：$(git rev-parse --abbrev-ref HEAD)
- 提交：$(git rev-parse HEAD)（$HEAD）
- 规模：$(git ls-files | wc -l) 个跟踪文件；相对 origin/main 改动 $N2 个文件
- 起点：上一轮评审基线 ee72f79
MD
if [ "$DRY" = "1" ]; then
  echo "[dry-run] 不打包，目录已生成可复核：$OUT"
else
  tar -czf "${OUT}.tar.gz" -C /home/szf/data/dev/delivery "$(basename "$OUT")"
  echo "打包完成：${OUT}.tar.gz"
fi
