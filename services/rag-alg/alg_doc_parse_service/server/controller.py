import asyncio
import base64
import copy
import json
import os
import re
import time
import traceback
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from tqdm import tqdm

from server.operator.async_runner import async_runner
from server.middleware import register_middlewares
from deepdoc.image_link import link_images_text, link_images_text_ppt
from deepdoc.multi_version.version_rec import VersionRec
from deepdoc.output_object import ParsedText, ParsedImage, ParsedTable
from deepdoc.parser import ImageParser
from deepdoc.splitter import Splitter
from deepdoc.splitter.utils import LENGTH_FUNCTIONS, extract_preceding_context, merge_table_documents
from log import logger, request_id, set_request_id
from server.exception.base import get_error_code, ApiError
from server.loader import load_files, LoadResult
from .api_param import ParseParams, OCRParams, ReviseDateParams, FileVersionParams, IndicatorQueryParams, \
    IndicatorModifyParams, IndicatorGroupbyParams, ModelInfo, DatabaseDescConfig, IndicatorAddParams
from .exception.custom_exception import FileParseFailedError, IndexInternalError
from .indexing_utils import index_es, index_milvus
from .minio_utils import MinioFile
from .multi_modal_utils import PROMPT_TEMPLATE, QUERY, MultiModalClient, MultiModalMessage, RELATIVE_CHUNKS, \
    MERGE_PROMPT_TEMPLATE, MERGE_QUERY
from .nacos_utils import DocParseConfig
from .process_reporter import ProcessReporter, TASK_STATUS
from .response_model import ParseResponse, TaskResult, OCRResponse, Box, MultiVersionResponse, IndicatorResponse, \
    BaseResponse, IndicatorGroupbyResponse, DataBaseDescResponse
from .utils import create_uuid, run_in_thread_pool, image_need_multi_modal, try_catch
from deepdoc.database_desc.build_database_desc import (DatabaseDesc)

indexing_failed_chunks = Path(DocParseConfig().config['log_path']) / 'indexing_failed_chunks'
if not os.path.exists(indexing_failed_chunks):
    os.makedirs(indexing_failed_chunks)

app = FastAPI()

# 添加请求日志中间件
register_middlewares(app)


