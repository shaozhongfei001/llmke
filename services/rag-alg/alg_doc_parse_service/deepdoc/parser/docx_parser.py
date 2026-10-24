import base64
import os
import re
import traceback
from io import BytesIO
from pathlib import Path
from typing import Iterator

import docx
from PIL import Image
from docx import Document
from docx.opc.oxml import parse_xml
from docx.opc.pkgreader import _SerializedRelationships, _SerializedRelationship
from langchain_core.document_loaders import Blob

from log import logger
from .base_parser import BaseParser
from .image_parser import Parser as ImageParser
from .utils import _PARSER_DICT
from ..output_object import ParsedTableCell, ParsedTable, ParsedImage, ParsedText, ParsedImageMetadata, \
    ParsedTextMetadata, ParsedTableMetadata


def load_from_xml_v2(baseURI, rels_item_xml):
    """
    Return |_SerializedRelationships| instance loaded with the
    relationships contained in *rels_item_xml*. Returns an empty
    collection if *rels_item_xml* is |None|.

    这个函数是为了解决python-docx中无法处理docx中存在的NULL引用问题
    参考：https://github.com/python-openxml/python-docx/issues/1105#issuecomment-1298075246
    """
    srels = _SerializedRelationships()
    if rels_item_xml is not None:
        rels_elm = parse_xml(rels_item_xml)
        for rel_elm in rels_elm.Relationship_lst:
            if rel_elm.target_ref in ('../NULL', 'NULL'):
                continue
            srels._srels.append(_SerializedRelationship(baseURI, rel_elm))
    return srels


_SerializedRelationships.load_from_xml = load_from_xml_v2


def _clean(line):
    line = re.sub(r'\u3000', ' ', line).strip()
    return line


class _BaseParser(BaseParser):
    def __init__(self):
        self.doc = None
        self.file_path = None
        self.image_parser = ImageParser.get_parser()
        self.image_count = 0

    def __call__(self, file):
        raise Exception('不允许使用_BaseParser')

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        return self(blob)


