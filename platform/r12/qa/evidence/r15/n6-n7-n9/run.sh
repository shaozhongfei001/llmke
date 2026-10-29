#!/usr/bin/env bash
# RECORD_ONLY：本目录是排障过程记录，没有可独立复跑的入口。
# 原因：结论依赖当时的临时夹具与中间态（见 RESULT.md 的"局限"段）。
# 对应的稳定判据请跑：platform/r15/verify.sh
echo "[RECORD_ONLY] 本目录不可独立复跑；稳定判据见 platform/r15/verify.sh" >&2
exit 3
