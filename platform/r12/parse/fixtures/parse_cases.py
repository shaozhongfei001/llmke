#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
R12 解析服务样本回归（12 用例）。

由 run-parse-cases.sh 调用；也可单独执行：
    /home/szf/data/dev/llmke-r12/platform/r12/venvs/parse/bin/python parse_cases.py --outdir /tmp/x

事实约定（与 R12-ENV-CONTRACT / platform/r12/status/parse.md 一致）：
- 服务按 MinIO 路径 `bucket/object` 取文件，bucket=路径第一段 → 本脚本把样本上传到 `r12-rag/fixtures/*`。
- 需要 LLM 的用例（表格摘要）：`LLM_URL/LLM_MODEL[/LLM_KEY]`；缺省时该用例记 BLOCKED_FOR_LLM，不算 PASS 也不算 FAIL。
- 需要多模态 VLM 的用例（docx 内嵌图片）：`MM_URL/MM_MODEL[/MM_KEY]`；缺省时记 BLOCKED_FOR_MM（R12 已知限制，见报告 §8-①）。
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

R12 = Path("/home/szf/data/dev/llmke-r12/platform/r12")
DEFAULT_SRC = Path("/home/szf/data/dev/coordination/samples")
FIX_LOCAL = Path(__file__).resolve().parent / "generated"   # 生成样本落这里

# ---------------------------------------------------------------- 样本清单
# (本地文件名, MinIO key 后缀, 来源: sample=TL提供 / gen=本脚本生成)
SAMPLES = [
    ("pdf-digital.pdf",   "pdf-digital.pdf",   "sample"),
    ("pdf-scanned.pdf",   "pdf-scanned.pdf",   "sample"),
    ("pdf-encrypted.pdf", "pdf-encrypted.pdf", "sample"),
    ("docx-plain.docx",   "docx-plain.docx",   "sample"),
    ("docx-table.docx",   "docx-table.docx",   "sample"),
    ("docx-image.docx",   "docx-image.docx",   "sample"),
    ("scan-text.png",     "scan-text.png",     "gen"),
    ("table-ledger.xlsx", "table-ledger.xlsx", "gen"),
    ("image-slide.pptx",  "image-slide.pptx",  "gen"),
    ("cn-digital.pdf",    "cn-digital.pdf",    "gen"),
    ("cn-scan.pdf",       "cn-scan.pdf",       "gen"),
    ("big-table.xlsx",    "big-table.xlsx",    "gen"),   # 附加：大表压力
]