class _NaiveParser(_BaseParser):
    def __init__(self):
        super().__init__()
        self.lines = []

    def __call__(self, file: str | Blob) -> Iterator[ParsedText]:
        # 加载Word文档
        self.file_path = file if isinstance(file, str) else file.path
        self.doc = Document(file) if isinstance(file, str) else Document(BytesIO(file.as_bytes()))

        # 找到docx 中所有图片
        relations_ids = sorted(self.doc.part.rels, key=lambda x: int(x.strip("rIDd")))
        image_list = []

        for rid in relations_ids:
            rel = self.doc.part.rels[rid]
            if "image" in rel.target_ref:
                file_ext = os.path.splitext(rel.target_ref)[-1]  # .png
                file_blob = rel.target_part.blob
                image_list.append(("image", file_ext, file_blob))
            elif "chart" in rel.target_ref:
                # 保存嵌入的 Excel 文件
                # file_ext = os.path.splitext(chart_item.filename)[-1]  # 'charts/chart1.xml'
                file_blob = rel.target_part.blob
                image_list.append(("chart", "", file_blob))
            # TODO 处理附件
            elif 'embeddings' in rel.target_ref:
                # 获取嵌入对象的二进制数据
                embedded_object = rel.target_part.blob

                # 获取嵌入对象名称
                embedded_object_name = os.path.basename(rel.target_ref)

                # 解析文件
                pass

        image_idx = 0
        table_idx = 0

        # 遍历文档中的每个元素
        for element in self.doc.element.body:
            if isinstance(element, docx.oxml.text.paragraph.CT_P):
                # 提取段落文本
                text = element.text
                if text.strip():  # 只添加非空文本
                    yield self.parse_text_document(text)

                for ele in element.inner_content_elements:
                    if isinstance(ele, docx.oxml.text.run.CT_R):
                        for _ in ele.drawing_lst:
                            img_type, img_ext, img_bytes = image_list[image_idx]
                            if img_type == "image":
                                yield self.parse_image(img_bytes=img_bytes, ext=img_ext)
                            else:
                                yield self.parse_chart(img_bytes)
                            image_idx += 1

            elif isinstance(element, docx.oxml.table.CT_Tbl):
                # 提取表格
                yield self.parse_table(table_idx)
                table_idx += 1

            elif element.tag.endswith('drawing'):
                # 提取图片
                img_ext, img_bytes = image_list[image_idx]
                yield self.parse_image(img_bytes=img_bytes, ext=img_ext)
                image_idx += 1

    def parse_table(self, table_idx) -> ParsedTable:
        # 处理表格
        table = self.doc.tables[table_idx]
        cells = []

        merge_row_col_index = -1
        row_span = 0
        col_span = 0

        for row_index, row in enumerate(table.rows):
            for col_index, cell_element in enumerate(row.cells):
                cell = ParsedTableCell(
                    value=cell_element.text,
                    position=(row_index, col_index),
                    is_merged=False,
                    merged_positions=[]
                )

                # TODO 处理合并单元格
                # # 处理单元格的行合并
                # v_merge = cell_element._element.vMerge
                # if v_merge and merge_row_col_index == -1:
                #     cell.is_merged = True
                #     row_span = 1
                #     merge_row_col_index = col_index
                #     for row_span_index in range(row_index + 1, len(rows)):
                #         if not rows[row_span_index][merge_row_col_index]._element.vMerge:
                #             break
                #         row_span += 1
                # elif not v_merge:
                #     merge_row_col_index = -1
                #
                # # 处理单元格的列合并
                # if cell_element.grid_span > 1:
                #     cell.is_merged = True
                #     col_span = cell_element.grid_span

                cells.append(cell)

        metadata = ParsedTableMetadata(source=self.file_path, file_path=self.file_path, table_name='')
        return ParsedTable(table_cells=cells, metadata=metadata)

    def parse_text_document(self, text) -> ParsedText:

        metadata = ParsedTextMetadata(source=self.file_path, file_path=self.file_path)

        return ParsedText(page_content=text, metadata=metadata)

    def parse_image(self, img_bytes, ext) -> ParsedImage:
        self.image_count += 1
        image_blob = Blob.from_data(img_bytes, path=f'{Path(self.file_path).name}-{self.image_count}.{ext.lstrip(".")}')

        image = Image.open(BytesIO(img_bytes))
        metadata = ParsedImageMetadata(
            base64=base64.b64encode(img_bytes).decode(),
            ext=ext,
            source=self.file_path,
            file_path=self.file_path,
            is_parsed=True,
            image_size=list(image.size)
        )
        image.close()

        image_text = ''
        try:
            logger.info(f'解析{self.file_path}的第{self.image_count}张图片中')
            image_results = self.image_parser.parse(image_blob)

            metadata.image_size = image_results[0].metadata.page_size[0]

            for image_result in image_results:
                if not isinstance(image_result, ParsedImage):
                    image_text += image_result.page_content
                    metadata.boxes += image_result.metadata.position
        except Exception as e:
            logger.error(f"[docx中图片解析失败] 图片后缀: {ext}, Error: {e}, Message:{traceback.format_exc()}")

        return ParsedImage(page_content=image_text, metadata=metadata)

    def parse_chart(self, file_blob: bytes) -> ParsedTable:
        from lxml import etree
        tree = etree.fromstring(file_blob)
        texts = []

        # 递归函数，用于打印所有文本
        def get_all_text(element):
            if element.text:
                texts.append(element.text.strip())
            for child in element:
                get_all_text(child)

        # 调用函数，从根元素开始
        get_all_text(tree)
        metadata = ParsedTextMetadata(source=self.file_path, file_path=self.file_path)
        return ParsedText(page_content="\n".join(texts), metadata=metadata)


class _LawsParser(_NaiveParser):
    pass


class _BookParser(_NaiveParser):
    pass


class _TableParser(_NaiveParser):
    pass


class Parser:
    @staticmethod
    def get_parser(document_type='naive'):
        if document_type in _PARSER_DICT.keys():
            return eval(_PARSER_DICT[document_type])()
        else:
            logger.info('未找到document_type，默认使用naive。')
            return _NaiveParser()