class _Parser:
    def __init__(self, parse_params: ParseParams):
        parse_params_str = json.dumps(parse_params.model_dump(), indent=4, ensure_ascii=False)

        logger.info(parse_params_str)

        self.request_id = request_id.get()
        self.parse_params = parse_params

        with ProcessReporter() as process_reporter:
            process_reporter.update_process(
                task_id=self.request_id,
                minio_paths=','.join(map(lambda file: file.file_path, parse_params.files))
            )

        # 解析后结果
        self.load_results: list[LoadResult] = []
        self.documents: list[ParsedText] = []

        # 文本图片切块
        self.text_image_chunks: list[ParsedText | dict] = []

        # 表格切块结果
        self.table_chunks: list[ParsedText | dict] = []  # 规则表格按行/列切分结果
        self.table_summaries: list[ParsedTable | dict] = []  # 表格概述 （大模型生成/ 表头拼接）
        self.table_backbones = []  # 大型表格的骨架信息 （表格压缩后原始代码）
        self.all_chunks: list[ParsedText] = []

        self.task_results: list[TaskResult] = []
        self.success = True
        self.files_type_have_excel = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def report_after_started(self, info: str):
        logger.info(info)

        with ProcessReporter() as process_reporter:
            process_reporter.update_process(
                task_id=self.request_id,
                status=TASK_STATUS.STARTED.value,
                process_info=info
            )

    def close(self):
        if not self.success:
            with ProcessReporter() as process_reporter:
                process_reporter.update_process(
                    task_id=self.request_id,
                    process_info='有文件解析失败，成功的文件索引正常。',
                    status=TASK_STATUS.FAILED.value,
                    result=json.dumps(
                        [task_result.model_dump() for task_result in self.task_results],
                        indent=4,
                        ensure_ascii=False
                    )
                )

    @staticmethod
    def sort_by_offset(parsed_texts: list[ParsedText]) -> list[ParsedText]:
        def sort_key(parsed_text: ParsedText):
            offset = parsed_text.metadata.offset
            return [offset[0][0], offset[-1][-1]]

        return sorted(parsed_texts, key=sort_key)

    def parse_without_chunking(self, multi_modal=True, need_image_boxes=True):
        self.report_after_started('开始解析')

        if self.parse_params.files:
            for result in load_files(
                    self.parse_params,
                    multi_thread=False,
                    multi_modal=multi_modal,
                    need_image_boxes=need_image_boxes
            ):
                self.load_results.append(result)

        for load_result in self.load_results:
            self.success = self.success and load_result.success

            if load_result.success:
                self.documents += load_result.documents

            self.task_results.append(TaskResult(
                file_path=load_result.file_path,
                file_id=load_result.file_id,
                success=load_result.success,
                fail_reason='解析失败：' + str(load_result.exception) if not load_result.success else None,
                revise_date=load_result.revise_date,
                code=200 if load_result.success else get_error_code(load_result.exception)
            ))

    def multi_modal_process(self, images: list[ParsedText]):
        timer = time.perf_counter()

        images = list(filter(lambda x: isinstance(x, ParsedImage) and x.metadata.is_parsed, images))
        image_amount = len(images)
        self.report_after_started(f'开始进行多模态处理，一共有{image_amount}个图片待处理。')

        text_chunks_dict = {}
        for text_image_chunk in self.text_image_chunks:
            if text_image_chunk.metadata.type == 'text':
                text_chunks_dict[text_image_chunk.metadata.pk] = text_image_chunk

        @set_request_id(self.request_id)
        def worker(_index: int, _image: ParsedImage, _multi_modal_config: ModelInfo):
            logger.info(f'多模态处理进度：{_index}/{image_amount}，{_index / image_amount * 100:.2f}%')
            metadata = _image.metadata
            boxes = metadata.boxes
            image_size = metadata.image_size

            # [R12-FIX-PARSE-02] 首次进入时把 parser（OCR）产出的文字固化为基线，
            # 之后所有合并都以 ocr_text 为锚，避免被 VLM 输出覆盖。
            if metadata.ocr_text is None:
                metadata.ocr_text = _image.page_content or ''

            # [R12-FIX-PARSE-02] 幂等：已成功拿到 VLM 结果的图片不再重复调用。
            # 原实现会在"二次多模态处理"里把首轮 VLM 输出当作"图片内文字内容"再问一遍，
            # 导致自我退化（实测退化为"图片上没有文字信息"）并覆盖首轮的正确结果。
            if metadata.vlm_status == 'ok' and metadata.vlm_text:
                _image.page_content = self._merge_image_text(metadata)
                return

            if not image_need_multi_modal(image_size, boxes):
                metadata.vlm_status = 'skipped'
                _image.page_content = self._merge_image_text(metadata)
                return

            multi_modal_client = MultiModalClient(_multi_modal_config)
            prompt = ''

            # [R12-FIX-PARSE-02] 送入模型的"图片内文字"始终取 OCR 基线，不取 page_content，
            # 防止二次处理时把上一轮 VLM 输出当成输入（反馈污染）。
            if metadata.ocr_text and not metadata.text_parent_id_list:
                prompt += PROMPT_TEMPLATE.replace('{{content}}', metadata.ocr_text) + '\n\n'

            if metadata.text_parent_id_list:
                logger.info('找到关联文本块')
                relative_chunks = '\n'.join([
                    text_chunks_dict[text_parent_id].page_content
                    for text_parent_id in metadata.text_parent_id_list
                    if text_parent_id in text_chunks_dict
                ])
                prompt += RELATIVE_CHUNKS.replace('{{content}}', relative_chunks) + '\n\n'
            prompt += QUERY

            try:
                response, meta = multi_modal_client.chat([
                    MultiModalMessage(
                        type='text',
                        content=prompt
                    ),
                    MultiModalMessage(
                        type='image',
                        content=base64.b64decode(metadata.base64)
                    )
                ], return_meta=True)
                metadata.vlm_text = response
                metadata.vlm_finish_reason = (meta or {}).get('finish_reason')
                _timings = (meta or {}).get('timings') or {}
                metadata.vlm_prompt_n = _timings.get('prompt_n')
                metadata.vlm_cache_n = _timings.get('cache_n')
                # [R12-FIX-PARSE-05] 字符敏感字段标记：VLM 实测会丢字（CASE-CCC333 → CASE-CC333），
                # 编号/账号/金额/日期不得只靠 VLM，需下游用 OCR/正则交叉校验。
                _tokens = self._detect_sensitive_tokens(response)
                metadata.vlm_sensitive_tokens = _tokens
                metadata.vlm_needs_crosscheck = bool(_tokens)
                # [R12-FIX-PARSE-05] finish_reason='length' ⇒ 输出被 max_tokens 截断，
                # 不能当作"完整逐字转录"用；单独打 truncated 档，便于 QA 用廉价断言识别。
                if metadata.vlm_finish_reason == 'length':
                    metadata.vlm_status = 'truncated'
                    logger.warning(f'第{_index}张图片 VLM 输出被截断（finish_reason=length，'
                                   f'output_max_tokens={DocParseConfig().config.get("online_multi_modal_model", {}).get(_multi_modal_config.model_id, {}).get("output_max_tokens", 4096)}），'
                                   f'该图文本不完整')
                else:
                    metadata.vlm_status = 'ok'
            except Exception as exc:
                # [R12-FIX-PARSE-03] 单图 VLM 失败不得让整篇解析失败（原实现异常冒泡 → 整篇 500，
                # 连正文都拿不到）。这里只降级打标：保留 OCR 文本，标注失败分档。
                metadata.vlm_status = getattr(exc, 'kind', None) or 'failed'
                metadata.vlm_text = None
                logger.error(f'第{_index}张图片多模态处理失败（vlm_status={metadata.vlm_status}），'
                             f'该图降级为纯 OCR 文本：{exc}')

            _image.page_content = self._merge_image_text(metadata)
            # [R12-FIX-PARSE-02] 有 OCR 文字框时补页内 bbox 定位（页码无法伪造，保持为空）
            if boxes and not metadata.position:
                xs = [pt[0] for box in boxes for pt in box]
                ys = [pt[1] for box in boxes for pt in box]
                metadata.position = [[[min(xs), min(ys)], [max(xs), min(ys)],
                                      [max(xs), max(ys)], [min(xs), max(ys)]]]
                if image_size and not metadata.page_size:
                    metadata.page_size = [image_size]

        # [R12-FIX-PARSE-03] 并发上限：原实现用默认线程池（最多 32），N 张图会同时打 N 个 VLM 请求，
        # 在 CPU 上既无吞吐收益（实测 1.08×），还会把服务端 KV 水位打穿（mtmd 硬失败）。默认改为 1。
        max_workers = DocParseConfig().config.get('multi_modal_max_workers', 1)
        futures = run_in_thread_pool(
            worker,
            [{
                '_index': index,
                '_image': image,
                '_multi_modal_config': self.parse_params.multi_model_info
            } for index, image in enumerate(images)],
            max_workers=max_workers
        )
        for _ in tqdm(futures, total=image_amount, desc='多模态处理'):
            pass

        logger.info(f'多模态处理花费时间：{(time.perf_counter() - timer):.2f}s')

    @staticmethod
    def _detect_sensitive_tokens(text: str) -> list[str]:
        """[R12-FIX-PARSE-05] 抽出"字符敏感"片段：长数字串、金额、日期、带连字符的编号。

        VLM 逐字转录存在字符级误识（实测 CASE-CCC333 → CASE-CC333，连续相同字符被合并），
        因此这些片段不能直接当证据字段，必须由 OCR / 正则 / 校验位交叉校验。
        """
        if not text:
            return []
        patterns = [
            r"[0-9]{6,}",                                  # 账号/长编号
            r"[0-9][0-9,]*\.[0-9]{2}",                     # 金额（两位小数）
            # 金额（万元/亿元计价）：1,250 万元 / 3.2 亿元 —— 只认两位小数会漏
            r"[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:万元|亿元|万|亿)",
            # 日期：尾部「日/号」必须纳入，否则等值比对会错位（2026年10月20 ≠ 2026年10月20日）
            r"[0-9]{4}\s*[-/.年]\s*[0-9]{1,2}\s*[-/.月]\s*[0-9]{1,2}\s*[日号]?",
            # 百分比/利率：4.35% / 年化 3.85% / LPR+50BP —— 错一位即实质错误
            r"[0-9]+(?:\.[0-9]+)?\s*%",
            r"(?:LPR|lpr)\s*[+-]\s*[0-9]+\s*(?:BP|bp|个基点)",
            r"[A-Za-z]{2,}-[A-Za-z0-9-]{4,}",              # 形如 SPDB-2026-PJ-00871 / CASE-AAA111
        ]
        found, seen = [], set()
        for pat in patterns:
            for m in re.finditer(pat, text):
                tok = m.group(0).strip()
                if tok and tok not in seen:
                    seen.add(tok)
                    found.append(tok)
        return found[:10]

    @staticmethod
    def _merge_image_text(metadata) -> str:
        """[R12-FIX-PARSE-02] 图片块文本 = OCR 基线 ∪ VLM 描述（VLM 只补充、不覆盖）。

        [R12-FIX-PARSE-06] 但 `vlm_status == 'truncated'`（finish_reason=length）时**不并入**：
        截断残句常是半句/半词/半个数字（如 `金额 1,250.0`、`账号 6222001234`），
        拼进正文后下游无法分辨，且可能"补上"一个看起来合理的数字前缀，比缺文本更有害。
        宁可缺，不可污染；状态仍保留在 metadata.vlm_status / vlm_finish_reason 上供下游识别。
        """
        ocr = (metadata.ocr_text or '').strip()
        if metadata.vlm_status == 'truncated':
            return ocr
        vlm = (metadata.vlm_text or '').strip()
        parts = [p for p in (ocr, vlm) if p]
        return '\n\n'.join(parts)

    def chunk(self):
        timer = time.perf_counter()

        self.report_after_started('开始切分')

        # 过滤掉非text的解析结果 作为splitter的输入
        text_documents: list[ParsedText] = []
        table_documents: list[ParsedTable] = []
        image_documents: list[ParsedImage] = []
        # [跨页表格合并-仅对financial]
        if self.parse_params.file_type == 'financial':
            self.documents = merge_table_documents(self.documents, model_info=self.parse_params.model_info, span_len=4)
        for _idx, document in enumerate(self.documents):
            if document.metadata.type == 'text':
                text_documents.append(document)
            elif isinstance(document, ParsedTable):
                # [为表格抽取上文]
                document.metadata.table_preceding_context = extract_preceding_context(_idx, self.documents)
                table_documents.append(document)
            elif isinstance(document, ParsedImage):
                image_documents.append(document)
            else:
                raise Exception(f'未定义类型：{type(document)}')

        # 获取splitter关键字参数
        splitter_args = {
            'chunk_size': self.parse_params.chunk_size,
            'chunk_overlap': self.parse_params.chunk_overlap,
            'length_function': LENGTH_FUNCTIONS[self.parse_params.length_function],
            'user_id': self.parse_params.user_id,
            'knowledge_base_id': self.parse_params.knowledge_base_id,
            'split_regex': self.parse_params.split_regex,
            'model_info': self.parse_params.model_info,
            'embedding_model_info': self.parse_params.embedding_model_info,
            'multi_model_info': self.parse_params.multi_model_info
        }
        # [chunk_overlap 不能大于 chunk_size]
        if splitter_args["chunk_overlap"] > splitter_args["chunk_size"]:
            splitter_args["chunk_overlap"] = 0

        logger.info('文本切分中')
        splitter = Splitter.get_splitter(
            self.parse_params.file_type,
            False,
            **splitter_args
        )
        text_documents = splitter.chunk(text_documents)

        # 处理文本块position
        last_position = [[0, 0]] * 4
        last_page_size = [0, 0]
        last_page_number = 0

        if text_documents:
            metadata = text_documents[0].metadata
            if metadata.position:
                last_position = metadata.position[0]
            if metadata.page_size:
                last_page_size = metadata.page_size[0]
            if metadata.page_number:
                last_page_number = metadata.page_number[0]

        for chunk in text_documents:
            metadata = chunk.metadata
            new_position = []
            new_page_size = []
            new_page_number = []
            all_zero = True

            for position, page_size, page_number in zip(metadata.position, metadata.page_size, metadata.page_number):
                if position != [[0, 0]] * 4:
                    last_position = position
                    last_page_size = page_size
                    last_page_number = page_number
                    all_zero = False
                    new_position.append(position)
                    new_page_size.append(page_size)
                    new_page_number.append(page_number)

            if all_zero:
                chunk.metadata.position = [last_position]
                chunk.metadata.page_size = [last_page_size]
                chunk.metadata.page_number = [last_page_number]
            else:
                chunk.metadata.position = new_position
                chunk.metadata.page_size = new_page_size
                chunk.metadata.page_number = new_page_number

        # 按顺序插入图片
        sorted_all_chunks = _Parser.sort_by_offset(text_documents + image_documents + table_documents)
        self.text_image_chunks = []
        for i, chunk in enumerate(sorted_all_chunks):
            chunk.metadata.parsed_chunk_index = i
            if not isinstance(chunk, ParsedTable):
                chunk.metadata.pk = create_uuid()
                self.text_image_chunks.append(chunk)

        logger.info('表格切分中')
        splitter = Splitter.get_splitter(
            self.parse_params.file_type,
            True,
            **splitter_args
        )
        table_i = 0
        for chunk in splitter.chunk(table_documents):
            if chunk.metadata.type == 'table':
                chunk.metadata.chunk_index = table_i
                self.table_chunks.append(chunk)
                table_i += 1
            else:
                self.table_summaries.append(chunk)

        logger.info(f'切分花费时间：{(time.perf_counter() - timer):.2f}s')

    def judge(self, documents):
        """
        判断是不是pdf文件,如果是pdf文件,进行处理
        """
        is_ppt = False
        for document in documents:
            parent_file_name = str(document.metadata.parent_file_name)
            file_path = str(document.metadata.file_path)
            page_size = document.metadata.page_size
            if parent_file_name.endswith(".pptx"):
                is_ppt = True
                break
            if file_path.endswith(".pdf") and not parent_file_name.endswith(".doc") and not parent_file_name.endswith(
                    ".txt") \
                    and not parent_file_name.endswith(".docx"):
                for page in page_size:
                    if len(page) == 2:
                        if page[0] > page[1]:
                            is_ppt = True
        return is_ppt

    def merge_pptx_image(self, images):
        """
        按照每一页合并一个解析
        解析之后图片关联到这个chunk，图片不进行单独解析
        图片进行挂载
        """

        def deduplicate_nested_list_ordered(ordered_list: list) -> list:
            """
            有序去重：保留原列表中子列表的首次出现顺序
            要求：子列表中的元素必须是可哈希类型
            """
            seen = set()  # 记录已出现的子列表（以元组形式）
            result = []
            for sublist in ordered_list:
                key = tuple(sublist)
                if key not in seen:
                    seen.add(key)
                    result.append(sublist)
            return result

        # 测试示例
        merge_images = []
        images_dict = {}
        # 这里只处理图片类型的 Document，避免文本元数据（ParsedTextMetadata）不存在 base64 字段时报错
        for document in images:
            # if not isinstance(document, ParsedImage):
            #     continue

            page_number = document.metadata.page_number[0]
            if page_number in images_dict:
                images_dict[page_number].page_content = images_dict[
                                                            page_number].page_content + " " + document.page_content
                images_dict[page_number].metadata.base64 = images_dict[
                                                               page_number].metadata.base64 + document.metadata.base64
                images_dict[page_number].metadata.page_number.extend(document.metadata.page_number)
                images_dict[page_number].metadata.offset.extend(document.metadata.offset)
                images_dict[page_number].metadata.position.extend(document.metadata.position)
            else:
                metadata = copy.deepcopy(document.metadata)
                images_dict[page_number] = ParsedText(page_content=document.page_content, metadata=metadata)
        for key in images_dict:
            try:
                images_dict[key].metadata.image_path = ""
            except:
                pass
            try:
                images_dict[key].metadata.image_url = ""
            except:
                pass
            images_dict[key].metadata.offset = deduplicate_nested_list_ordered(images_dict[key].metadata.offset)
            images_dict[key].metadata.pk = create_uuid()
            merge_images.append(images_dict[key])
        return merge_images

    def multi_modal_process_ppt(self, images: list[ParsedText]):
        timer = time.perf_counter()
        self.merge_images = self.merge_pptx_image(images)
        images = list(filter(lambda x: isinstance(x, ParsedImage) and x.metadata.is_parsed, images))
        self.merge_images.extend(images)
        image_amount = len(self.merge_images)
        self.report_after_started(f'开始进行多模态处理，一共有{image_amount}个图片待处理。')

        text_chunks_dict = {}
        for text_image_chunk in self.text_image_chunks:
            if text_image_chunk.metadata.type == 'text':
                text_chunks_dict[text_image_chunk.metadata.pk] = text_image_chunk

        @set_request_id(self.request_id)
        def worker(_index: int, _image: ParsedImage, _multi_modal_config: ModelInfo):
            logger.info(f'多模态处理进度：{_index}/{image_amount}，{_index / image_amount * 100:.2f}%')
            multi_modal_client = MultiModalClient(_multi_modal_config)
            prompt = ''

            if _image.page_content:
                prompt += MERGE_PROMPT_TEMPLATE.replace('{{content}}', _image.page_content) + '\n\n'

            prompt += MERGE_QUERY

            if len(_image.metadata.base64) > 0:
                response = multi_modal_client.chat([
                    MultiModalMessage(
                        type='text',
                        content=prompt
                    ),
                    MultiModalMessage(
                        type='image',
                        content=base64.b64decode(_image.metadata.base64)
                    )
                ])

                _image.page_content = response

        futures = run_in_thread_pool(
            worker,
            [{
                '_index': index,
                '_image': image,
                '_multi_modal_config': self.parse_params.multi_model_info
            } for index, image in enumerate(self.merge_images)]
        )
        for _ in tqdm(futures, total=image_amount, desc='多模态处理'):
            pass

        logger.info(f'多模态处理花费时间：{(time.perf_counter() - timer):.2f}s')

    def parse(self):
        self.parse_without_chunking()
        is_ppt = self.judge(self.documents)
        is_ppt = False # ppt解析存在bug，先关掉等优化好打开
        if is_ppt:
            self.multi_modal_process_ppt(self.documents)
            self.text_image_chunks.extend(self.merge_images)
            for document in self.text_image_chunks:
                if isinstance(document, ParsedText):
                    document.metadata.base64 = None
            for document in self.text_image_chunks:
                document.metadata.pk = create_uuid()
            self.text_image_chunks = link_images_text_ppt(self.text_image_chunks,
                                                          self.parse_params.embedding_model_info)
            chunks = []
            for chunk in self.text_image_chunks:
                try:
                    image_path = chunk.metadata.image_path
                    if len(image_path) == 0:
                        if chunk.page_content.strip():
                            chunk = chunk.model_dump()
                            if chunk['metadata']['type'] == 'image':
                                chunk['metadata'].pop('base64', None)
                                chunk['metadata'].pop('ext', None)
                            chunks.append(chunk)
                except:
                    if chunk.page_content.strip():
                        chunk = chunk.model_dump()
                        if chunk['metadata']['type'] == 'image':
                            chunk['metadata'].pop('base64', None)
                            chunk['metadata'].pop('ext', None)
                        chunks.append(chunk)
            self.text_image_chunks = chunks
        else:
            self.multi_modal_process(self.documents)
            self.chunk()

            self.report_after_started('开始图片关联')
            self.text_image_chunks = link_images_text(self.text_image_chunks, self.parse_params.embedding_model_info)

            self.report_after_started('开始二次多模态处理')
            self.multi_modal_process(self.text_image_chunks)

            # 构建文本和图片index服务的入参
            chunks = []
            for chunk in self.text_image_chunks:
                if chunk.page_content.strip():
                    chunk = chunk.model_dump()
                    if chunk['metadata']['type'] == 'image':
                        chunk['metadata'].pop('base64', None)
                        chunk['metadata'].pop('ext', None)
                    chunks.append(chunk)
            self.text_image_chunks = chunks

            # 构建表格index服务的入参
            table_chunks = []
            table_summaries = []
            for chunk in self.table_chunks + self.table_summaries:
                if chunk.page_content:
                    chunk = chunk.model_dump(include={'page_content', 'metadata'})
                    if chunk['metadata']['type'] != 'table':
                        chunk['metadata'].pop('table_summary_id', None)
                        table_summaries.append(chunk)
                    else:
                        table_chunks.append(chunk)
            self.table_chunks = table_chunks
            self.table_summaries = table_summaries

            self.all_chunks = self.text_image_chunks + table_chunks

            # 按照解析后的原始chunk顺序和切分后的chunk 顺序排序
            # self.all_chunks = sorted(self.all_chunks, key=lambda x: [x["metadata"]["parsed_chunk_index"], x["metadata"]["chunk_index"]])

            for file in self.parse_params.files:
                ext = Path(file.file_path).suffix.lower()
                if ext in ['.xls', '.xlsx', '.csv']:
                    self.files_type_have_excel = True
                    break
            if self.files_type_have_excel:
                self.all_chunks = sorted(self.all_chunks,
                                         key=lambda x: [x["metadata"]["parsed_chunk_index"],
                                                        x["metadata"]["chunk_index"]])
            else:
                # 保证按页码顺序排序，同一页内按parsed_chunk_index排序，然后是切分的chunk顺序排序
                # [R12-FIX-PARSE-01] 表格类chunk（如docx内表格）可能没有页码/页尺寸（page_number为空列表），
                # 原实现直接取 page_number[0] 会抛 IndexError 导致整篇解析 500；此处对缺失页码降级为 0。
                self.all_chunks = sorted(self.all_chunks, key=lambda x: [(x["metadata"].get("page_number") or [0])[0],
                                                                         x["metadata"]["parsed_chunk_index"],
                                                                         x["metadata"]["chunk_index"]])

            for i, chunk in enumerate(self.all_chunks):
                self.all_chunks[i]["metadata"].pop("parsed_chunk_index")
                self.all_chunks[i]["metadata"]["chunk_index"] = i



