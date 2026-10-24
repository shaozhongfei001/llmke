import base64
import json
import time
from pathlib import Path
from typing import Iterator, Any
from urllib.parse import urlparse, parse_qs

import requests
from fastapi import HTTPException
from langchain_core.document_loaders import Blob

from log import logger
from server.nacos_utils import DocParseConfig
from server.utils import compile_extension_regex_ignore_case
from .base_parser import BaseParser
from .utils import is_split_table
from ..output_object import ParsedTable, ParsedTableMetadata, ParsedText, ParsedTextMetadata, ParsedImage, \
    ParsedImageMetadata


def _position_formatter(position: list[int]) -> list[list[int]]:
    """
    将代表文本框四个点的位置的8个数字转化为四对坐标
    """
    assert len(position) == 8, '合合服务位置信息异常'
    return [[position[index], position[index + 1]] for index in range(0, len(position) - 1, 2)]


class TextInParser(BaseParser):
    supported_formats = compile_extension_regex_ignore_case([
        '.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'
    ])

    def __init__(self, polling_time=5.0):
        self.polling_time = polling_time

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        file_path = Path(blob.path)
        api_endpoints = DocParseConfig().config['text_in']['endpoint']
        files = [(
            'documents',
            (file_path.name, blob.as_bytes())
        )]

        # 创建解析任务
        with requests.post(api_endpoints['create_task'], files=files) as response:
            status_code = response.status_code
            if status_code != 200:
                raise HTTPException(status_code, '合合解析任务创建失败：' + response.text)
            result = response.json()

        # 处理创建任务异常
        if result['code'] != 200:
            logger.error(json.dumps(result, indent=4, ensure_ascii=False))
            raise Exception('合合解析任务创建失败：' + result['msg'])

        # 获取任务ID
        data = {
            'task_id': result['data']['task_ids'][0]
        }

        # 初始化是否解析成功的信号变量
        is_parsed = False

        # 初始化最大轮询次数
        polling_count = int(1200 / self.polling_time)
        pooling_round = 0

        # 轮询获取解析结果
        logger.info('waiting...')
        while pooling_round < polling_count:
            # 尝试获取解析结果
            with requests.post(api_endpoints['task_result'], json=data) as response:
                # 处理HTTP异常
                status_code = response.status_code
                if status_code != 200:
                    raise HTTPException(status_code, '合合解析结果获取失败：' + response.text)

                # 响应转成dict
                result = response.json()

            code = result['code']

            # 合合内部异常处理
            if code == 10703:
                logger.error(json.dumps(result, indent=4, ensure_ascii=False))
                raise Exception('合合解析失败：' + result['msg'])

            # 判断是否有解析结果
            if code == 200:
                if result['data']['status'] != 2:
                    logger.error(json.dumps(result, indent=4, ensure_ascii=False))
                    raise ValueError('合合未知错误')
                parsed_result = result['data']['parse_result']

                # 标志成功解析（不会抛出超时异常）
                is_parsed = True

                if parsed_result['md_detail']:
                    for item in parsed_result['md_detail']:
                        # 获取文本框位置
                        position = _position_formatter(item['position'])

                        # 设置metadata
                        # 包括：源文件路径、文本框位置、页码
                        page_number = item['page_id']
                        metadata: dict[str, Any] = {
                            'source': blob.path,
                            'file_path': blob.path,
                            'position': [position],
                            'page_number': [page_number],
                        }

                        # 设置metadata
                        # 根据页码获得页面大小
                        page = parsed_result['pages'][metadata['page_number'][0] - 1]
                        metadata['page_size'] = [[page['width'], page['height']]]

                        # 判断是否为页脚页眉
                        # 判断是否需要过滤页脚页眉
                        if item.get('content', 0):
                            metadata['need_filtered'] = True

                        if item['type'] == 'paragraph':
                            yield ParsedText(
                                page_content=item['text'],
                                metadata=ParsedTextMetadata(**metadata)
                            )
                        elif item['type'] == 'image':
                            try:
                                image_url = urlparse('http://' + item['image_url'])
                                image_name = parse_qs(image_url.query)['image_id'][0]
                                image_url = api_endpoints['image_download'].format(image_name=image_name)
                                image_bytes = requests.get(image_url).content
                                metadata['base64'] = base64.b64encode(image_bytes).decode()
                            except Exception as e:
                                logger.warning(e)
                                logger.warning('无base64str')
                            metadata['image_size'] = [position[1][0] - position[0][0], position[2][1] - position[0][1]]

                            yield ParsedImage(
                                page_content=item['text'],
                                metadata=ParsedImageMetadata(**metadata)
                            )
                        elif item['type'] == 'table':
                            # 考虑同类型跨页表格被合并（每页含表头）
                            flag_split = False
                            # 过滤不跨页
                            if 'text' in item and 'split_section_positions' in item and 'cells' in item:
                                flag_split, cells_split, html_table_split = is_split_table(item['text'], item['split_section_positions'], item['cells'])
                            if flag_split:
                                for cells_current, html_table_current, split_section_positions_current, page_id_current in  zip(cells_split, html_table_split, item['split_section_positions'], item['split_section_page_ids']):
                                    metadata['page_number'] = [page_id_current]
                                    metadata['postion'] = [_position_formatter(split_section_positions_current)]
                                    page = parsed_result['pages'][metadata['page_number'][0] - 1]
                                    metadata['page_size'] = [[page['width'], page['height']]]
                                    yield ParsedTable(
                                        page_content=html_table_current,
                                        metadata=ParsedTableMetadata(**metadata)
                                    )
                            else:
                                yield ParsedTable(
                                    page_content=item['text'],
                                    metadata=ParsedTableMetadata(**metadata)
                                )
                else:
                    logger.warning(f'合合返回md_detail结果为空')

                break
            elif code == 10702:
                pooling_round += 1

            # 等待下一次获取结果的机会
            time.sleep(self.polling_time)

        if not is_parsed:
            raise Exception(f'合合解析超时：{data}')
