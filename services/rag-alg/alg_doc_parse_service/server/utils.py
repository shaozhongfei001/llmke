import base64
import hashlib
import io
import json
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal, Callable, Generator, TYPE_CHECKING

import requests
from fastapi import HTTPException

from log import logger
from .minio_utils import MinioFile
from .nacos_utils import DocParseConfig

if TYPE_CHECKING:
    from deepdoc.output_object import ParsedImage, ParsedTable


def try_catch(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(e)
            raise e

    return wrapper


def load_local_ocr(device: Literal['gpu', 'cpu'] = 'cpu'):
    from .ocr_pool import ocr_pool

    return ocr_pool.load_ocrs(os.environ.get('OCR_PATH', './ocr_models'), device=device)


def run_in_thread_pool(
        func: Callable,
        params: list[dict] | None = None,
        stable_order=False,
        max_workers=None
) -> Generator:
    """
    在线程池中批量运行任务，并将运行结果以生成器的形式返回。
    请确保任务中的所有操作是线程安全的，任务函数请全部使用关键字参数。
    """

    if params is None:
        params = []
    tasks = []

    if max_workers is None or max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for kwargs in params:
                thread = pool.submit(func, **kwargs)
                tasks.append(thread)

            if not stable_order:
                for obj in as_completed(tasks):
                    yield obj.result()
            else:
                for task in tasks:
                    yield task.result()
    else:
        for kwargs in params:
            yield func(**kwargs)


def create_document_id(file_path):
    text = str(file_path)
    document_id = base64.b64encode(text.encode()).decode()
    return document_id


def create_uuid():
    pk_value = uuid.uuid4().int & ((1 << 63) - 1)  # 取 63 位保证在有符号范围内
    if pk_value > 9223372036854775807:  # INT64 的最大正数
        pk_value = pk_value - (1 << 64)  # 转换为负数范围
    return pk_value


# ---------------------------------------------------------------------------
# R14-C-FIX-08：内容寻址主键（解析服务与索引写入层必须用**同一算法、同一字段**）
#
# 背景（A-data 的 e2e 证据）：controller.py 在交给索引层之前给每个 chunk 写死了随机 pk，
# 索引层"metadata.pk 存在则优先"被短路，导致同一文件重解析 ES _id / Milvus pk 每次都变，
# 图里的 chunk_pk_list、引用回填全部随之悬空。
#
# 约束（与 A-data 对齐，逐字符一致）：
#   * index_name 必须 .lower()（ES 侧 is_index_lower() 已如此，Milvus 侧已对齐）
#   * seq 传 parsed_chunk_index（controller.py:405 赋的全局序号；最终 chunk_index 只能在末尾
#     :644-646 才知道，不能前推）
#   * None 一律走空串；file_id 两次解析必须同类型（都 int 或都 str 由调用方保证同源）
#   * version 不进种子：document_id 已是 base64(含 /V0/ 的路径)，版本变化天然换 id，
#     再加 version 会在"有的行 version=null、有的 V0"时漂移
# ---------------------------------------------------------------------------
def _pk_from_seed(seed: str) -> int:
    return int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:15], 16)


def create_chunk_pk(index_name, document_id, file_id, seq, page_content) -> int:
    """文本/图片 chunk 主键：chunk|index_name|file_id|seq|sha1(text)

    R14-A-FIX-18（TL 批准）：**种子不再含 document_id**。
    document_id 由"谁调用了解析"的路径形态决定（完整对象键 vs 裸文件名会算出两个不同的
    base64），一旦进种子，"谁调的"就决定了"存什么 id"：
      r12-rag/kb_9/…/x.docx  -> cjEyLXJhZy9rYl85L1IxMkZJWC1wcm9kdWN0LWxv…
      x.docx                 -> cHJvZHVjdC1sb2FuKDEpLmRvY3g=
    → 同一文件两种入口得到两个 pk → 图侧 `chunk_pk_list`（存的是抽取时刻的 ES `_id`）立刻悬空，
    `exact_chunk=0` 永远修不好。去掉后 pk 只由 (库, 文件, 块序号, 内容哈希) 决定，跨入口稳定。
    签名保留，调用方（controller.py:410/512/585）无需改动。
    """
    parts = (
        "chunk",
        "" if index_name is None else str(index_name).lower(),
        file_id,
        seq,
        hashlib.sha1(str(page_content).encode("utf-8")).hexdigest(),
    )
    return _pk_from_seed("|".join("" if p is None else str(p) for p in parts))