@app.middleware('http')
async def add_task(request: Request, call_next):
    _request_id = request_id.get()
    if _request_id and request.scope.get('route') in {
        '/parse_without_indexing',
        '/parse',
        '/parse/ocr',
        '/parse/revise_date',
        '/parse/multi_version',
        '/indicator_query',
        '/indicator_groupby',
        '/indicator_modify'
    }:
        with ProcessReporter() as process_reporter:
            process_reporter.new_task(
                task_id=_request_id,
                pid=os.getpid(),
                param=json.dumps(await request.json(), indent=4, ensure_ascii=False)
            )
    response = await call_next(request)
    return response


@app.middleware('http')
async def add_request_id_header(request: Request, call_next):
    request_id.set(str(uuid.uuid4()))
    response = await call_next(request)
    response.headers['x-request-id'] = request_id.get()
    return response


@app.post(
    '/parse_without_indexing',
    tags=['File Parse'],
    summary='返回文本解析，但是不进行索引'
)
def parse_without_indexing(parse_params: ParseParams):
    with _Parser(parse_params) as parser:
        if parse_params.need_chunk:
            parser.parse()
        else:
            parser.parse_without_chunking(multi_modal=False)

        # 返回结果
        if not parser.success:
            return ParseResponse(
                msg='有文件解析失败',
                task_statuses=parser.task_results
            )
        else:
            with ProcessReporter() as process_reporter:
                process_reporter.update_process(
                    task_id=parser.request_id,
                    status=TASK_STATUS.COMPLETED.value
                )

        if parse_params.need_chunk:
            return parser.all_chunks
        else:
            return parser.documents


