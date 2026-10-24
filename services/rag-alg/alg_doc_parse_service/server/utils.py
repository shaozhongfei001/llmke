import base64
import io
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
    with requests.post(
            doc_parse_config.config['minio-upload'].format(ip=gateway_ip, port=gateway_port),
            data={'kbId': knowledge_base_id, 'fileId': file_id, 'userId': user_id},
            files=[('file', (file_name + '.md', file_stream))] + image_streams + table_streams
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
