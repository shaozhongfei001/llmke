import base64
import copy
import json
import os
import shutil
from json import JSONDecodeError
from pathlib import Path
from typing import Iterator

import requests
from requests import RequestException, Timeout
from langchain_core.document_loaders import Blob

from log import request_id, logger
from server.nacos_utils import DocParseConfig
from server.utils import compile_extension_regex_ignore_case
from server.exception.custom_exception import (
    FileParseFailedError,
    MineruRequestTimeoutError,
    MineruResourceInsufficientError,
    MineruServiceUnavailableError, ModelRequestInternalError,
)
from .base_parser import BaseParser
from ..output_object import ParsedText, ParsedTextMetadata, ParsedImageMetadata, ParsedImage, ParsedTable, \
    ParsedTableMetadata

try:
    from magic_pdf.config.enums import SupportedPdfParseMethod
    from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
    from magic_pdf.data.dataset import PymuDocDataset, ImageDataset
    from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
    from magic_pdf.utils.office_to_pdf import convert_file_to_pdf
    magic_pdf = True
except ModuleNotFoundError:
    magic_pdf = False
    logger.info('未安装minerU，无法使用build-in sdk只能使用webapi，如需使用请运行“pip install -U "magic-pdf[core]"”。')

MINERU_TEMP_DIR = Path('mineru_temp_dir')
os.makedirs(MINERU_TEMP_DIR, exist_ok=True)