@try_catch
def parse_task(parse_params: ParseParams):
    doc_parse_config = DocParseConfig()
    gateway_ip = doc_parse_config.configs['java-common']['server']['host-ip']
    gateway_port = doc_parse_config.configs['java-gateway']['server']['port']
    async_callback = doc_parse_config.config['async-callback'].format(ip=gateway_ip, port=gateway_port)

    def revoke_callback(payload: ParseResponse | dict):
        if isinstance(payload, ParseResponse):
            payload = json.loads(payload.model_dump_json())

        # [R12-FIX-PARSE-07] task_id 为空时跳过回调：
        # 非 Java 发起的 /parse（如脚本/联调）没有 task_id，Java 侧会 NPE
        # （`FileParseTask.getRetryTimes() because "task" is null`），
        # 这里会把后台任务打成 500 并污染日志。真实 Java 调用一定带 task_id。
        _task_id = payload.get('task_id') if isinstance(payload, dict) else None
        if not _task_id:
            logger.warning('该解析任务没有 task_id（非 Java 主链发起），跳过异步回调')
            return

        # [R12-FIX-PARSE-07] 补超时：原实现无 timeout，网关挂住会把后台线程占死
        response = requests.post(async_callback, json=payload,
                                 timeout=DocParseConfig().config.get('gateway_timeout', 60))

        if response.status_code != 200:
            raise HTTPException(response.status_code,
                                f'回调接口失败：{response.text} 回调URL：{async_callback}, params: {payload}')

        try:
            response = response.json()
            if not response['success']:
                raise Exception(response['errorMsg'])
        except Exception as _e:
            logger.error(response.text)
            raise _e

        logger.debug(f'[Request] 回调接口成功, URL: {async_callback}, params: {payload}')

    with _Parser(parse_params) as parser:
        try:
            if parse_params.need_chunk:
                parser.parse()
                parser_chunks = parser.text_image_chunks
                parser_table_summaries = parser.table_summaries
                parser_table_chunks = parser.table_chunks

                def indexing_error_logging(_info: str, _chunks: list[dict], _index_name: str):
                    indexing_failed_chunks_path = Path(
                        indexing_failed_chunks) / f'{_index_name}_{request_id.get()}.json'
                    with open(indexing_failed_chunks_path, 'w') as f:
                        json.dump(_chunks, f, indent=4, ensure_ascii=False)

                    logger.error(f'{_info}，具体chunks内容已记录到{indexing_failed_chunks_path}中。')

                    with ProcessReporter() as _process_reporter:
                        _process_reporter.update_process(
                            task_id=parser.request_id,
                            status=TASK_STATUS.FAILED.value,
                            process_info=_info + traceback.format_exc()
                        )

                    return ParseResponse(msg=_info, task_statuses=parser.task_results, task_id=parse_params.task_id)

                timer = time.perf_counter()

                for chunks, name_prefix, task_name in [(parser_chunks, "", "解析块"),
                                                       (parser_table_summaries, "table_summary_", "表格总结"),
                                                       (parser_table_chunks, "table_chunks_", "表格解析块")]:
                    if chunks:
                        index_name = name_prefix + str(parse_params.index_name)
                        es_time = time.time()
                        # 调用es索引接口
                        try:
                            future = async_runner.submit(index_es(
                                index_name=index_name,
                                document_list=chunks
                            ))
                            future.result()  # 等待任务完成
                        except Exception as e:
                            _e = e
                            if not isinstance(e, ApiError):
                                e = IndexInternalError(str(e))
                            indexing_error_logging(f'[es]index服务插入[{task_name}]错误: {_e}', chunks, index_name)

                            raise e.__class__(f'[es]index服务插入[{task_name}]错误: {_e}') from _e
                        logger.info(f"[es]index服务插入[{task_name}]耗时: {(time.time() - es_time):.2f}s")

                        milvus_time = time.time()
                        # 调用milvus索引接口
                        try:
                            future = async_runner.submit(index_milvus(
                                index_name=index_name,
                                embed_model=parse_params.embedding_model_info.model_id,
                                document_list=chunks
                            ))
                            future.result()  # 等待任务完成
                        except Exception as e:
                            _e = e
                            if not isinstance(e, ApiError):
                                e = IndexInternalError(str(e))
                            indexing_error_logging(f'[milvus]index服务插入[{task_name}]错误: {_e}', chunks, index_name)
                            raise e.__class__(f'[milvus]index服务插入[{task_name}]错误: {_e}') from _e
                        logger.info(f"[milvus]index服务插入[{task_name}]耗时: {(time.time() - milvus_time):.2f}s")

                logger.info(f'[es][milvus]index服务插入索引总花费时间：{(time.perf_counter() - timer):.2f}s')

            else:
                parser.parse_without_chunking(need_image_boxes=False)
        except Exception as e:
            with ProcessReporter() as process_reporter:
                process_reporter.update_process(
                    task_id=parser.request_id,
                    status=TASK_STATUS.FAILED.value,
                    process_info=traceback.format_exc()
                )
            _e = e
            if not isinstance(e, ApiError):
                e = FileParseFailedError(str(e))
            task_statuses = []
            for file in parse_params.files:
                task_statuses.append(TaskResult(
                    file_path=file.file_path,
                    file_id=file.file_id,
                    success=False,
                    fail_reason=f"解析失败: {e}",
                    code=get_error_code(e),
                ))
            revoke_callback(ParseResponse(msg=str(e), task_id=parse_params.task_id, task_statuses=task_statuses))
            raise _e

        if not parser.success:
            parse_response = ParseResponse(
                msg='有文件解析失败，成功解析的文件索引正常。',
                task_statuses=parser.task_results,
                task_id=parse_params.task_id
            )

            if parse_params.need_chunk:
                revoke_callback(parse_response)
                return None

            return parse_response
        else:
            with ProcessReporter() as process_reporter:
                process_reporter.update_process(
                    task_id=parser.request_id,
                    process_info='解析完成',
                    status=TASK_STATUS.COMPLETED.value
                )

            if parse_params.need_chunk:
                revoke_callback(ParseResponse(
                    success=True,
                    task_statuses=parser.task_results,
                    task_id=parse_params.task_id
                ))
                return None

            return {
                'success': True,
                'msg': '成功',
                'documents': [document.model_dump() for document in parser.documents],
                'task_id': parse_params.task_id
            }


