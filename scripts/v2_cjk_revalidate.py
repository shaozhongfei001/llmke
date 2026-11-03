#!/usr/bin/env python3
"""D9：HippoRAG 升级后重验中文补丁（交付/升级流程固定步骤）。

判据（与 EVIDENCE-CJK-COMPAT 同口径）：
  1) 上游 text_processing 是否仍会把中文清成空串；
  2) hipporag_compat 补丁能否安装且中文保留、ASCII 路径不变；
  3) 失败时退出码非 0，禁止"装没装不知道"地继续升级。
用法：
  /home/szf/data/dev/hipporag-toolenv/bin/python scripts/v2_cjk_revalidate.py
"""
import importlib
import re
import sys


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def main() -> int:
    # 1) 上游原始行为
    try:
        import hipporag.utils.misc_utils as mu
        from hipporag.utils.misc_utils import text_processing as upstream_tp
    except Exception as exc:  # noqa: BLE001
        return fail(f"import hipporag 失败: {exc}")

    s = "智造贷 AAA档 5000万元"
    stripped = upstream_tp(s)
    keeps_chinese = bool(re.search(r"[\u4e00-\u9fff]", str(stripped)))
    print(f"[INFO] 上游 text_processing('{s}') -> {stripped!r}")
    if keeps_chinese:
        print("[PASS] 上游已保留中文（补丁可能已内建或上游已修）——仍验证补丁安装幂等性")

    # 2) 补丁安装与效果
    sys.path.insert(0, "services/rag-alg/index_data_service")
    try:
        import graph_engine_adapter.hipporag_compat as compat
    except Exception as exc:  # noqa: BLE001
        return fail(f"导入 hipporag_compat 失败: {exc}")

    try:
        report = compat.install_cjk_text_processing()
    except Exception as exc:  # noqa: BLE001
        return fail(f"补丁安装失败: {exc}")
    print(f"[INFO] 补丁报告: {report}")

    patched = mu.text_processing(s)
    ok_cn = bool(re.search(r"[\u4e00-\u9fff]", str(patched)))
    ok_ascii = mu.text_processing("abc123 XYZ") == upstream_tp("abc123 XYZ")
    print(f"[INFO] 补丁后 text_processing('{s}') -> {patched!r}")
    if not ok_cn:
        return fail("补丁后中文仍被清空")
    if not ok_ascii:
        return fail("补丁破坏了 ASCII 路径")

    print("[PASS] CJK 补丁安装与效果验证通过（中文保留、ASCII 不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