def create_table_pk(index_name, document_id, file_id, table_ordinal) -> int:
    """表格（或其全表摘要）的稳定 id：table|index_name|file_id|table_ordinal。

    R14-A-FIX-18：同样去掉 document_id（理由见 create_chunk_pk）。
    注意：绝不能用正文哈希 —— table_summary 的正文本是 LLM 生成的，同一张表两次解析文字不同，
    用正文做种子必然每次漂移；`table_ordinal` 已足够区分同文件内的多张表。
    """
    parts = (
        "table",
        "" if index_name is None else str(index_name).lower(),
        file_id,
        table_ordinal,
    )
    return _pk_from_seed("|".join("" if p is None else str(p) for p in parts))


def create_table_chunk_pk(table_id, table_pos) -> int:
    """表格块主键：table_chunk|<table_id>|<规范化 table_pos>。

    table_pos 是嵌套 list，必须先规范序列化（sort_keys + 紧凑分隔符），否则 [0,0] 与 [[0,0]]
    之类的写法差异会让同一块算出不同 id。
    """
    pos = json.dumps(table_pos, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _pk_from_seed(f"table_chunk|{table_id}|{pos}")


def save_to_minio(
        text: str,
        images: list['ParsedImage'],
        tables: list['ParsedTable'],
        knowledge_base_id: int,
        user_id: str,
        file_name: str,
        file_id: int,
        txt_path: str | None = None
):
    logger.info(f'保存解析结果到minio中：{file_name}')

    # 字符串编码为文件流
    text_bytes = text.encode()
    file_stream = io.BytesIO(text_bytes)
    file_stream.seek(0)

    # base64解码为文件流
    image_streams = []
    for image_index, image in enumerate(images):
        if image.metadata.base64:
            image_stream = io.BytesIO(base64.b64decode(image.metadata.base64))
            image_stream.seek(0)
            image_streams.append((
                'imagesFiles',
                (
                    f'image-{image_index}.{image.metadata.ext.lstrip(".")}',
                    image_stream
                )
            ))
        else:
            logger.warning(f'{file_name}的第{image_index + 1}张图片没有base64！')

    table_streams = []
    for table_index, table in enumerate(tables):
        table.metadata.table_name = (f'table-{table_index}' + (
            f'-{table.metadata.table_name}' if table.metadata.table_name else ''))[:70]
        table_stream = io.BytesIO(table.page_content.encode())
        table_stream.seek(0)
        table_streams.append((
            'tableFiles',
            (
                f'{table.metadata.table_name}.md',
                table_stream
            )
        ))

    # 调用解析保存接口
    doc_parse_config = DocParseConfig()
    gateway_ip = doc_parse_config.configs['java-common']['server']['host-ip']
    gateway_port = doc_parse_config.configs['java-gateway']['server']['port']
    # R13-SEC-05：网关已不再无条件放行内部回写入口，必须带共享令牌
    internal_token = doc_parse_config.config.get('internal-token') or ''
    with requests.post(
            doc_parse_config.config['minio-upload'].format(ip=gateway_ip, port=gateway_port),
            data={'kbId': knowledge_base_id, 'fileId': file_id, 'userId': user_id},
            files=[('file', (file_name + '.md', file_stream))] + image_streams + table_streams,
            headers={'X-Internal-Token': internal_token} if internal_token else {}
    ) as response:
        status_code = response.status_code
        if status_code != 200:
            raise HTTPException(status_code, 'minio保存失败：' + response.text)

        response = response.json()
        if not response['success']:
            raise Exception('minio保存失败：' + response['errorMsg'])

    if txt_path:
        file_stream.seek(0)
        minio_file = MinioFile(txt_path)
        minio_file.put_object(file_stream, len(text_bytes))

    # 更新图片metadata的image_path
    image_paths = response['data']['imagePaths']
    # assert len(image_paths) == len(images), f'图片路径数量错误：{len(image_paths)}。正确数量应该是{len(images)}'
    for image, image_path in zip(images, image_paths):
        if image.metadata.base64:
            image.metadata.image_path = image_path


def compile_extension_regex_ignore_case(extensions: list[str]) -> list[re.Pattern[str]]:
    return [re.compile('^[\s\S]*' + re.escape(expression) + '$', re.IGNORECASE) for expression in extensions]


def image_need_multi_modal(image_size: list[int | float], boxes: list[list[list[int | float]]]):
    # qwen2-vl会过滤掉边长小于28的图片
    if min(image_size) <= 28:
        logger.warning('多模态输入图片过小')
        return False

    text_area = 0
    for box in boxes:
        text_area += (box[1][0] - box[0][0]) * (box[2][1] - box[0][1])

    if image_size:
        image_area = image_size[0] * image_size[1]
        if text_area / image_area < 0.3:
            return True

    logger.info('图片大部分是文字内容.')
    return False