@app.post(
    '/parse',
    tags=['File Parse'],
    summary='文本解析，将数据添加到数据库中'
)
def parse(parse_params: ParseParams, background_tasks: BackgroundTasks):
    if parse_params.need_chunk:
        try:
            logger.info('start')
            background_tasks.add_task(parse_task, parse_params)
        except Exception as e:
            logger.exception(e)
            return {'success': False, 'msg': e, 'task_id': parse_params.task_id}
        return {'success': True, 'msg': '正在执行', 'task_id': parse_params.task_id}
    else:
        return parse_task(parse_params)


@app.post(
    '/parse_sync',
    tags=['File Parse'],
    summary='文本解析，将数据添加到数据库中'
)
def parse_sync(parse_params: ParseParams):
    with _Parser(parse_params) as parser:
        try:
            if parse_params.need_chunk:
                parser.parse()
                parser_chunks = parser.text_image_chunks
                parser_table_summaries = parser.table_summaries
                parser_table_chunks = parser.table_chunks

                def indexing_error_logging(_info: str, _chunks: list[dict], _index_name: str):
                    indexing_failed_chunks_path = Path(
                        indexing_failed_chunks) / f'{_index_name}_{request_id.get()}.json'
                    with open(indexing_failed_chunks_path, 'w') as f:
                        json.dump(_chunks, f, indent=4, ensure_ascii=False)

                    logger.error(f'索引失败，具体chunks内容已记录到{indexing_failed_chunks_path}中。')
                    logger.exception(_info)

                    with ProcessReporter() as _process_reporter:
                        _process_reporter.update_process(
                            task_id=parser.request_id,
                            status=TASK_STATUS.FAILED.value,
                            process_info=_info + traceback.format_exc()
                        )

                    return ParseResponse(msg=_info, task_statuses=parser.task_results)

                timer = time.perf_counter()

                for chunks, name_prefix in [(parser_chunks, ""),
                                            (parser_table_summaries, "table_summary_"),
                                            (parser_table_chunks, "table_chunks_")]:
                    if chunks:
                        index_name = name_prefix + str(parse_params.index_name)

                        # 调用es索引接口
                        try:
                            future = async_runner.submit(index_es(
                                index_name=index_name,
                                document_list=chunks
                            ))
                            future.result()  # 等待任务完成
                        except Exception as e:
                            return indexing_error_logging(f'ES错误：{e}', chunks, index_name)

                        # 调用milvus索引接口
                        try:
                            future = async_runner.submit(index_milvus(
                                index_name=index_name,
                                embed_model=parse_params.embedding_model_info.model_id,
                                document_list=chunks
                            ))
                            future.result()  # 等待任务完成
                        except Exception as e:
                            return indexing_error_logging(f'milvus错误：{e}', chunks, index_name)

                logger.info(f'索引花费时间：{(time.perf_counter() - timer):.2f}s')

            else:
                parser.parse_without_chunking(need_image_boxes=False)
        except Exception as e:
            logger.exception(e)

            with ProcessReporter() as process_reporter:
                process_reporter.update_process(
                    task_id=parser.request_id,
                    status=TASK_STATUS.FAILED.value,
                    process_info=traceback.format_exc()
                )

            return ParseResponse(msg=str(e))

        # 返回结果
        if not parser.success:
            return ParseResponse(
                msg='有文件解析失败，成功解析的文件索引正常。',
                task_statuses=parser.task_results
            )
        else:
            with ProcessReporter() as process_reporter:
                process_reporter.update_process(
                    task_id=parser.request_id,
                    process_info='解析完成',
                    status=TASK_STATUS.COMPLETED.value
                )

        if parse_params.need_chunk:
            return ParseResponse(success=True, task_statuses=parser.task_results)
        else:
            if parser.task_results:
                return ParseResponse(success=True, task_statuses=parser.task_results)
            else:
                return {
                    'success': True,
                    'msg': '成功',
                    'documents': [document.model_dump() for document in parser.documents]
                }


