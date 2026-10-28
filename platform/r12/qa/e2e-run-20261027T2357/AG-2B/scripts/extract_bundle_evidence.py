#!/usr/bin/env python3
"""AG-2B · ① 包内证据：从线上 entry bundle 抠出 resolvePreviewTarget 及其 presign 调用，
并枚举 dist/assets 全部 chunk，确认该逻辑的唯一副本位置与下发一致性。
输出：AG-2B/evidence/bundle-extract.txt
"""
import hashlib
import json
import pathlib
import re
import urllib.request

BASE = "http://127.0.0.1:18088"
ROOT = pathlib.Path("/home/szf/data/dev/llmke-r12")
DIST = ROOT / "frontend/plateform/dist"
OUT = pathlib.Path("/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2B/evidence")
OUT.mkdir(parents=True, exist_ok=True)

html = (DIST / "index.html").read_text(encoding="utf-8", errors="replace")
m = re.search(r"assets/index-[A-Za-z0-9_-]+\.js", html)
entry = m.group(0)

local = (DIST / entry).read_bytes()
served = urllib.request.urlopen(f"{BASE}/{entry}").read()
lines = []
w = lines.append
w("== AG-2B ① 包内证据：presign 是否位于 fileType 分支之前 ==")
w(f"entry asset          : {entry}")
w(f"local  md5 / bytes   : {hashlib.md5(local).hexdigest()} / {len(local)}")
w(f"served md5 / bytes   : {hashlib.md5(served).hexdigest()} / {len(served)}")
w(f"local == served      : {local == served}")
s = served.decode("utf-8", errors="replace")
w(f"decoded chars        : {len(s)}")
w("")

# 1) 全部 chunk 枚举：确认该逻辑副本位置（避免只搜 entry = 局部搜索冒充全量）
needle = "缺少原文对象键，无法打开原文"
hits = []
for f in sorted((DIST / "assets").glob("*.js")):
    txt = f.read_text(encoding="utf-8", errors="replace")
    n = txt.count(needle)
    if n:
        try:
            dl = hashlib.md5(f.read_bytes()).hexdigest()
            dv = hashlib.md5(urllib.request.urlopen(f"{BASE}/assets/{f.name}").read()).hexdigest()
        except Exception:
            dl = dv = "n/a"
        hits.append((f.name, n, len(txt), dl, dv))
w("-- chunk 枚举（特征串：%s）--" % needle)
w(f"dist/assets/*.js 文件数: {len(list((DIST / 'assets').glob('*.js')))}")
for h in hits:
    w(f"  {h[0]:<28} 命中={h[1]} chars={h[2]} dist_md5={h[3]} served_md5={h[4]} 一致={h[3]==h[4]}")
w("")

# 2) 抽取关键片段
def ctx(start, end):
    return s[max(0, start - 60): end]

i_presign_const = s.find('"/proxy/index/knowledgeBase/file/presign"')
i_needle = s.find(needle)
w("-- 片段 A：接口常量（presign / stream / previewStream）--")
w(ctx(i_presign_const, i_presign_const + 200))
w("")

# Go = 签发函数：从常量后的 `Go=async(` 开始
i_go = s.find("Go=async(", i_presign_const)
w("-- 片段 B：Go() = getPresignedObjectUrl（含三态错误映射）--")
w(s[i_go: i_go + 1050])
w("")

# qo = resolvePreviewTarget
i_qo = s.find("qo=async(", i_go)
w("-- 片段 C：qo() = resolvePreviewTarget（presign → 类型分支）--")
w(s[i_qo: i_qo + 420])
w("")

# 3) 结构判定（按位置而非猜测）
seg = s[i_qo: i_qo + 420]
pos_presign_call = seg.find("await Go(")
pos_first_branch = seg.find("return zo(")
w("-- 结构判定 --")
w(f"qo() 内 `await Go(` 偏移      : {pos_presign_call}")
w(f"qo() 内第一个类型分支 return   : {pos_first_branch}")
w(f"presign 在类型分支之前        : {0 <= pos_presign_call < pos_first_branch}")
w("判据：`await Go(t,r)` 的返回值赋给 n；随后才是 `return zo(s)?{...}:lr(s)||$o(s)?{...}:{...}`。")
w("      zo=isImageType, lr=isOfficePreviewType, $o=isSheetType；Go=getPresignedObjectUrl(Oo=presign 常量)。")
w("      即所有类型都会**先 await presign**，任一类型失败都不会再发取流请求。")
w("")

# 4) 三态文案在包内
w("-- 片段 D：三态错误文案（包内常量，用于 S5-08 文案对照）--")
for pat in ["原文不存在或已删除", "无权访问该原文", "原文服务异常（HTTP "]:
    i = s.find(pat)
    w(f"  {pat}  命中={i}")
w("")

manifest = {
    "entry": entry,
    "md5": hashlib.md5(served).hexdigest(),
    "chars": len(s),
    "resolvePreviewTarget": {
        "presign_call_offset_in_fn": pos_presign_call,
        "first_type_branch_offset_in_fn": pos_first_branch,
        "presign_before_type_branch": 0 <= pos_presign_call < pos_first_branch,
    },
    "chunks_with_needle": [h[0] for h in hits],
}
(OUT / "bundle-extract.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
(OUT / "bundle-extract.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
