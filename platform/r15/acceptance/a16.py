#!/usr/bin/env python3
"""A16 离线与发布（任务书 §5.2 A16）。

判据：候选包干净离线复建实装，核对全量/差分，再在既有授权目标验证；
完整源码/依赖/模型/配置与运行一致；入口可用；发布状态、签收状态如实区分。
A16 必须分项：A16-ENG（源码/依赖/模型 + 干净离线复建实装）与 A16-REL（真实目标发布与签收）。
A16-ENG 通过不能让 A16 整体或 A16-REL 变成 PASS。
写操作边界：离线复建、安装、发布、签收都是写/外部动作，本轮不执行，只做只读清点：
  P1 交付清单类文件存在（MANIFEST.sha256 / BUILD-INFO.txt / VERSION）
  P2 离线包目录存在且有文件
  N1 不得把"包存在"当"已发布"：发布状态必须来自真实签收材料，缺材料即 NOT_AVAILABLE
"""
import os

import common as C

ID = "A16"
TITLE = "离线与发布：A16-ENG / A16-REL 分项如实记录"
WRITES = True


def run():
    checks = []
    for rel in ("MANIFEST.sha256", "BUILD-INFO.txt", "VERSION"):
        p = os.path.join(C.ROOT, rel)
        checks.append(C.chk(f"P1 {rel} 存在", os.path.exists(p),
                            f"path={p} size={os.path.getsize(p) if os.path.exists(p) else 0}"))

    offline = os.path.join(C.ROOT, "platform/r12/dist/offline")
    n = 0
    if os.path.isdir(offline):
        for _, _, fs in os.walk(offline):
            n += len(fs)
    checks.append(C.chk("P2 离线包目录存在且有文件", os.path.isdir(offline) and n > 0,
                        f"dir={offline} 文件数={n}"))

    # N1：发布/签收状态必须来自真实材料；目录存在不等于已发布
    release_claim = os.path.join(C.ROOT, "platform/r12/dist/RELEASE-SIGNOFF.json")
    signed = os.path.exists(release_claim)
    checks.append(C.chk("N1 反例：不把制品存在当已发布签收", not signed,
                        f"签收材料 {release_claim} 存在={signed}；"
                        f"当前 A16-REL=NOT_AVAILABLE（无真实外部签收）"))

    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason="A16-ENG 需干净环境离线复建+实装，A16-REL 需真实目标与外部签收；"
                                 "两者均未执行，不得以只读清点充抵")