@app.post(
    '/parse/ocr',
    tags=['File Parse', 'OCR'],
    response_model=OCRResponse,
    summary='获取ocr结果'
)
def ocr(ocr_params: OCRParams):
    blob = MinioFile(ocr_params.image_path).get_blob()
    if ImageParser.is_image(blob):
        parser = ImageParser.get_parser()
    else:
        return OCRResponse(msg='不是图片')

    boxes = [Box(**box) for box in parser.get_ocr_boxes(blob)]

    return OCRResponse(
        success=True,
        boxes=boxes
    )


@app.post(
    '/parse/revise_date',
    tags=['File Parse', 'Get Revise Date'],
    response_model=ParseResponse,
    summary='获取修订日期'
)
def get_revise_date(revise_date_params: ReviseDateParams):
    with _Parser(revise_date_params) as parser:
        parser.parse_without_chunking()

        # 返回结果
        if not parser.success:
            return ParseResponse(
                msg='有文件解析失败，成功解析的文件索引正常。',
                task_statuses=parser.task_results
            )
        else:
            with ProcessReporter() as process_reporter:
                process_reporter.update_process(
                    task_id=parser.request_id,
                    process_info='解析完成',
                    status=TASK_STATUS.COMPLETED.value
                )

        return ParseResponse(success=True, task_statuses=parser.task_results)