class MinerUParser(BaseParser):
    supported_formats = compile_extension_regex_ignore_case([
        '.pdf',
        '.jsonl',
        '.doc', '.docx', '.ppt', '.pptx',
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'
    ])

    @classmethod
    def _position_formatter(cls, position: list[float]) -> list[list[float]]:
        """
        将代表文本框四个点的位置的4个数字转化为四对坐标
        """
        assert len(position) == 4, 'MinerU位置信息异常'
        return [
            [position[0], position[1]],
            [position[2], position[1]],
            [position[2], position[3]],
            [position[0], position[3]]
        ]

    @classmethod
    def _get_position(cls, para_block):
        if para_block['bbox']:
            position = para_block['bbox']
        else:
            if para_block['blocks']:
                position = para_block['blocks'][0]['bbox']
            else:
                raise ValueError('无法找到block的位置')
        return cls._position_formatter(position)

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        nacos_config = DocParseConfig().config['mineru']
        file_path = Path(blob.path)
        file_name = file_path.name

        temp_file_dir = MINERU_TEMP_DIR / (file_name + request_id.get())
        image_dir = temp_file_dir / 'image'
        convert_dir = temp_file_dir / 'convert'
        os.makedirs(image_dir, exist_ok=True)
        os.makedirs(convert_dir, exist_ok=True)

        try:
            build_in = nacos_config['build-in']
            none_build_in_result = None
            backend = nacos_config['backend']
            mineru_version = str(nacos_config['version'])

            if build_in:
                if not magic_pdf:
                    raise ModelRequestInternalError('minerU未安装')

                image_writer = FileBasedDataWriter(str(image_dir))
                reader = FileBasedDataReader()

                try:
                    if self.valid_file_name(
                            file_name,
                            compile_extension_regex_ignore_case(['.doc', '.docx', '.ppt', '.pptx'])
                    ):
                        origin_file_path = convert_dir / file_name
                        with open(origin_file_path, 'wb') as f:
                            f.write(blob.as_bytes())

                        convert_file_to_pdf(origin_file_path, convert_dir)
                        converted_file_path = convert_dir / (file_path.stem + '.pdf')

                        dataset = PymuDocDataset(reader.read(str(converted_file_path)))
                    elif self.valid_file_name(file_name, compile_extension_regex_ignore_case(['.pdf'])):
                        dataset = PymuDocDataset(blob.as_bytes())
                    else:
                        dataset = ImageDataset(blob.as_bytes())
                except Exception as exc:
                    raise FileParseFailedError(f'mineru构建数据集失败：{exc}') from exc

                if dataset.classify() == SupportedPdfParseMethod.OCR:
                    infer_result = dataset.apply(doc_analyze, ocr=True)
                    pipe_result = infer_result.pipe_ocr_mode(image_writer)
                else:
                    infer_result = dataset.apply(doc_analyze, ocr=False)
                    pipe_result = infer_result.pipe_txt_mode(image_writer)

                middle_json = pipe_result.get_middle_json()
            else:
                files = [(
                    'files',
                    (file_name, blob.as_bytes())
                )]
                payload = {
                    'backend': backend,
                    'return_middle_json': True,
                    'return_images': True
                }
                
                url = nacos_config['endpoint']

                logger.info(f'Mineru API请求信息：version={mineru_version},URL={url}, payload={payload}')
                try:
                    with requests.post(url, files=files, data=payload) as response:
                        status_code = response.status_code
                        if status_code != 200:
                            response_text = response.text
                            message = f'mineru解析失败：{response_text}'
                            lower_text = response_text.lower()
                            if status_code == 504 or 'timeout' in lower_text:
                                raise MineruRequestTimeoutError(message)
                            if status_code in {507, 509} or 'out of memory' in lower_text:
                                raise MineruResourceInsufficientError(message)
                            raise MineruServiceUnavailableError(message)
                        try:
                            result = response.json()
                        except JSONDecodeError as e:
                            logger.error('mineru解析失败：' + response.text)
                            raise ModelRequestInternalError('mineru响应格式错误') from e
                except Timeout as exc:
                    raise MineruRequestTimeoutError('mineru请求超时') from exc
                except RequestException as exc:
                    raise ModelRequestInternalError(f'mineru请求失败：{exc}') from exc

                none_build_in_result = result['results'][file_path.stem]
                middle_json = none_build_in_result['middle_json']

            pages = json.loads(middle_json)['pdf_info']
            for page in pages:
                page_index = None
                page_size = None
                if not build_in:
                    page_index = page['page_idx']
                    page_size = page['page_size']

                # mineru 2.5版本且backend为pipeline时，段落信息在preproc_blocks字段中
                # page_blocks = page.get('preproc_blocks', []) if mineru_version=="2.5" and backend =='pipeline'  else page.get('para_blocks', [])
                page_blocks = page['para_blocks']
                for para_block in page_blocks:
                    position = self._get_position(para_block)
                    metadata = {
                        'source': blob.path,
                        'file_path': blob.path,
                        'position': [position],
                        'page_number': [
                            (int(para_block['page_num'].split('_')[-1]) if build_in else page_index) + 1
                        ],
                        'page_size': [para_block['page_size'] if build_in else page_size],
                    }

                    if para_block['type'] == 'table':
                        result = None
                        table_name = ''
                        table_footnote = ''

                        for block in para_block['blocks']:
                            contents = []
                            for line in block['lines']:
                                for span in line['spans']:
                                    if block['type'] == 'table_body':
                                        if 'html' in span.keys():
                                            contents.append(span['html'])
                                    else:
                                        # table_footnote和table_caption
                                        contents.append(span['content'])

                            if block['type'] == 'table_caption':
                                table_name = '\n'.join(contents)
                            elif block['type'] == 'table_body':
                                page_content = '\n'.join(contents)
                                result = ParsedTable(
                                    page_content=page_content,
                                    metadata=ParsedTableMetadata(**metadata)
                                )
                            else:
                                # table footnote
                                table_footnote = '\n'.join(contents)

                        if result:
                            result.metadata.table_name = table_name
                            result.metadata.table_footnote = table_footnote
                            yield result
                        else:
                            yield ParsedText(
                                page_content=' '.join([table_name, table_footnote]),
                                metadata=ParsedTextMetadata(**metadata)
                            )
                    elif para_block['type'] == 'image':
                        # 先遍历图片的blocks来确定caption
                        image_caption = None
                        for block in para_block['blocks']:
                            if block['type'] == 'image_caption':
                                caption_metadata = copy.deepcopy(metadata)
                                caption_metadata['position'] = [self._get_position(para_block)]

                                contents = []
                                for line in block['lines']:
                                    for span in line['spans']:
                                        contents.append(span['content'])

                                image_caption = ParsedText(
                                    page_content='\n'.join(contents),
                                    metadata=ParsedTextMetadata(**caption_metadata)
                                )

                                break

                        for block in para_block['blocks']:
                            if block['type'] == 'image_footnote':
                                contents = []
                                for line in block['lines']:
                                    for span in line['spans']:
                                        contents.append(span['content'])

                                position = self._get_position(para_block)
                                if image_caption:
                                    image_caption.metadata.position.append(position)
                                    image_caption.page_content += '\n' + '\n'.join(contents)
                                else:
                                    caption_metadata = copy.deepcopy(metadata)
                                    caption_metadata.update({'position': [position]})

                                    image_caption = ParsedText(
                                        page_content='\n'.join(contents),
                                        metadata=ParsedTextMetadata(**caption_metadata)
                                    )

                                break

                        if image_caption:
                            yield image_caption

                        # 后拿到图片来关联caption
                        for block in para_block['blocks']:
                            if block['type'] == 'image_body' and block['lines']:
                                image_path = Path(block['lines'][0]['spans'][0]['image_path'])
                                if build_in:
                                    with open(image_dir / image_path, 'rb') as f:
                                        metadata['base64'] = base64.b64encode(f.read()).decode()
                                else:
                                    metadata['base64'] = none_build_in_result['images'][image_path.name].split(',')[-1]

                                metadata['image_size'] = [position[1][0] - position[0][0],
                                                          position[2][1] - position[0][1]]

                                if image_caption:
                                    metadata['caption_nearby'] = 'previous'

                                yield ParsedImage(
                                    page_content='',
                                    metadata=ParsedImageMetadata(**metadata)
                                )
                                break
                         

                    else:
                        contents = []
                        if "blocks" in para_block :
                            for block in para_block['blocks']:
                                for line in block['lines']:
                                    for span in line['spans']:
                                        try:
                                            contents.append(span['content'])
                                        except:
                                            pass
                                
                        else:
                            for line in para_block['lines']:
                                for span in line['spans']:
                                    try:
                                        contents.append(span['content'])
                                    except:
                                        continue

                        yield ParsedText(
                            page_content='\n'.join(contents),
                            metadata=ParsedTextMetadata(**metadata)
                        )
        finally:
            shutil.rmtree(temp_file_dir)