# ---------------------------------------------------------------- 用例与断言
# chinese: 期望正文含中文；types: 必须出现的 metadata.type；
# loc: 期望至少一种定位信息（offset/page_number/position 且非全 0）；
# table_md: 表格块必须是 markdown 表格；ocr_kw: OCR 输出应出现的关键词（证明走 OCR 且内容相关）；
# business_fail: 负例，期望 HTTP200 但 success=false + 指定 code。
CASES = [
    dict(id="C01", file="pdf-digital.pdf",   desc="数字版PDF(英文TL样本) 文本层抽取", chinese=False, types=["text"], loc=True),
    dict(id="C02", file="cn-digital.pdf",    desc="数字版中文PDF 文本层抽取",         chinese=True,  types=["text"], loc=True),
    dict(id="C03", file="pdf-scanned.pdf",   desc="扫描版PDF(TL样本) OCR分支",        chinese=False, types=["text"], loc=True),
    dict(id="C04", file="cn-scan.pdf",       desc="中文扫描PDF(无文本层) OCR分支",    chinese=True,  types=["text"], loc=True, ocr_kw=["授信", "上海浦东"]),
    dict(id="C05", file="scan-text.png",     desc="中文图片 单图OCR",                chinese=True,  types=["text"], loc=True, ocr_kw=["授信审批", "5000"]),
    dict(id="C06", file="docx-plain.docx",   desc="DOCX 纯文本",                     chinese=True,  types=["text"], loc=False),
    dict(id="C07", file="docx-table.docx",   desc="DOCX 含表格（表格摘要需LLM）",     chinese=True,  types=["text", "table"], loc=False, table_md=True, needs_llm=True),
    dict(id="C08", file="docx-image.docx",   desc="DOCX 内嵌图片（需VLM）",           chinese=False, types=[], loc=False, needs_llm=True, needs_mm=True, expect_image_chunks=1),
    dict(id="C09", file="table-ledger.xlsx", desc="XLSX 含表格（表格摘要需LLM）",      chinese=True,  types=["table"], loc=False, table_md=True, needs_llm=True, table_kw=["客户编号", "授信额度"]),
    dict(id="C10", file="image-slide.pptx",  desc="PPTX 文本（图片通路上游已关闭）",  chinese=True,  types=["text"], loc=False),
    dict(id="C11", file="pdf-encrypted.pdf", desc="加密PDF 负例：应优雅失败",         business_fail=True, expect_code=1100),
    dict(id="C12", files=["cn-digital.pdf", "cn-scan.pdf"], desc="多文件同请求（2 文件）", chinese=True, types=["text"], loc=True),
    # [R12-FIX-CONV-03 回归] 中文 docx **直读**完整性：防止 Java 侧退回"docx→无中文字体 PDF"导致汉字全丢
    # 实测事故：转换后 PDF 只剩 47 字/0 汉字（`“”PRD-CORP-LOAN-2026-01R1250...`），直读 docx 为 459 字/376 汉字（100%）
    dict(id="C16", file="cn-docx-direct.docx", desc="中文DOCX直读 汉字完整性（防CONV-03回归）",
         chinese=True, types=["text"], loc=True, min_chars=380, min_chinese=350,
         text_kw=["智造贷", "授信额度", "5000", "三年", "汽车零部件"]),
    # 附加压力用例（需 --with-stress）：规则大表按行切分 + 表头重复，摘要只取前 9 行
    dict(id="C13", file="big-table.xlsx", desc="大表 40行×8列 规则表切分（附加）",
         chinese=True, types=["table"], loc=False, table_md=True, needs_llm=True, stress=True,
         min_chunks=5, table_kw=["客户编号", "五级分类"]),
    # 多图用例（需 --with-vlm-heavy；单次 500-700s，VLM 侧 7.7G RSS，必须串行）
    dict(id="C14", file="docx-2images.docx", desc="2 张整页扫描图（多图）", chinese=False,
         types=["image"], loc=False, needs_llm=True, needs_mm=True, vlm_heavy=True, expect_image_chunks=2),
    dict(id="C15", file="docx-3images.docx", desc="3 张整页扫描图（多图）", chinese=False,
         types=["image"], loc=False, needs_llm=True, needs_mm=True, vlm_heavy=True, expect_image_chunks=3),
]