@app.post(
    '/parse/multi_version',
    tags=['File Parse', 'Get multi version id'],
    response_model=MultiVersionResponse,
    summary='获取版本ID'
)
def get_file_version(file_version_params: FileVersionParams):
    logger.info(str(file_version_params))
    with ProcessReporter() as process_reporter:
        process_reporter.update_process(
            task_id=request_id.get(),
            status=TASK_STATUS.STARTED.value,
            process_info='文件版本获取中'
        )
        version_rec_model = VersionRec(file_version_params)
        try:
            version_rec_model.version_rec()
            process_reporter.update_process(
                task_id=request_id.get(),
                status=TASK_STATUS.COMPLETED.value,
                process_info='文件版本获取成功'
            )
            return MultiVersionResponse(success=True, data=version_rec_model.data)
        except Exception as e:
            logger.exception(e)
            process_reporter.update_process(
                task_id=request_id.get(),
                status=TASK_STATUS.FAILED.value,
                process_info=f'文件版本获取失败：{traceback.format_exc()}'
            )
            return MultiVersionResponse(success=False, data=[])


@app.post(
    '/indicator_query',
    tags=['File Parse', 'Inquire statement measures'],
    response_model=IndicatorResponse,
    summary='查询财报指标'
)
def indicator_query(indicator_params: IndicatorQueryParams):
    # 取得提交的参数
    knowledge_base_name = indicator_params.knowledge_base_name
    knowledge_base_id = indicator_params.knowledge_base_id
    file_id = indicator_params.file_id
    company_short_name = indicator_params.company_short_name
    company_full_name = indicator_params.company_full_name
    year = indicator_params.year
    period_type = indicator_params.period_type
    table_name = indicator_params.table_name

    # 如果table无值，则查询全部三张表，否则只查单张
    if not table_name:
        tables = ["consolidated_balance", "consolidated_income", "consolidated_cash_flow"]
    else:
        tables = [table_name]

    # 使用%s防止注入
    query_params = [knowledge_base_id]
    where = f'''knowledge_base_id = %s '''
    if knowledge_base_name:
        where += f'''AND knowledge_base_name = %s '''
        query_params.append(knowledge_base_name)
    if company_short_name:
        where += f'''AND company_short_name = %s '''
        query_params.append(company_short_name)
    if company_full_name:
        where += f'''AND company_full_name = %s '''
        query_params.append(company_full_name)
    if file_id:
        file_id_str = '(' + ','.join(["%s"] * len(file_id)) + ') '
        where += f'''AND file_id in ''' + file_id_str
        query_params.extend(file_id)
    if year:
        where += f'''AND year = %s '''
        query_params.append(year)
    if period_type:
        where += f'''AND period_type = %s '''
        query_params.append(period_type)
    query_params = tuple(query_params)

    sql_queries = []
    for name in tables:
        sql_query = f"Select id, company_full_name, company_short_name, year, period_type, date_type, indicator_name, indicator_raw, indicator_value, fixed_value, indicator_unit, indicator_value_position, indicator_value_page_size, indicator_value_offset,indicator_value_page_number, parsed_file_path, file_name, file_path, file_id, knowledge_base_name, knowledge_base_id, status, adopt From {name} Where {where}"
        sql_queries.append(sql_query)

    idx = request_id.get()  # 生成唯一id
    with ProcessReporter() as process_reporter:
        success, msg, task_id, results = process_reporter.indicate_execute_query(sql_queries, table_names=tables,
                                                                                 params=query_params,
                                                                                 request_id=idx)  # 执行查询任务
        if success:
            process_reporter.update_process(
                task_id=idx,
                status=TASK_STATUS.COMPLETED.value,
                process_info='财务指标查询成功。'
            )
        else:
            process_reporter.update_process(
                task_id=idx,
                status=TASK_STATUS.FAILED.value,
                process_info=f'财务指标查询失败。'
            )
        return IndicatorResponse(success=success, msg=msg, request_id=task_id, results=results)


