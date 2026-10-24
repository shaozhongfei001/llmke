import json
import time
from io import BytesIO
from pathlib import Path
from typing import Iterator

from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_credentials.models import Config as CredConfig
from alibabacloud_docmind_api20220711 import models as docmind_api20220711_models
from alibabacloud_docmind_api20220711.client import Client as docmind_api20220711Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from langchain_core.document_loaders import Blob

from log import logger
from server.nacos_utils import DocParseConfig
from server.utils import compile_extension_regex_ignore_case
from .base_parser import BaseParser
from ..output_object import ParsedText, ParsedTextMetadata


class AliParser(BaseParser):
    supported_formats = compile_extension_regex_ignore_case([
        '.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.bmp', '.gif'
    ])

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        file_path = Path(blob.path)
        nacos_ali_config = DocParseConfig().config['ali']

        # 使用默认凭证初始化Credentials Client。
        credential = CredClient(
            CredConfig(
                type='access_key',
                access_key_id=nacos_ali_config['access_key'],
                access_key_secret=nacos_ali_config['access_secret_key'],
            )
        ).get_credential()
        config = open_api_models.Config(
            # 通过credentials获取配置中的AccessKey ID
            access_key_id=credential.access_key_id,
            # 通过credentials获取配置中的AccessKey Secret
            access_key_secret=credential.access_key_secret,
            endpoint=nacos_ali_config['endpoint'],
            read_timeout=nacos_ali_config.get('read_timeout', 60000),
            connect_timeout=nacos_ali_config.get('connect_timeout', 60000)
        )

        client = docmind_api20220711Client(config)
        request = docmind_api20220711_models.SubmitDocStructureJobAdvanceRequest(
            # file_url_object : 本地文件流
            file_url_object=BytesIO(blob.as_bytes()),
            # file_name ：文件名称。名称必须包含文件类型
            file_name=file_path.name,
            structure_type='layout'
            # file_name_extension : 文件后缀格式。与文件名二选一
            # file_name_extension='pdf'
        )
        runtime = util_models.RuntimeOptions(
            http_proxy=nacos_ali_config.get('http_proxy', None),
            https_proxy=nacos_ali_config.get('https_proxy', None),
            socks_5proxy=nacos_ali_config.get('socks_5proxy', None)
        )

        # 复制代码运行请自行打印 API 的返回值
        response = client.submit_doc_structure_job_advance(request, runtime)
        logger.debug(response)

        if response.status_code != 200:
            raise Exception(response.body.message)

        document_id = response.body.data.id

        parsing_result = None
        for _ in range(60):
            logger.info('waiting...')
            request = docmind_api20220711_models.GetDocStructureResultRequest(
                # id :  任务提交接口返回的id
                id=document_id
            )
            # 复制代码运行请自行打印 API 的返回值
            response = client.get_doc_structure_result_with_options(request, runtime)

            if response.status_code != 200:
                raise Exception(response.body.message)

            # API返回值格式层级为 body -> data -> 具体属性。可根据业务需要打印相应的结果。获取属性值均以小写开头
            # 获取异步任务处理情况,可根据response.body.completed判断是否需要继续轮询结果
            if response.body.completed:
                logger.debug(json.dumps(response.body.data, indent=4, ensure_ascii=False))

                if response.body.status == 'Success':
                    parsing_result = response.body.data
                    break
                else:
                    raise Exception(response.body.message)

            time.sleep(10)

        if not parsing_result:
            raise TimeoutError('文档解析超时')

        table_name = None
        for layout in parsing_result['layouts']:
            if layout['type'] in nacos_ali_config['garbage_types']:
                continue

            if layout['type'] == 'table_name':
                table_name = layout['text']
                continue
            elif layout['type'] == 'table':
                col_number = layout['numCol']

                rows = ['<table>', f'<caption>{table_name}</caption>'] if table_name else ['<table>']
                table_name = None

                row_str = '<tr>'
                for cell in layout['cells']:
                    if cell['cellId'] % col_number == 0:
                        row_str += '</tr>'
                        rows.append(row_str)
                        row_str = '<tr>'

                    cell_str = []
                    for cell_layout in cell['layouts']:
                        for block in cell_layout['blocks']:
                            cell_str.append(block['text'])
                    cell_str = ''.join(cell_str)
                    row_str += f'<td>{repr(cell_str)[1:-1]}</td>'
                row_str += '</tr>'
                rows.append(row_str)
                rows.append('</table>')

                page_content = '\n'.join(rows)
            else:
                page_content = layout['text']

            yield ParsedText(
                page_content=page_content,
                metadata=ParsedTextMetadata(**{
                    'position': [list(position.values()) for position in layout['pos']],
                    'type': nacos_ali_config['type_dict'].get(layout['type'], 'text'),
                    'source': blob.source,
                    'file_path': blob.path
                })
            )