# ---------------------------------------------------------------- 样本生成
def gen_fixtures(src_dir: Path):
    FIX_LOCAL.mkdir(parents=True, exist_ok=True)
    # TL 提供的样本直接复制
    for name, _, origin in SAMPLES:
        dst = FIX_LOCAL / name
        if origin == "sample" and not dst.exists():
            s = src_dir / name
            if not s.exists():
                print(f"[WARN] 缺 TL 样本 {s}，用例将失败", file=sys.stderr)
                continue
            dst.write_bytes(s.read_bytes())

    from PIL import Image, ImageDraw, ImageFont
    font = "/usr/local/share/fonts/windows/simsun.ttc"
    if not Path(font).exists():
        font = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"

    def _text_img():
        img = Image.new("RGB", (1000, 420), "white")
        d = ImageDraw.Draw(img)
        f1, f2 = ImageFont.truetype(font, 40), ImageFont.truetype(font, 32)
        for i, line in enumerate([
            "附件三：授信审批意见通知书",
            "客户名称：上海浦东发展集团有限公司",
            "授信金额：人民币 5000 万元",
            "审批结论：同意，期限 12 个月",
            "签发日期：2026年10月20日",
            "编号：SPDB-2026-PJ-00871",
        ]):
            d.text((30, 30 + i * 60), line, font=f1 if i == 0 else f2, fill="black")
        return img

    p_cn_docx = FIX_LOCAL / "cn-docx-direct.docx"
    if not p_cn_docx.exists():
        from docx import Document as _Doc
        _d = _Doc()
        _lines = [
            '"智造贷"企业流动资金贷款产品说明书',
            '文件编号：PRD-CORP-LOAN-2026-01（R12 回归夹具）',
            '一、适用对象',
            '面向制造业中小微企业，重点支持汽车零部件、装备制造、电子信息三条产业链上的规模以上工业企业。借款人须持续经营满三年，近十二个月无连续逾期记录。',
            '二、授信额度',
            '单户最高授信额度为人民币5000万元。其中信用方式不超过1000万元，其余部分须以应收账款质押、设备抵押或核心企业保证方式增信。额度有效期为十二个月，到期需重新核定。',
            '三、贷款期限与利率',
            '流动资金贷款期限最长三年，单笔提款期限不超过十二个月。执行利率按放款日全国银行间同业拆借中心公布的一年期贷款市场报价利率加点形成，加点幅度根据客户信用评级确定：AAA级加30个基点，AA级加60个基点，A级加100个基点。',
            '四、还款方式',
            '可采用按月付息到期还本、等额本息或按季付息分期还本三种方式。提前还款需提前十五个工作日提出书面申请，不收取违约金。',
            '五、办理时限',
            '资料齐全的情况下，自受理之日起十个工作日内完成审批，审批通过后三个工作日内放款。',
        ]
        for _t in _lines:
            _d.add_paragraph(_t)
        _d.save(p_cn_docx)

    p = FIX_LOCAL / "scan-text.png"
    if not p.exists():
        _text_img().save(p)

    p = FIX_LOCAL / "cn-scan.pdf"
    if not p.exists():
        _text_img().convert("RGB").save(p, "PDF", resolution=150)

    p = FIX_LOCAL / "table-ledger.xlsx"
    if not p.exists():
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "授信台账"
        for r in [
            ["客户编号", "客户名称", "授信额度(万元)", "已用额度(万元)", "五级分类", "到期日"],
            ["CUST-CORP-0001", "上海浦东发展集团有限公司", 5000, 3200, "正常", "2027-03-31"],
            ["CUST-CORP-0002", "江苏恒瑞医药股份有限公司", 8000, 6100, "正常", "2026-12-31"],
            ["CUST-CORP-0003", "杭州海康威视数字技术有限公司", 12000, 11500, "关注", "2026-11-30"],
            ["CUST-CORP-0004", "宁波均胜电子股份有限公司", 3000, 2950, "次级", "2026-10-31"],
        ]:
            ws.append(r)
        wb.save(p)

    p = FIX_LOCAL / "image-slide.pptx"
    if not p.exists():
        from pptx import Presentation
        from pptx.util import Inches
        chart = FIX_LOCAL / "chart.png"
        if not chart.exists():
            im = Image.new("RGB", (900, 500), "white")
            cd = ImageDraw.Draw(im)
            fc = ImageFont.truetype(font, 30)
            for i, line in enumerate(["华东地区不良率 1.05%", "华南地区不良率 1.35%", "华北地区不良率 1.88%"]):
                cd.text((20, 20 + i * 70), line, font=fc, fill="black")
                cd.rectangle([500, 30 + i * 90, 500 + int((0.35 + i * 0.2) * 400), 80 + i * 90], fill=(40, 90, 160))
            im.save(chart)
        prs = Presentation()
        s1 = prs.slides.add_slide(prs.slide_layouts[1])
        s1.shapes.title.text = "2026年上半年风险资产分析"
        s1.placeholders[1].text = "不良率 1.12%，较年初下降 0.08 个百分点；关注类占比上升。"
        s2 = prs.slides.add_slide(prs.slide_layouts[5])
        s2.shapes.title.text = "区域风险分布图"
        s2.shapes.add_picture(str(chart), Inches(1), Inches(1.6), width=Inches(7))
        prs.save(p)

    p = FIX_LOCAL / "big-table.xlsx"
    if not p.exists():
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "大表压力"
        ws.append(["序号", "客户编号", "客户名称", "授信额度(万元)", "已用额度(万元)", "五级分类", "到期日", "客户经理"])
        for i in range(40):
            ws.append([i + 1, f"CUST-CORP-{i:04d}", f"上海示例实业集团有限公司第{i}分公司",
                       5000 + i * 10, 3200 + i * 5, "正常" if i % 7 else "关注", "2027-03-31", f"RM{i % 5}"])
        wb.save(p)

    p = FIX_LOCAL / "cn-digital.pdf"
    if not p.exists():
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        pdfmetrics.registerFont(TTFont("SimSun", font, subfontIndex=0) if font.endswith(".ttc") else TTFont("SimSun", font))
        c = canvas.Canvas(str(p), pagesize=A4)
        w, h = A4
        c.setFont("SimSun", 16); c.drawString(60, h - 70, "附件二：客户访前准备·授信审批材料（数字版）")
        c.setFont("SimSun", 12); y = h - 110
        for line in [
            "客户名称：上海浦东发展集团有限公司   客户编号：CUST-CORP-0001",
            "日均存款：2,983,333.33 元（口径按 30 个自然日、跨账户汇总计算）",
            "授信额度：人民币 5000 万元；已用额度：3200 万元；五级分类：正常",
            "审批结论：同意，期限 12 个月，需补充供应链上下游合同与纳税证明。",
            "风险提示：逾期欠息 0 次，涉诉及被执行记录 0 条，上下游集中度偏高需复核。",
        ]:
            c.drawString(60, y, line); y -= 26
        c.showPage(); c.save()
    print(f"[fixtures] 目录 {FIX_LOCAL} 就绪：", sorted(x.name for x in FIX_LOCAL.iterdir() if x.is_file()))