@app.post(
    '/indicator_groupby',
    tags=['File Parse', 'Groupby extract'],
    response_model=IndicatorGroupbyResponse,
    summary='获取筛选项'
)
def indicator_groupby(indicator_groupby_params: IndicatorGroupbyParams):
    knowledge_base_id, file_id = indicator_groupby_params.knowledge_base_id, indicator_groupby_params.file_id
    tables = ["consolidated_balance", "consolidated_income", "consolidated_cash_flow"]
    answers = []
    task_id = request_id.get()
    with ProcessReporter() as process_reporter:
        try:
            for table in tables:
                query_params = [knowledge_base_id]
                where = f'''knowledge_base_id = %s '''
                placeholders = ','.join(['%s'] * len(file_id))
                if placeholders:
                    where += f'''AND file_id in ({placeholders}) '''
                    query_params.extend(file_id)
                query = f"Select company_short_name, company_full_name, year, period_type From {table} where {where} Group by company_short_name, company_full_name, year, period_type "
                results = process_reporter.dao.execute_query(query, tuple(query_params))
                for result in results:
                    result["table_name"] = table
                    answers.append(result)
            success = True
            msg = "查询筛选项成功"
            process_reporter.update_process(
                task_id=task_id,
                status=TASK_STATUS.COMPLETED.value,
                process_info='查询筛选项任务执行成功。'
            )
        except Exception as e:
            logger.info(repr(e))
            logger.info(traceback.format_exc())
            success = False
            msg = "查询筛选项失败"
            process_reporter.update_process(
                task_id=task_id,
                status=TASK_STATUS.COMPLETED.value,
                process_info='查询筛选项任务执行失败。'
            )
    return IndicatorGroupbyResponse(success=success, msg=msg, results=answers, request_id=task_id)


@app.post(
    '/indicator_modify',
    tags=['File Parse', 'Ref measures'],
    response_model=IndicatorResponse,
    summary='修改财报指标'
)
def indicator_modify(indicator_modify_params: IndicatorModifyParams):
    table_names, ref_ids, fixed_value, adopt_index, modified_by = (indicator_modify_params.table_names,
                                                                   indicator_modify_params.ref_ids,
                                                                   indicator_modify_params.fixed_value,
                                                                   indicator_modify_params.adopt_index,
                                                                   indicator_modify_params.modified_by)
    task_id = request_id.get()
    if len(table_names) != len(ref_ids):
        msg = "table_names与ref_ids长度不一致"
        success = False
        return IndicatorResponse(success=success, msg=msg, results=[], request_id=task_id)
    if fixed_value is None and adopt_index is None:
        msg = "fixed_value与adopt_index都为null"
        success = False
        return IndicatorResponse(success=success, msg=msg, results=[], request_id=task_id)

    with ProcessReporter() as process_reporter:
        success, msg = process_reporter.indicate_ref(table_names, ref_ids, fixed_value, adopt_index, modified_by)
        if success:
            process_reporter.update_process(
                task_id=task_id,
                status=TASK_STATUS.COMPLETED.value,
                process_info='指标修订任务执行成功。'
            )
        else:
            process_reporter.update_process(
                task_id=task_id,
                status=TASK_STATUS.FAILED.value,
                process_info=f'指标修订任务执行失败。'
            )
    return IndicatorResponse(success=success, msg=msg, results=[], request_id=task_id)


@app.post(
    '/parse/database_desc',
    tags=['Database Parse', 'Get database description'],
    response_model=DataBaseDescResponse,
    summary='获取数据库描述'
)
def get_database_desc(database_desc: DatabaseDescConfig):
    try:
        database_model = DatabaseDesc(database_desc)
        summary = database_model.data_base_desc_build()
        return DataBaseDescResponse(success=True, code=200, msg=f'获取数据库描述成功', table_description=summary)
    except Exception as e:
        # traceback.print_exc()
        return DataBaseDescResponse(code=500, msg=f'获取数据库描述失败', table_description="")


@app.post(
    '/indicator_add',
    tags=['Database Parse', 'Get database description'],
    response_model=IndicatorResponse,
    summary='获取数据库描述'
)
def indicator_add(indicator_add_params: IndicatorAddParams):
    knowledge_base_id, knowledge_base_name, table_name, company_short_name, company_full_name, year, period_type, date_type, indicator_name, fixed_value, indicator_unit, creator_id, indicator_raw, file_path = indicator_add_params.knowledge_base_id, indicator_add_params.knowledge_base_name, indicator_add_params.table_name, indicator_add_params.company_short_name, indicator_add_params.company_full_name, indicator_add_params.year, indicator_add_params.period_type, indicator_add_params.date_type, indicator_add_params.indicator_name, indicator_add_params.fixed_value, indicator_add_params.indicator_unit, indicator_add_params.creator_id, indicator_add_params.indicator_raw, indicator_add_params.file_path
    task_id = request_id.get()
    if None in [table_name, fixed_value, indicator_name]:
        msg = "缺少必要参数："
        l = []
        if table_name is None:
            l.append('table_name')
        if fixed_value is None:
            l.append('fixed_value')
        if indicator_name is None:
            l.append('indicator_name')
        msg = msg + '、'.join(l)
        success = False
        return IndicatorResponse(success=success, msg=msg, results=[], request_id=task_id)
    if company_short_name is None and company_full_name is None:
        msg = '公司全称与公司简称均为null'
        success = False
        return IndicatorResponse(success=success, msg=msg, results=[], request_id=task_id)

    with ProcessReporter() as process_reporter:
        success, msg = process_reporter.indicate_add(knowledge_base_id, knowledge_base_name, table_name,
                                                     company_short_name, company_full_name, year, period_type,
                                                     date_type, indicator_name, fixed_value, indicator_unit, creator_id,
                                                     indicator_raw, file_path)
        if success:
            process_reporter.update_process(
                task_id=task_id,
                status=TASK_STATUS.COMPLETED.value,
                process_info='指标新增任务执行成功。'
            )
        else:
            process_reporter.update_process(
                task_id=task_id,
                status=TASK_STATUS.FAILED.value,
                process_info=f'指标新增任务执行失败。'
            )
    return IndicatorResponse(success=success, msg=msg, results=[], request_id=task_id)
