import gc
import json
import os
import random
import re
import sys
import time
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Iterator

import numpy as np
import pdfplumber
import xgboost as xgb
from PIL import Image
from pypdf import PdfReader
from langchain_core.document_loaders import Blob

from log import logger
from server.nacos_utils import DocParseConfig
from server.utils import load_local_ocr
from .base_parser import BaseParser
from .utils import _PARSER_DICT, timer
from .. import rag_tokenizer
from ..output_object import ParsedTable, ParsedText, ParsedTextMetadata, ParsedTableMetadata
from ..utils import to_image
from ..vision import Recognizer, TableStructureRecognizer

_lock = Lock()


class _BaseParser(BaseParser):
    def __init__(self, garbage_file_name: str):
        ocr_model_dict = load_local_ocr()
        self.ocr = ocr_model_dict['ocr']
        if hasattr(self, 'model_type'):
            self.layouter = ocr_model_dict.get(self.model_type + '_layouter', None)
        else:
            self.layouter = ocr_model_dict.get('layouter', None)
        self.tbl_det = ocr_model_dict['tbl_det']
        self.updown_cnt_mdl = ocr_model_dict['updown_cnt_mdl']

        self.page_from = 0
        self.garbage_file_name = garbage_file_name
        self.page_images = []

        nacos_config = DocParseConfig().config
        if not os.path.exists(nacos_config['layout_garbage_path']):
            os.makedirs(nacos_config['layout_garbage_path'])
        self.layout_garbage_path = nacos_config['layout_garbage_path']

        self.file_path = None
        self.tables = []
        self.boxes = []
        self.pdf = None

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        self.file_path = blob.path
        self(
            blob,
            zoomin=3,
            from_page=0,
            to_page=sys.maxsize
        )

        # TODO 确保文字表格图片按照顺序输出

        yield from [ParsedText(
            page_content=box['text'],
            metadata=ParsedTextMetadata(
                source=self.file_path,
                file_path=self.file_path,
                page_number=[box['page_number']],
                position=[[
                    [box['x0'], box['top']],
                    [box['x1'], box['top']],
                    [box['x1'], box['bottom']],
                    [box['x0'], box['bottom']],
                ]],
                page_size=[box['page_size']]
            )
        ) for box in self.boxes]

        # TODO 处理图片 如果table是列表的话则意味着page content是图片 暂时忽略图片
        for (image, table), positions, page_size in self.tables:
            if isinstance(table, ParsedTable):
                if positions:
                    position = [
                        [
                            [position[1], position[3]],
                            [position[2], position[3]],
                            [position[2], position[4]],
                            [position[1], position[4]]
                        ] for position in positions
                    ]
                    page_number = [position[0] for position in positions]
                else:
                    position = []
                    page_number = []

                table.metadata = ParsedTableMetadata(
                    source=self.file_path,
                    file_path=self.file_path,
                    position=position,
                    page_number=page_number,
                    page_size=[page_size],
                    table_name=table.metadata.table_name
                )
                yield table

    def __char_width(self, c):
        return (c["x1"] - c["x0"]) // max(len(c["text"]), 1)

    def __height(self, c):
        return c["bottom"] - c["top"]

    def _x_dis(self, a, b):
        return min(abs(a["x1"] - b["x0"]), abs(a["x0"] - b["x1"]),
                   abs(a["x0"] + a["x1"] - b["x0"] - b["x1"]) / 2)

    def _y_dis(
            self, a, b):
        return (
                b["top"] + b["bottom"] - a["top"] - a["bottom"]) / 2

    def _match_proj(self, b):
        proj_patt = [
            r"第[零一二三四五六七八九十百]+章",
            r"第[零一二三四五六七八九十百]+[条节]",
            r"[零一二三四五六七八九十百]+[、是 　]",
            r"[\(（][零一二三四五六七八九十百]+[）\)]",
            r"[\(（][0-9]+[）\)]",
            r"[0-9]+(、|\.[　 ]|）|\.[^0-9./a-zA-Z_%><-]{4,})",
            r"[0-9]+\.[0-9.]+(、|\.[ 　])",
            r"[⚫•➢①② ]",
        ]
        return any([re.match(p, b["text"]) for p in proj_patt])

    def _updown_concat_features(self, up, down):
        w = max(self.__char_width(up), self.__char_width(down))
        h = max(self.__height(up), self.__height(down))
        y_dis = self._y_dis(up, down)
        LEN = 6
        tks_down = rag_tokenizer.tokenize(down["text"][:LEN]).split(" ")
        tks_up = rag_tokenizer.tokenize(up["text"][-LEN:]).split(" ")
        tks_all = up["text"][-LEN:].strip() \
                  + (" " if re.match(r"[a-zA-Z0-9]+",
                                     up["text"][-1] + down["text"][0]) else "") \
                  + down["text"][:LEN].strip()
        tks_all = rag_tokenizer.tokenize(tks_all).split(" ")
        fea = [
            up.get("R", -1) == down.get("R", -1),
            y_dis / h,
            down["page_number"] - up["page_number"],
            up["layout_type"] == down["layout_type"],
            up["layout_type"] == "text",
            down["layout_type"] == "text",
            up["layout_type"] == "table",
            down["layout_type"] == "table",
            True if re.search(
                r"([。？！；!?;+)）]|[a-z]\.)$",
                up["text"]) else False,
            True if re.search(r"[，：‘“、0-9（+-]$", up["text"]) else False,
            True if re.search(
                r"(^.?[/,?;:\]，。；：’”？！》】）-])",
                down["text"]) else False,
            True if re.match(r"[(（][^()（）]+[）)]$", up["text"]) else False,
            True if re.search(r"[，,][^。.]+$", up["text"]) else False,
            True if re.search(r"[，,][^。.]+$", up["text"]) else False,
            True if re.search(r"[(（][^)）]+$", up["text"])
                    and re.search(r"[)）]", down["text"]) else False,
            self._match_proj(down),
            True if re.match(r"[A-Z]", down["text"]) else False,
            True if re.match(r"[A-Z]", up["text"][-1]) else False,
            True if re.match(r"[a-z0-9]", up["text"][-1]) else False,
            True if re.match(r"[0-9.%,-]+$", down["text"]) else False,
            up["text"].strip()[-2:] == down["text"].strip()[-2:] if len(up["text"].strip()
                                                                        ) > 1 and len(
                down["text"].strip()) > 1 else False,
            up["x0"] > down["x1"],
            abs(self.__height(up) - self.__height(down)) / min(self.__height(up),
                                                               self.__height(down)),
            self._x_dis(up, down) / max(w, 0.000001),
            (len(up["text"]) - len(down["text"])) /
            max(len(up["text"]), len(down["text"])),
            len(tks_all) - len(tks_up) - len(tks_down),
            len(tks_down) - len(tks_up),
            tks_down[-1] == tks_up[-1],
            max(down["in_row"], up["in_row"]),
            abs(down["in_row"] - up["in_row"]),
            len(tks_down) == 1 and rag_tokenizer.tag(tks_down[0]).find("n") >= 0,
            len(tks_up) == 1 and rag_tokenizer.tag(tks_up[0]).find("n") >= 0
        ]
        return fea

    @staticmethod
    def sort_X_by_page(arr, threashold):
        # sort using y1 first and then x1
        arr = sorted(arr, key=lambda r: (r["page_number"], r["x0"], r["top"]))
        for i in range(len(arr) - 1):
            for j in range(i, -1, -1):
                # restore the order using th
                if abs(arr[j + 1]["x0"] - arr[j]["x0"]) < threashold \
                        and arr[j + 1]["top"] < arr[j]["top"] \
                        and arr[j + 1]["page_number"] == arr[j]["page_number"]:
                    tmp = arr[j]
                    arr[j] = arr[j + 1]
                    arr[j + 1] = tmp
        return arr

    def _has_color(self, o):
        if o.get("ncs", "") == "DeviceGray":
            if o["stroking_color"] and o["stroking_color"][0] == 1 and o["non_stroking_color"] and \
                    o["non_stroking_color"][0] == 1:
                if re.match(r"[a-zT_\[\]()-]+", o.get("text", "")):
                    return False
        return True

    def _table_transformer_job(self, ZM):
        logger.info("Table processing...")
        images, position, crops = [], [], []
        table_counts = [0]
        MARGIN = 10
        tb_cpns = []
        assert len(self.page_layout) == len(self.pdf.pages)
        for page_index, tables in enumerate(self.page_layout):  # for page
            tables = [f for f in tables if f["type"] == "table"]
            table_counts.append(len(tables))
            if not tables:
                continue
            for table in tables:  # for table
                left, top, right, bott = table["x0"] - MARGIN, table["top"] - MARGIN, \
                                         table["x1"] + MARGIN, table["bottom"] + MARGIN
                left *= ZM
                top *= ZM
                right *= ZM
                bott *= ZM
                position.append((left, top))
                images.append(self.pdf.pages[page_index])
                crops.append((left, top, right, bott))

        assert len(self.pdf.pages) == len(table_counts) - 1
        if not images:
            return
        recos = self.tbl_det(images, crops=crops)
        images.clear()
        table_counts = np.cumsum(table_counts)
        for i in range(len(table_counts) - 1):  # for page
            pg = []
            for j, tb_items in enumerate(
                    recos[table_counts[i]: table_counts[i + 1]]):  # for table
                poss = position[table_counts[i]: table_counts[i + 1]]
                for it in tb_items:  # for table components
                    it["x0"] = (it["x0"] + poss[j][0])
                    it["x1"] = (it["x1"] + poss[j][0])
                    it["top"] = (it["top"] + poss[j][1])
                    it["bottom"] = (it["bottom"] + poss[j][1])
                    for n in ["x0", "x1", "top", "bottom"]:
                        it[n] /= ZM
                    it["top"] += self.page_cum_height[i]
                    it["bottom"] += self.page_cum_height[i]
                    it["pn"] = i
                    it["layoutno"] = j
                    pg.append(it)
            tb_cpns.extend(pg)

        def gather(kwd, fzy=10, ption=0.6):
            eles = Recognizer.sort_Y_firstly(
                [r for r in tb_cpns if re.match(kwd, r["label"])], fzy)
            eles = Recognizer.layouts_cleanup(self.boxes, eles, 5, ption)
            return Recognizer.sort_Y_firstly(eles, 0)

        # add R,H,C,SP tag to boxes within table layout
        headers = gather(r".*header$")
        rows = gather(r".* (row|header)")
        spans = gather(r".*spanning")
        clmns = sorted([r for r in tb_cpns if re.match(
            r"table column$", r["label"])], key=lambda x: (x["pn"], x["layoutno"], x["x0"]))
        clmns = Recognizer.layouts_cleanup(self.boxes, clmns, 5, 0.5)
        for b in self.boxes:
            if b.get("layout_type", "") != "table":
                continue
            ii = Recognizer.find_overlapped_with_threashold(b, rows, thr=0.3)
            if ii is not None:
                b["R"] = ii
                b["R_top"] = rows[ii]["top"]
                b["R_bott"] = rows[ii]["bottom"]

            ii = Recognizer.find_overlapped_with_threashold(
                b, headers, thr=0.3)
            if ii is not None:
                b["H_top"] = headers[ii]["top"]
                b["H_bott"] = headers[ii]["bottom"]
                b["H_left"] = headers[ii]["x0"]
                b["H_right"] = headers[ii]["x1"]
                b["H"] = ii

            ii = Recognizer.find_horizontally_tightest_fit(b, clmns)
            if ii is not None:
                b["C"] = ii
                b["C_left"] = clmns[ii]["x0"]
                b["C_right"] = clmns[ii]["x1"]

            ii = Recognizer.find_overlapped_with_threashold(b, spans, thr=0.3)
            if ii is not None:
                b["H_top"] = spans[ii]["top"]
                b["H_bott"] = spans[ii]["bottom"]
                b["H_left"] = spans[ii]["x0"]
                b["H_right"] = spans[ii]["x1"]
                b["SP"] = ii

    def __ocr(self, pagenum, img, chars, ZM=3):
        bxs = self.ocr.detect(np.array(img))
        if not bxs:
            self.boxes.append([])
            return
        bxs = [(line[0], line[1][0]) for line in bxs]
        bxs = Recognizer.sort_Y_firstly(
            [{"x0": b[0][0] / ZM, "x1": b[1][0] / ZM,
              "top": b[0][1] / ZM, "text": "", "txt": t,
              "bottom": b[-1][1] / ZM,
              "page_number": pagenum} for b, t in bxs if b[0][0] <= b[1][0] and b[0][1] <= b[-1][1]],
            self.mean_height[-1] / 3
        )

        # merge chars in the same rect
        for c in Recognizer.sort_X_firstly(
                chars, self.mean_width[pagenum - 1] // 4):
            ii = Recognizer.find_overlapped(c, bxs)
            if ii is None:
                self.lefted_chars.append(c)
                continue
            ch = c["bottom"] - c["top"]
            bh = bxs[ii]["bottom"] - bxs[ii]["top"]
            if abs(ch - bh) / max(ch, bh) >= 0.7 and c["text"] != ' ':
                self.lefted_chars.append(c)
                continue
            if c["text"] == " " and bxs[ii]["text"]:
                if re.match(r"[0-9a-zA-Z,.?;:!%]", bxs[ii]["text"][-1]):
                    bxs[ii]["text"] += " "
            else:
                bxs[ii]["text"] += c["text"]

        start = time.time()
        for b in bxs:
            b["x0"] *= ZM
            b["x1"] *= ZM
            b["top"] *= ZM
            b["bottom"] *= ZM
            if not b["text"]:
                left, right, top, bott = b["x0"], b["x1"], b["top"], b["bottom"]
                b["text"] = self.ocr.recognize(np.array(img),
                                               np.array([[left, top], [right, top], [right, bott], [left, bott]],
                                                        dtype=np.float32))
            b['page_size'] = list(img.size)
            del b["txt"]
        logger.debug(f'recognize elapsed: {time.time() - start}')
        bxs = [b for b in bxs if b["text"]]
        if self.mean_height[-1] == 0:
            self.mean_height[-1] = np.median([b["bottom"] - b["top"]
                                              for b in bxs])
        self.boxes.append(bxs)

    def _layouts_rec(self, ZM, drop=False):
        assert len(self.pdf.pages) == len(self.boxes)
        self.boxes, self.page_layout = self.layouter(self.pdf.pages, self.boxes, scale_factor=ZM, drop=drop)
        if self.layouter.garbage:
            with open(Path(self.layout_garbage_path) / (self.garbage_file_name + '.json'), 'w') as f:
                json.dump(self.layouter.garbage, f, ensure_ascii=False, indent=4)
        # cumlative Y
        # TODO 需要停止修改坐标
        # for i in range(len(self.boxes)):
        #     self.boxes[i]["top"] += \
        #         self.page_cum_height[self.boxes[i]["page_number"] - 1]
        #     self.boxes[i]["bottom"] += \
        #         self.page_cum_height[self.boxes[i]["page_number"] - 1]

    def _text_merge(self):
        # merge adjusted boxes
        bxs = self.boxes

        def end_with(b, txt):
            txt = txt.strip()
            tt = b.get("text", "").strip()
            return tt and tt.find(txt) == len(tt) - len(txt)

        def start_with(b, txts):
            tt = b.get("text", "").strip()
            return tt and any([tt.find(t.strip()) == 0 for t in txts])

        # horizontally merge adjacent box with the same layout
        i = 0
        while i < len(bxs) - 1:
            b = bxs[i]
            b_ = bxs[i + 1]
            if b.get("layoutno", "0") != b_.get("layoutno", "1") or b.get("layout_type", "") in ["table", "figure",
                                                                                                 "equation"]:
                i += 1
                continue
            if abs(self._y_dis(b, b_)
                   ) < self.mean_height[bxs[i]["page_number"] - 1] / 3:
                # merge
                bxs[i]["x1"] = b_["x1"]
                bxs[i]["top"] = (b["top"] + b_["top"]) / 2
                bxs[i]["bottom"] = (b["bottom"] + b_["bottom"]) / 2
                bxs[i]["text"] += b_["text"]
                bxs.pop(i + 1)
                continue
            i += 1

        self.boxes = bxs

    def _naive_vertical_merge(self):
        bxs = Recognizer.sort_Y_firstly(
            self.boxes, np.median(
                self.mean_height) / 3)
        i = 0
        while i + 1 < len(bxs):
            b = bxs[i]
            b_ = bxs[i + 1]
            if b["page_number"] < b_["page_number"] and re.match(
                    r"[0-9 •一—-]+$", b["text"]):
                bxs.pop(i)
                continue
            if not b["text"].strip():
                bxs.pop(i)
                continue
            concatting_feats = [
                b["text"].strip()[-1] in ",;:'\"，、‘“；：-",
                len(b["text"].strip()) > 1 and b["text"].strip(
                )[-2] in ",;:'\"，‘“、；：",
                b["text"].strip()[0] in "。；？！?”）),，、：",
            ]
            # features for not concating
            feats = [
                b.get("layoutno", 0) != b.get("layoutno", 0),
                b["text"].strip()[-1] in "。？！?",
                self.is_english and b["text"].strip()[-1] in ".!?",
                b["page_number"] == b_["page_number"] and b_["top"] -
                b["bottom"] > self.mean_height[b["page_number"] - 1] * 1.5,
                b["page_number"] < b_["page_number"] and abs(
                    b["x0"] - b_["x0"]) > self.mean_width[b["page_number"] - 1] * 4,
            ]
            # split features
            detach_feats = [b["x1"] < b_["x0"],
                            b["x0"] > b_["x1"]]
            if (any(feats) and not any(concatting_feats)) or any(detach_feats):
                print(
                    b["text"],
                    b_["text"],
                    any(feats),
                    any(concatting_feats),
                    any(detach_feats))
                i += 1
                continue
            # merge up and down
            b["bottom"] = b_["bottom"]
            b["text"] += b_["text"]
            b["x0"] = min(b["x0"], b_["x0"])
            b["x1"] = max(b["x1"], b_["x1"])
            bxs.pop(i + 1)
        self.boxes = bxs

    def _concat_downward(self, concat_between_pages=True):
        # count boxes in the same row as a feature
        for index in range(len(self.boxes)):
            mean_height = self.mean_height[self.boxes[index]["page_number"] - 1]
            self.boxes[index]["in_row"] = 0
            j = max(0, index - 12)
            while j < min(index + 12, len(self.boxes)):
                if j == index:
                    j += 1
                    continue
                ydis = self._y_dis(self.boxes[index], self.boxes[j]) / mean_height
                if abs(ydis) < 1:
                    self.boxes[index]["in_row"] += 1
                elif ydis > 0:
                    break
                j += 1

        # concat between rows
        boxes = deepcopy(self.boxes)
        blocks = []
        while boxes:
            chunks = []

            def dfs(up, dp):
                chunks.append(up)
                i = dp
                while i < min(dp + 12, len(boxes)):
                    ydis = self._y_dis(up, boxes[i])
                    smpg = up["page_number"] == boxes[i]["page_number"]
                    mh = self.mean_height[up["page_number"] - 1]
                    mw = self.mean_width[up["page_number"] - 1]
                    if smpg and ydis > mh * 4:
                        break
                    if not smpg and ydis > mh * 16:
                        break
                    down = boxes[i]
                    if not concat_between_pages and down["page_number"] > up["page_number"]:
                        break

                    if up.get("R", "") != down.get(
                            "R", "") and up["text"][-1] != "，":
                        i += 1
                        continue

                    if re.match(r"[0-9]{2,3}/[0-9]{3}$", up["text"]) \
                            or re.match(r"[0-9]{2,3}/[0-9]{3}$", down["text"]) \
                            or not down["text"].strip():
                        i += 1
                        continue

                    if not down["text"].strip():
                        i += 1
                        continue

                    if up["x1"] < down["x0"] - 10 * \
                            mw or up["x0"] > down["x1"] + 10 * mw:
                        i += 1
                        continue

                    if i - dp < 5 and up.get("layout_type") == "text":
                        if up.get("layoutno", "1") == down.get(
                                "layoutno", "2"):
                            dfs(down, i + 1)
                            boxes.pop(i)
                            return
                        i += 1
                        continue

                    fea = self._updown_concat_features(up, down)
                    if self.updown_cnt_mdl.predict(
                            xgb.DMatrix([fea]))[0] <= 0.5:
                        i += 1
                        continue
                    dfs(down, i + 1)
                    boxes.pop(i)
                    return

            dfs(boxes[0], 1)
            boxes.pop(0)
            if chunks:
                blocks.append(chunks)

        # concat within each block
        boxes = []
        for b in blocks:
            if len(b) == 1:
                boxes.append(b[0])
                continue
            t = b[0]
            for c in b[1:]:
                t["text"] = t["text"].strip()
                c["text"] = c["text"].strip()
                if not c["text"]:
                    continue
                if t["text"] and re.match(
                        r"[0-9.a-zA-Z]+$", t["text"][-1] + c["text"][-1]):
                    t["text"] += " "
                t["text"] += c["text"]
                t["x0"] = min(t["x0"], c["x0"])
                t["x1"] = max(t["x1"], c["x1"])
                t["page_number"] = min(t["page_number"], c["page_number"])
                t["bottom"] = c["bottom"]
                if not t["layout_type"] \
                        and c["layout_type"]:
                    t["layout_type"] = c["layout_type"]
            boxes.append(t)

        self.boxes = Recognizer.sort_Y_firstly(boxes, 0)

    def _filter_forpages(self):
        if not self.boxes:
            return
        findit = False
        i = 0
        while i < len(self.boxes):
            if not re.match(r"(contents|目录|目次|table of contents|致谢|acknowledge)$",
                            re.sub(r"([ \u3000])+", "", self.boxes[i]["text"].lower())):
                i += 1
                continue
            findit = True
            eng = re.match(
                r"[0-9a-zA-Z :'.-]{5,}",
                self.boxes[i]["text"].strip())
            prefix = None
            while not prefix:
                self.boxes.pop(i)
                if i >= len(self.boxes):
                    break
                prefix = self.boxes[i]["text"].strip()[:3] if not eng else " ".join(
                    self.boxes[i]["text"].strip().split(" ")[:2])
            self.boxes.pop(i)
            if i >= len(self.boxes) or not prefix:
                break
            for j in range(i, min(i + 128, len(self.boxes))):
                if not re.match(prefix, self.boxes[j]["text"]):
                    continue
                for k in range(i, j):
                    self.boxes.pop(i)
                break
        if findit:
            return

        page_dirty = [0] * len(self.pdf.pages)
        for b in self.boxes:
            if re.search(r"(··)", b["text"]):
                page_dirty[b["page_number"] - 1] += 1
        page_dirty = set([i + 1 for i, t in enumerate(page_dirty) if t > 3])
        if not page_dirty:
            return
        i = 0
        while i < len(self.boxes):
            if self.boxes[i]["page_number"] in page_dirty:
                self.boxes.pop(i)
                continue
            i += 1

    def _merge_with_same_bullet(self):
        i = 0
        while i + 1 < len(self.boxes):
            b = self.boxes[i]
            b_ = self.boxes[i + 1]
            if not b["text"].strip():
                self.boxes.pop(i)
                continue
            if not b_["text"].strip():
                self.boxes.pop(i + 1)
                continue

            if b["text"].strip()[0] != b_["text"].strip()[0] \
                    or b["text"].strip()[0].lower() in set("qwertyuopasdfghjklzxcvbnm") \
                    or rag_tokenizer.is_chinese(b["text"].strip()[0]) \
                    or b["top"] > b_["bottom"]:
                i += 1
                continue
            b_["text"] = b["text"] + "\n" + b_["text"]
            b_["x0"] = min(b["x0"], b_["x0"])
            b_["x1"] = max(b["x1"], b_["x1"])
            b_["top"] = b["top"]
            self.boxes.pop(i)

    def _extract_table_figure(self, need_image, ZM,
                              return_html, need_position):
        tables = {}
        figures = {}
        # extract figure and table boxes
        i = 0
        lst_lout_no = ""
        nomerge_lout_no = []
        while i < len(self.boxes):
            if "layoutno" not in self.boxes[i]:
                i += 1
                continue
            lout_no = str(self.boxes[i]["page_number"]) + \
                      "-" + str(self.boxes[i]["layoutno"])
            if TableStructureRecognizer.is_caption(self.boxes[i]) or self.boxes[i]["layout_type"] in ["table caption",
                                                                                                      "title",
                                                                                                      "figure caption",
                                                                                                      "reference"]:
                nomerge_lout_no.append(lst_lout_no)
            if self.boxes[i]["layout_type"] == "table":
                if re.match(r"(数据|资料|图表)*来源[:： ]", self.boxes[i]["text"]):
                    self.boxes.pop(i)
                    continue
                if lout_no not in tables:
                    tables[lout_no] = []
                tables[lout_no].append(self.boxes[i])
                self.boxes.pop(i)
                lst_lout_no = lout_no
                continue
            if need_image and self.boxes[i]["layout_type"] == "figure":
                if re.match(r"(数据|资料|图表)*来源[:： ]", self.boxes[i]["text"]):
                    self.boxes.pop(i)
                    continue
                if lout_no not in figures:
                    figures[lout_no] = []
                figures[lout_no].append(self.boxes[i])
                self.boxes.pop(i)
                lst_lout_no = lout_no
                continue
            i += 1

        # merge table on different pages
        nomerge_lout_no = set(nomerge_lout_no)
        tbls = sorted([(k, bxs) for k, bxs in tables.items()],
                      key=lambda x: (x[1][0]["top"], x[1][0]["x0"]))

        i = len(tbls) - 1
        while i - 1 >= 0:
            k0, bxs0 = tbls[i - 1]
            k, bxs = tbls[i]
            i -= 1
            if k0 in nomerge_lout_no:
                continue
            if bxs[0]["page_number"] == bxs0[0]["page_number"]:
                continue
            if bxs[0]["page_number"] - bxs0[0]["page_number"] > 1:
                continue
            mh = self.mean_height[bxs[0]["page_number"] - 1]
            if self._y_dis(bxs0[-1], bxs[0]) > mh * 23:
                continue
            tables[k0].extend(tables[k])
            del tables[k]

        def x_overlapped(a, b):
            return not any([a["x1"] < b["x0"], a["x0"] > b["x1"]])

        # find captions and pop out
        i = 0
        while i < len(self.boxes):
            c = self.boxes[i]
            # mh = self.mean_height[c["page_number"]-1]
            if not TableStructureRecognizer.is_caption(c):
                i += 1
                continue

            # find the nearest layouts
            def nearest(tbls):
                nonlocal c
                mink = ""
                minv = 1000000000
                for k, bxs in tbls.items():
                    for b in bxs:
                        if b.get("layout_type", "").find("caption") >= 0:
                            continue
                        y_dis = self._y_dis(c, b)
                        x_dis = self._x_dis(
                            c, b) if not x_overlapped(
                            c, b) else 0
                        dis = y_dis * y_dis + x_dis * x_dis
                        if dis < minv:
                            mink = k
                            minv = dis
                return mink, minv

            tk, tv = nearest(tables)
            fk, fv = nearest(figures)
            # if min(tv, fv) > 2000:
            #    i += 1
            #    continue
            if tv < fv and tk:
                tables[tk].insert(0, c)
                logger.debug(
                    "TABLE:" +
                    self.boxes[i]["text"] +
                    "; Cap: " +
                    tk)
            elif fk:
                figures[fk].insert(0, c)
                logger.debug(
                    "FIGURE:" +
                    self.boxes[i]["text"] +
                    "; Cap: " +
                    tk)
            self.boxes.pop(i)

        res = []
        positions = []
        page_sizes = []

        def cropout(bxs, ltype, poss):
            nonlocal ZM
            pn = set([b["page_number"] - 1 for b in bxs])
            if len(pn) < 2:
                pn = list(pn)[0]
                ht = self.page_cum_height[pn]
                b = {
                    "x0": np.min([b["x0"] for b in bxs]),
                    "top": np.min([b["top"] for b in bxs]) - ht,
                    "x1": np.max([b["x1"] for b in bxs]),
                    "bottom": np.max([b["bottom"] for b in bxs]) - ht
                }
                louts = [l for l in self.page_layout[pn] if l["type"] == ltype]
                ii = Recognizer.find_overlapped(b, louts, naive=True)
                if ii is not None:
                    b = louts[ii]
                else:
                    logger.warning(
                        f"Missing layout match: {pn + 1},%s" %
                        (bxs[0].get(
                            "layoutno", "")))

                left, top, right, bott = b["x0"], b["top"], b["x1"], b["bottom"]
                if right < left: right = left + 1
                poss.append((pn + self.page_from, left, right, top, bott))
                page_image = to_image(self.pdf.pages[pn], resolution=72 * ZM).annotated
                return page_image.crop((left * ZM, top * ZM, right * ZM, bott * ZM))
            pn = {}
            for b in bxs:
                p = b["page_number"] - 1
                if p not in pn:
                    pn[p] = []
                pn[p].append(b)
            pn = sorted(pn.items(), key=lambda x: x[0])
            imgs = [cropout(arr, ltype, poss) for p, arr in pn]
            pic = Image.new("RGB",
                            (int(np.max([i.size[0] for i in imgs])),
                             int(np.sum([m.size[1] for m in imgs]))),
                            (245, 245, 245))
            height = 0
            for img in imgs:
                pic.paste(img, (0, int(height)))
                height += img.size[1]
            return pic

        # crop figure out and add caption
        for k, bxs in figures.items():
            txt = "\n".join([b["text"] for b in bxs])
            if not txt:
                continue

            poss = []
            res.append(
                (cropout(
                    bxs,
                    "figure", poss),
                 [txt]))
            positions.append(poss)

        for k, bxs in tables.items():
            if not bxs:
                continue
            bxs = Recognizer.sort_Y_firstly(bxs, np.mean(
                [(b["bottom"] - b["top"]) / 2 for b in bxs]))
            poss = []
            res.append((
                cropout(bxs, "table", poss),
                self.tbl_det.construct_table(bxs, html=return_html, is_english=self.is_english)
            ))
            positions.append(poss)
            page_sizes.append(bxs[0]['page_size'])

        assert len(positions) == len(res)

        if need_position:
            return list(zip(res, positions, page_sizes))
        return res

    def proj_match(self, line):
        if len(line) <= 2:
            return
        if re.match(r"[0-9 ().,%+/-]+$", line):
            return False
        for p, j in [
            (r"第[零一二三四五六七八九十百]+章", 1),
            (r"第[零一二三四五六七八九十百]+[条节]", 2),
            (r"[零一二三四五六七八九十百]+[、 　]", 3),
            (r"[\(（][零一二三四五六七八九十百]+[）\)]", 4),
            (r"[0-9]+(、|\.[　 ]|\.[^0-9])", 5),
            (r"[0-9]+\.[0-9]+(、|[. 　]|[^0-9])", 6),
            (r"[0-9]+\.[0-9]+\.[0-9]+(、|[ 　]|[^0-9])", 7),
            (r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+(、|[ 　]|[^0-9])", 8),
            (r".{,48}[：:?？]$", 9),
            (r"[0-9]+）", 10),
            (r"[\(（][0-9]+[）\)]", 11),
            (r"[零一二三四五六七八九十百]+是", 12),
            (r"[⚫•➢✓]", 12)
        ]:
            if re.match(p, line):
                return j
        return

    @staticmethod
    def total_page_number(fnm, binary=None):
        try:
            pdf = pdfplumber.open(
                fnm) if not binary else pdfplumber.open(BytesIO(binary))
            return len(pdf.pages)
        except Exception as e:
            logger.error(str(e))

    @timer
    def __images__(self, file: str | Blob, zoomin=3, from_page=0, to_page=sys.maxsize):
        logger.info("OCR is running...")
        self.lefted_chars = []
        self.mean_height = []
        self.mean_width = []
        self.garbages = {}
        self.page_cum_height = [0]
        self.page_layout = []
        self.page_from = from_page
        self.pdf = pdfplumber.open(file) if isinstance(file, str) else pdfplumber.open(BytesIO(file.as_bytes()))
        self.page_chars = [[c for c in page.chars if self._has_color(c)] for page in self.pdf.pages[from_page:to_page]]
        self.total_page = len(self.pdf.pages)

        self.outlines = []
        try:
            pdf_reader = PdfReader(file if isinstance(file, str) else BytesIO(file.as_bytes()))
            outlines = pdf_reader.outline

            def dfs(arr, depth):
                for a in arr:
                    if isinstance(a, dict):
                        self.outlines.append((a["/Title"], depth))
                        continue
                    dfs(a, depth + 1)

            dfs(outlines, 0)
        except Exception as e:
            logger.warning(f"Outlines exception: {e}")
        if not self.outlines:
            logger.warning(f"Miss outlines")

        logger.info("Images converted.")
        self.is_english = [re.search(r"[a-zA-Z0-9,/¸;:'\[\]()!@#$%^&*\"?<>._-]{30,}", "".join(
            random.choices([c["text"] for c in self.page_chars[i]], k=min(100, len(self.page_chars[i]))))) for i in
                           range(len(self.page_chars))]
        if sum([1 if e else 0 for e in self.is_english]) > len(self.pdf.pages[from_page:to_page]) / 2:
            self.is_english = True
        else:
            self.is_english = False
        self.is_english = False

        start_ocr_time = time.time()
        for i, page in enumerate(self.pdf.pages[from_page:to_page]):
            img = to_image(page, resolution=72 * zoomin).annotated
            chars = self.page_chars[i] if not self.is_english else []
            self.mean_height.append(
                np.median(sorted([c["height"] for c in chars])) if chars else 0
            )
            self.mean_width.append(
                np.median(sorted([c["width"] for c in chars])) if chars else 8
            )
            self.page_cum_height.append(img.size[1] / zoomin)
            j = 0
            while j + 1 < len(chars):
                if chars[j]["text"] and chars[j + 1]["text"] \
                        and re.match(r"[0-9a-zA-Z,.:;!%]+", chars[j]["text"] + chars[j + 1]["text"]) \
                        and chars[j + 1]["x0"] - chars[j]["x1"] >= min(chars[j + 1]["width"],
                                                                       chars[j]["width"]) / 2:
                    chars[j]["text"] += " "
                j += 1

            self.__ocr(i + 1, img, chars, zoomin)
            chars.clear()
            del chars

            file_path = file if isinstance(file, str) else file.path
            average_time = (time.time() - start_ocr_time) / (i + 1)
            left_time = (self.total_page - i - 1) * average_time
            logger.info(f'{file_path} processing in ocr: {(i + 1) / self.total_page * 100:.2f}%, '
                        f'{i + 1}/{self.total_page}, '
                        f'{average_time:.2f}s/item, '
                        f'estimate {left_time:.2f}s left.')

            img.close()
            del img

        if not self.is_english and not any(self.page_chars) and self.boxes:
            bxes = [b for bxs in self.boxes for b in bxs]
            self.is_english = re.search(r"[\na-zA-Z0-9,/¸;:'\[\]()!@#$%^&*\"?<>._-]{30,}",
                                        "".join([b["text"] for b in random.choices(bxes, k=min(30, len(bxes)))]))
        self.page_chars.clear()
        logger.info(f"Is it English: {self.is_english}")

        self.page_cum_height = np.cumsum(self.page_cum_height)
        assert len(self.page_cum_height) == len(self.pdf.pages) + 1
        logger.info('OCR finished')

    def __call__(self, file, zoomin=3, from_page=0, to_page=sys.maxsize):
        raise NotImplemented('不可以使用base parser')

    def crop(self, text, ZM=3, need_position=False):
        imgs = []
        poss = []
        for tag in re.findall(r"@@[0-9-]+\t[0-9.\t]+##", text):
            pn, left, right, top, bottom = tag.strip(
                "#").strip("@").split("\t")
            left, right, top, bottom = float(left), float(
                right), float(top), float(bottom)
            poss.append(([int(p) - 1 for p in pn.split("-")],
                         left, right, top, bottom))
        if not poss:
            if need_position:
                return None, None
            return

        max_width = max(
            np.max([right - left for (_, left, right, _, _) in poss]), 6)
        GAP = 6
        pos = poss[0]
        poss.insert(0, ([pos[0][0]], pos[1], pos[2], max(
            0, pos[3] - 120), max(pos[3] - GAP, 0)))
        pos = poss[-1]
        page_image = to_image(self.pdf.pages[pos[0][-1]], resolution=72 * ZM).annotated
        poss.append(([pos[0][-1]], pos[1], pos[2], min(page_image.size[1] / ZM, pos[4] + GAP),
                     min(page_image.size[1] / ZM, pos[4] + 120)))
        page_image.close()
        del page_image

        positions = []
        for ii, (pns, left, right, top, bottom) in enumerate(poss):
            right = left + max_width
            bottom *= ZM
            for pn in pns[1:]:
                page_image = to_image(self.pdf.pages[pn - 1], resolution=72 * ZM).annotated
                bottom += page_image.size[1]
                page_image.close()
                del page_image
            page_image = to_image(self.pdf.pages[pns[0]], resolution=72 * ZM).annotated
            imgs.append(
                page_image.crop((
                    left * ZM,
                    top * ZM,
                    right * ZM,
                    min(bottom, page_image.size[1])
                ))
            )
            if 0 < ii < len(poss) - 1:
                positions.append((pns[0] + self.page_from, left, right, top, min(
                    bottom, page_image.size[1]) / ZM))
            bottom -= page_image.size[1]
            page_image.close()
            del page_image
            for pn in pns[1:]:
                page_image = to_image(self.pdf.pages[pn], resolution=72 * ZM).annotated
                imgs.append(
                    page_image.crop((left * ZM, 0,
                                               right * ZM,
                                               min(bottom,
                                                   page_image.size[1])
                                               ))
                )
                if 0 < ii < len(poss) - 1:
                    positions.append((pn + self.page_from, left, right, 0, min(
                        bottom, page_image.size[1]) / ZM))
                bottom -= page_image.size[1]
                page_image.close()
                del page_image

        if not imgs:
            if need_position:
                return None, None
            return
        height = 0
        for img in imgs:
            height += img.size[1] + GAP
        height = int(height)
        width = int(np.max([i.size[0] for i in imgs]))
        pic = Image.new("RGB",
                        (width, height),
                        (245, 245, 245))
        height = 0
        for ii, img in enumerate(imgs):
            if ii == 0 or ii + 1 == len(imgs):
                img = img.convert('RGBA')
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                overlay.putalpha(128)
                img = Image.alpha_composite(img, overlay).convert("RGB")
            pic.paste(img, (0, int(height)))
            height += img.size[1] + GAP

        if need_position:
            return pic, positions
        return pic

    def get_position(self, bx, ZM):
        poss = []
        pn = bx["page_number"]
        top = bx["top"] - self.page_cum_height[pn - 1]
        bott = bx["bottom"] - self.page_cum_height[pn - 1]
        page_image = to_image(self.pdf.pages[pn - 1], resolution=72 * ZM).annotated
        poss.append((pn, bx["x0"], bx["x1"], top, min(
            bott, page_image.size[1] / ZM)))
        while bott * ZM > page_image.size[1]:
            bott -= page_image.size[1] / ZM
            top = 0
            pn += 1
            poss.append((pn, bx["x0"], bx["x1"], top, min(
                bott, page_image.size[1] / ZM)))
        page_image.close()
        del page_image
        return poss


class _NaiveParser(_BaseParser):
    def __call__(self, file, from_page=0, to_page=sys.maxsize, zoomin=3):
        self.__images__(
            file,
            zoomin,
            from_page,
            to_page
        )
        self._layouts_rec(zoomin)
        logger.info('Layout analysis finished.')
        self._table_transformer_job(zoomin)
        logger.info('Table analysis finished.')
        self._text_merge()
        logger.info('Text merging finished')
        self.tables = self._extract_table_figure(True, zoomin, False, True)
        logger.info('table and figure extracting finished')
        # self._concat_downward()

        # if hasattr(self.pdf, 'close'):
        #     self.pdf.close()
        #     logger.info('pdf closed')
        gc.collect()


class _LawsParser(_BaseParser):
    def __init__(self, *args, **kwargs):
        self.model_type = 'laws'
        super().__init__(*args, **kwargs)

    def __call__(self, file, from_page=0, to_page=sys.maxsize, zoomin=3):
        self.__images__(
            file,
            zoomin,
            from_page,
            to_page
        )
        self._layouts_rec(zoomin)
        self._naive_vertical_merge()
        self.tables = []

        if hasattr(self.pdf, 'close'):
            self.pdf.close()
            logger.info('pdf closed')
        gc.collect()


class _BookParser(_BaseParser):
    def __call__(self, file, from_page=0, to_page=100000, zoomin=3):
        self.__images__(
            file,
            zoomin,
            from_page,
            to_page
        )
        self._layouts_rec(zoomin)
        self._table_transformer_job(zoomin)
        self._text_merge()
        self.tables = self._extract_table_figure(True, zoomin, True, True)
        self._naive_vertical_merge()
        self._filter_forpages()
        self._merge_with_same_bullet()

        if hasattr(self.pdf, 'close'):
            self.pdf.close()
            logger.info('pdf closed')
        gc.collect()


class _TableParser(_NaiveParser):
    pass


class Parser:
    @staticmethod
    def get_parser(
            garbage_file_name: str,
            document_type='naive'
    ) -> _BaseParser:
        if document_type in _PARSER_DICT.keys():
            return eval(_PARSER_DICT[document_type])(garbage_file_name)
        else:
            logger.info('未找到document_type，默认使用naive。')
            return _NaiveParser(garbage_file_name)


class PlainParser:
    def __call__(self, filename, from_page=0, to_page=100000, **kwargs):
        self.outlines = []
        lines = []
        try:
            self.pdf = PdfReader(
                filename if isinstance(
                    filename, str) else BytesIO(filename))
            for page in self.pdf.pages[from_page:to_page]:
                lines.extend([t for t in page.extract_text().split("\n")])

            outlines = self.pdf.outline

            def dfs(arr, depth):
                for a in arr:
                    if isinstance(a, dict):
                        self.outlines.append((a["/Title"], depth))
                        continue
                    dfs(a, depth + 1)

            dfs(outlines, 0)
        except Exception as e:
            logger.warning(f"Outlines exception: {e}")
        if not self.outlines:
            logger.warning(f"Miss outlines")

        return [(l, "") for l in lines], []

    def crop(self, ck, need_position):
        raise NotImplementedError

    @staticmethod
    def remove_tag(txt):
        raise NotImplementedError