# ---------------------------------------------------------------- MinIO 上传
def upload(bucket: str, endpoint: str, ak: str, sk: str):
    from minio import Minio
    cli = Minio(endpoint, access_key=ak, secret_key=sk, secure=False)
    if not cli.bucket_exists(bucket):
        cli.make_bucket(bucket)
        print(f"[minio] 创建 bucket {bucket}")
    # 全量上传目录内的夹具（原实现只传 SAMPLES 白名单，新增夹具会漏传并报 NoSuchKey）
    n = 0
    for f in sorted(FIX_LOCAL.iterdir()):
        if f.is_file():
            cli.fput_object(bucket, f"fixtures/{f.name}", str(f))
            n += 1
    print(f"[minio] 上传完成 {n} 个 -> {endpoint}/{bucket}/fixtures/")


# ---------------------------------------------------------------- HTTP
def call(base, keys, chunk_size=512, overlap=100, timeout=900):
    body = {
        "knowledge_base_name": "r12-parse-cases",
        "files": [{"file_path": f"{os.environ.get('R12_BUCKET', 'r12-rag')}/fixtures/{k}",
                   "file_id": 3000 + i, "file_size": "1"} for i, k in enumerate(keys)],
        "file_type": "naive", "chunk_size": chunk_size, "chunk_overlap": overlap,
        "length_function": "char", "need_chunk": True,
        "model_info":        {"model_id": os.environ.get("LLM_MODEL", "unset"),
                              "url": os.environ.get("LLM_URL", "http://127.0.0.1:18092/v1/chat/completions"),
                              "key": os.environ.get("LLM_KEY") or None},
        "embedding_model_info": {"model_id": os.environ.get("EMB_MODEL", "unset"),
                                 "url": os.environ.get("EMB_URL", "http://127.0.0.1:18090/v1/embeddings"),
                                 "key": os.environ.get("EMB_KEY") or None},
        "multi_model_info":  {"model_id": os.environ.get("MM_MODEL", "unset"),
                              "url": os.environ.get("MM_URL", "http://127.0.0.1:18092/v1/chat/completions"),
                              "key": os.environ.get("MM_KEY") or None},
    }
    req = urllib.request.Request(base.rstrip("/") + "/parse_without_indexing",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), time.perf_counter() - t0


