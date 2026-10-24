import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterator

import requests
from langchain_core.document_loaders import Blob

from server.nacos_utils import DocParseConfig
from server.utils import compile_extension_regex_ignore_case
from .base_parser import BaseParser
from ..output_object import (
    ParsedText, ParsedTextMetadata,
    ParsedTable, ParsedTableMetadata,
    ParsedImage, ParsedImageMetadata
)

_SUPPORT_FORMATS = compile_extension_regex_ignore_case(['.pdf', '.docx'])


def _get_authorized_headers(access_key, access_secret_key, api_path):
    headers = {
        'accept': 'application/json',
        'datetime': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'signature-nonce': uuid.uuid4().hex
    }
    signature = '\n'.join(['POST'] + list(headers.values()) + [api_path])
    hmac_sha1 = hmac.new(access_secret_key.encode(), signature.encode(), hashlib.sha1).hexdigest().encode()
    headers['authorization'] = f'ak {access_key}:{base64.b64encode(hmac_sha1).decode()}'

    return headers


class FudanParser(BaseParser):
    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        nacos_fudan_config = DocParseConfig().config['fudan']
        file_path = Path(blob.path)
        files = [(
            'file',
            (
                file_path.name,
                blob.as_bytes()
            )
        )]

        with requests.post(nacos_fudan_config['endpoint'],
                           headers=_get_authorized_headers(nacos_fudan_config['access_key'],
                                                           nacos_fudan_config['access_secret_key'],
                                                           nacos_fudan_config['path']),
                           data=nacos_fudan_config['fixed_data'],
                           files=files) as response:
            if response.status_code != 200:
                raise Exception(response.text)

            result = response.json()

        if not result['result']:
            raise Exception(f'复旦文本解析服务解析失败：\n{json.dumps(result, indent=4, ensure_ascii=False)}')

        for section in result['result']['tree']:
            page_number = section.get('page_no', None)
            metadata = {
                'source': blob.path,
                'file_path': blob.path,
                'page_number': [page_number + 1] if page_number else [],
            }

            if section['type'] in nacos_fudan_config['garbage_types']:
                metadata['need_filtered'] = True

            position = section.get('positions', None)
            if position:
                metadata['page_size'] = [[position['page_width'], position['page_height']]]
                position = position['bbox'][0]
                metadata['position'] = [[
                    position[:2],  # 左上
                    [position[2], position[1]],  # 右上
                    position[2:],  # 右下
                    [position[0], position[3]]  # 左下
                ]]

            if section['type'] == 'TABLE':
                table_cells = ParsedTable.get_table_cells(
                    section,
                    get_rows_func=lambda x: x['children'],
                    get_row_span_from_cell=lambda x: int(x.get('rowSpan', '1')),
                    get_col_span_from_cell=lambda x: int(x.get('colSpan', '1')),
                    get_text_from_cell=lambda x: x.get('text', '')
                )
                yield ParsedTable(
                    table_cells=table_cells,
                    metadata=ParsedTableMetadata(**metadata)
                )
            elif section['type'] == 'IMAGE':
                metadata['base64'] = section['base64']
                yield ParsedImage(
                    page_content=section['text'],
                    metadata=ParsedImageMetadata(**metadata)
                )
            else:
                yield ParsedText(
                    page_content=section['text'],
                    metadata=ParsedTextMetadata(**metadata)
                )