# ---------------------------------------------------------------- 断言
CJK = lambda s: any("\u4e00" <= ch <= "\u9fff" for ch in s)

def assert_case(case, http, raw):
    checks, failed = [], []
    def chk(name, cond, note=""):
        checks.append({"check": name, "ok": bool(cond), "note": note})
        if not cond:
            failed.append(name)

    chk("http_200", http == 200, f"http={http}")
    try:
        data = json.loads(raw)
    except Exception:
        chk("json_parse", False, raw[:120]); return checks, failed, None

    if case.get("business_fail"):
        chk("business_flagged_failure", isinstance(data, dict) and data.get("success") is False, str(data)[:160])
        codes = [t.get("code") for t in (data.get("task_statuses") or [])] if isinstance(data, dict) else []
        chk("error_code_expected", case["expect_code"] in codes, f"codes={codes}")
        return checks, failed, data

    if not isinstance(data, list):
        chk("chunk_list", False, str(data)[:200]); return checks, failed, data

    chunks = data
    types = [c.get("metadata", {}).get("type") for c in chunks]
    text = "\n".join(c.get("page_content") or "" for c in chunks)
    chk("chunks_gt_0", len(chunks) > 0, f"chunks={len(chunks)}")
    if case.get("min_chunks"):
        chk("chunks_ge_expected", len(chunks) >= case["min_chunks"], f"chunks={len(chunks)}")
    if case.get("expect_image_chunks") is not None:
        # 廉价判别：图片块数必须等于输入图片数。
        # 少一条 = "拼接丢图"类（红线）；等于但文字变糙 = "覆盖退化"（D-1）
        n_img = sum(1 for t in types if t == "image")
        chk("image_chunks_match", n_img == case["expect_image_chunks"],
            f"expect={case['expect_image_chunks']} got={n_img}")
        # [R12-FIX-PARSE-05] 廉价截断判据：finish_reason='length' ⇒ VLM 文本不完整，不可作为完整转录源
        trunc = [c["metadata"].get("vlm_finish_reason") for c in chunks
                 if c.get("metadata", {}).get("type") == "image"
                 and c["metadata"].get("vlm_finish_reason") == "length"]
        chk("image_text_not_truncated", not trunc, f"truncated_chunks={len(trunc)}")
    if case.get("types"):
        for t in case["types"]:
            chk(f"has_type_{t}", t in types, f"types={sorted(set(types))}")
    if case.get("chinese"):
        chk("contains_chinese", CJK(text), repr(text[:60]))
    if case.get("min_chars"):
        chk("min_chars", len(text) >= case["min_chars"], f"chars={len(text)} expect>={case['min_chars']}")
    if case.get("min_chinese"):
        # 汉字数覆盖率：直读 docx 必须≈真值；若上游又退回"无字体 PDF"，这里会直接掉到 0
        n_cn = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        chk("min_chinese", n_cn >= case["min_chinese"], f"chinese={n_cn} expect>={case['min_chinese']}")
    for kw in case.get("text_kw", []):
        chk(f"text_contains_{kw}", kw in text, repr(text[:80]))
    if case.get("loc"):
        loc_ok = False
        for c in chunks:
            md = c.get("metadata", {})
            if md.get("offset") and md["offset"] != [[0, 0]]:
                loc_ok = True; break
            if md.get("page_number") and any(p not in (0, None) for p in md["page_number"]):
                loc_ok = True; break
            pos = md.get("position") or []
            if pos and any(p != [[0, 0]] * 4 for p in pos):
                loc_ok = True; break
        chk("locator_present", loc_ok)
    if case.get("table_md"):
        tbl = [c for c in chunks if c.get("metadata", {}).get("type") == "table"]
        chk("table_chunk_present", len(tbl) > 0)
        if tbl:
            body = tbl[0].get("page_content") or ""
            chk("table_is_markdown", "|" in body and "\n" in body, repr(body[:60]))
            for kw in case.get("table_kw", []):
                chk(f"table_contains_{kw}", kw in body)
    for kw in case.get("ocr_kw", []):
        chk(f"ocr_contains_{kw}", kw in text, repr(text[:80]))
    return checks, failed, data



WINDOW_TOOL = "/home/szf/data/dev/llmke-r12/platform/r12/models/measure_window.py"
WINDOW_PY = "/home/szf/data/dev/llmke-r12/platform/r12/venvs/models/bin/python"


def window_gate(max_load: float, mode: str = "functional") -> bool:
    """调用 model-ops 的 measure_window.py 判 GO/NO-GO（0=GO, 1=NO-GO, 2=不可达）。

    两种模式（model-ops 依据我给的"load 19.67 但 VLM cpu=0.00"反例新增）：
      - `capacity`  ：load1/load5 + 槽空闲 + 内存，三项全过才 GO → 耗时数据可作容量引用；
      - `functional`：只要槽空闲 + 内存够即可跑 → 断言/功能回归不该因邻居编译 Java 被跳过。
    判据：`needs_mm` 用例中，`vlm_heavy`（多图容量）走 capacity，其余走 functional。
    工具缺失时退回 load1/load5 双阈值并说明降级。
    """
    if os.path.exists(WINDOW_TOOL) and os.path.exists(WINDOW_PY):
        proc = subprocess.run([WINDOW_PY, WINDOW_TOOL, "--load", str(max_load), "--mode", mode],
                              capture_output=True, text=True, timeout=60)
        print(proc.stdout.rstrip())
        return proc.returncode == 0
    load1, load5, _ = os.getloadavg()
    print(f"[window] 未找到 measure_window.py，退回 load 闸门 load1={load1:.1f}/load5={load5:.1f} <= {max_load}")
    return load1 <= max_load and load5 <= max_load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("R12_PARSE_BASE", "http://127.0.0.1:12340"))
    ap.add_argument("--minio", default=os.environ.get("R12_MINIO", "127.0.0.1:19000"))
    ap.add_argument("--bucket", default=os.environ.get("R12_BUCKET", "r12-rag"))
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--with-stress", action="store_true", help="额外跑 C13 大表压力用例")
    ap.add_argument("--with-vlm-heavy", action="store_true", help="额外跑 C14/C15 多图用例（单次 500-700s，串行）")
    ap.add_argument("--max-load", type=float, default=float(os.environ.get("R12_MAX_LOAD", 15)),
                    help="load1 超过该值时跳过所有 VLM 用例（model-ops 实测 load≈30 时 VLM 只有 0.18 tok/s，会得到假超时）")
    args = ap.parse_args()

    os.environ.setdefault("R12_BUCKET", args.bucket)
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    gen_fixtures(Path(args.src))
    if not args.skip_upload:
        env = {}
        for line in (R12 / ".env").read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
        upload(args.bucket, args.minio,
               os.environ.get("MINIO_AK") or env.get("R12_MINIO_ACCESS_KEY", "r12minio"),
               os.environ.get("MINIO_SK") or env.get("R12_MINIO_SECRET_KEY", ""))

    has_llm = bool(os.environ.get("LLM_URL") and os.environ.get("LLM_MODEL"))
    has_mm = bool(os.environ.get("MM_URL") and os.environ.get("MM_MODEL"))

    rows, npass, nfail, nblock = [], 0, 0, 0
    for case in CASES:
        keys = case.get("files") or [case["file"]]
        cid = case["id"]
        if case.get("stress") and not args.with_stress:
            print(f"[{cid}] SKIP(未加 --with-stress): {case['desc']}")
            continue
        if case.get("vlm_heavy") and not args.with_vlm_heavy:
            print(f"[{cid}] SKIP(未加 --with-vlm-heavy): {case['desc']}")
            continue
        # [measure_window] VLM 用例的 GO/NO-GO 以 model-ops 的窗口工具为准：
        # 真因是「槽间争抢」（邻居的 prefill 会把本请求的生成饿到 0.73 tok/s），
        # 而 VLM 自己 --threads 20，用 load1 当闸门是循环论证；关键判据是 VLM 进程 cpu < 0.25 核（两槽都空闲）。
        gate_mode = "capacity" if case.get("vlm_heavy") else "functional"
        if case.get("needs_mm") and not window_gate(args.max_load, gate_mode):
            print(f"[{cid}] SKIP(窗口 NO-GO/{gate_mode}): 见上方 measure_window 输出——"
                  f"{'VLM 槽被占用或负载未达标（容量数据不可引用）' if gate_mode == 'capacity' else 'VLM 槽被占用/内存不足'}")
            continue
        if case.get("needs_mm") and not has_mm:
            status, note = "BLOCKED_FOR_MM", "未提供 MM_URL/MM_MODEL（VLM 未就绪，R12 已知限制）"
            rows.append(dict(**case, status=status, note=note)); nblock += 1
            print(f"[{cid}] {status}: {case['desc']} — {note}")
            continue
        if case.get("needs_llm") and not has_llm:
            status, note = "BLOCKED_FOR_LLM", "未提供 LLM_URL/LLM_MODEL（表格摘要强依赖 LLM）"
            rows.append(dict(**case, status=status, note=note)); nblock += 1
            print(f"[{cid}] {status}: {case['desc']} — {note}")
            continue

        load_before = os.getloadavg()[0]
        http, raw, dt = call(args.base, keys)
        load_after = os.getloadavg()[0]
        checks, failed, data = assert_case(case, http, raw)
        (outdir / f"{cid}-{keys[0]}.json").write_text(raw, encoding="utf-8")
        status = "PASS" if not failed else "FAIL"
        rows.append(dict(**case, status=status, http=http, sec=round(dt, 2),
                         load1_before=round(load_before, 2), load1_after=round(load_after, 2), checks=checks,
                         failed=failed, chunks=(len(data) if isinstance(data, list) else None),
                         first80=(data[0].get("page_content", "")[:80] if isinstance(data, list) and data else None)))
        if status == "PASS":
            npass += 1
        else:
            nfail += 1
        print(f"[{cid}] {status} http={http} {dt:.2f}s load1={load_before:.1f}->{load_after:.1f} chunks={rows[-1]['chunks']} {case['desc']}"
              + ("" if status == "PASS" else f"  failed={failed}"))

    (outdir / "result.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = [f"# R12 解析样本回归 {time.strftime('%Y-%m-%d %H:%M:%S')}",
               f"- base={args.base} bucket={args.bucket} llm={'yes' if has_llm else 'no'} mm={'yes' if has_mm else 'no'}",
               f"- PASS={npass} FAIL={nfail} BLOCKED={nblock}", ""]
    for r in rows:
        summary.append(f"| {r['id']} | {r['file'] if isinstance(r.get('file'), str) else '+'.join(r['files'])} | {r['status']} | "
                       f"{r.get('chunks')} | {r.get('sec')} | {r.get('load1_before')}->{r.get('load1_after')} | {r.get('first80')} |")
    (outdir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"\nPASS={npass} FAIL={nfail} BLOCKED={nblock}  输出目录 {outdir}")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
