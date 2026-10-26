import base64
import datetime
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from bs4 import BeautifulSoup
from langchain_core.document_loaders import Blob
from tqdm import tqdm

from deepdoc.output_object import ParsedImage, ParsedText, ParsedTable, ParsedTextMetadata
from deepdoc.parser import (
    AliParser,
    CSVParser,
    DOCParser, DOCXParser,
    ExcelParser,
    FudanParser,
    HTMLParser,
    ImageParser,
    MinerUParser,
    PDFParser,
    PPTParser,
    TextInParser,
    TXTParser,
    WPSParser
)
from log import logger, request_id, set_request_id
from server.api_param import ParseParams, FileParams
from server.minio_utils import MinioFile
from server.multi_modal_utils import MultiModalClient, PROMPT_TEMPLATE, QUERY, MultiModalMessage
from server.nacos_utils import DocParseConfig
from server.exception.base import ApiError
from server.exception.custom_exception import FileParseFailedError
from server.utils import create_document_id, run_in_thread_pool, save_to_minio, image_need_multi_modal


@dataclass
class LoadResult:
    success: bool = field(metadata={'description': '是否成功'})
    file_path: str = field(metadata={'description': '文件的minio路径'})
    file_id: int = field(metadata={'description': '文件id'})
    exception: Exception | None = field(metadata={'description': '如果失败，对应的异常'}, default=None)
    documents: list[ParsedText] | None = field(metadata={'description': '成功对应的结果'}, default=None)
    revise_date: str | None = field(metadata={'description': '文件可能包含的最新修订日期'}, default=None)

    def __post_init__(self):
        if not self.success:
            if not (self.exception and self.file_path):
                raise ValueError('读取文件失败时，必须返回异常和文件路径')
        else:
            if self.documents is None:
                raise ValueError('读取文件成功时，必须返回对应的Document列表')

        return self


def _parse_html_table(html_table):
    soup = BeautifulSoup(html_table, 'html.parser')
    table = soup.find('table')

    # 获取表头
    logger.debug(table)
    headers = [th.get_text(strip=True) for th in table.find_all('tr')[1].find_all('td')]
    title = table.find("caption")
    if title:
        title = title.get_text(strip=True)
    else:
        title = ''
    # 获取表格数据
    data = []
    for row in table.find_all('tr')[2:]:
        cols = row.find_all('td')
        cols = [col.get_text(strip=True) for col in cols]
        dict_data = dict(zip(headers, cols))
        dict_data['title'] = title
        data.append(dict_data)

    return data


def _get_revise_date(content: str) -> str | None:
    """从内容中提取修订日期
    """
    logger.info('尝试提取修订日期：' + content[:100])
    # 修复：使用不同的变量名存储匹配结果
    revise_match = re.search(r'[(（][\s\S]*修[正订][)）]', content[:5000])
    if revise_match is None:
        return None
    # 修复：使用 .group() 获取匹配的字符串内容
    revise_content = revise_match.group()
    revise_date_matches = re.finditer(
        r'(\d{4})[年\-./](?:(1[0-2]|0?[1-9])[月\-./])*(?:([12][0-9]|3[01]|0?[1-9])日?)*',
        revise_content
    )
    revise_dates = []
    max_revise_datetime_date = datetime.date(1, 1, 1)
    max_revise_date_index = -1
    for index, revise_date_match in enumerate(revise_date_matches):
        revise_date = list(filter(lambda x: x is not None, revise_date_match.groups()))
        revise_dates.append(revise_date)
        revise_date = tuple(map(lambda x: 1 if x is None else int(x), revise_date_match.groups()))
        datetime_date = datetime.date(*revise_date)
        if datetime_date > max_revise_datetime_date:
            max_revise_datetime_date = datetime_date
            max_revise_date_index = index

    if not revise_dates:
        revise_date_str = None
    else:
        revise_date_str = '-'.join(revise_dates[max_revise_date_index])
    logger.info(f'提取到的修订日期为：{revise_date_str}')
    return revise_date_str

def _parse_images(documents: list[ParsedText], file_path: Path, batch_size=4):
    garbage_positions_group_by_page = dict()
    for document in documents:
        if document.metadata.need_filtered:
            garbage_positions_group_by_page.setdefault(
                document.metadata.page_number[0],
                []
            ).extend(document.metadata.position)

    parsed_images = list(filter(lambda _document: isinstance(_document, ParsedImage), documents))

    @set_request_id(request_id.get())
    def worker(parsed_image: ParsedImage, parsed_image_index: int):
        logger.info(f'解析{file_path}的第{parsed_image_index}/{len(parsed_images)}张图片中')
        metadata = parsed_image.metadata

        if metadata.is_parsed or not metadata.base64:
            return

        position = metadata.position[0]
        page_number = metadata.page_number
        page_number = page_number[0] if page_number else -1
        garbage_positions = garbage_positions_group_by_page.get(page_number, [])

        for garbage_position in garbage_positions:
            end = (position[2][1], garbage_position[2][1])
            start = (position[0][1], garbage_position[0][1])
            image_header_footer_overlap = max(0, min(end) - max(start))
            image_height = position[2][1] - position[0][1]
            proportion = image_header_footer_overlap / image_height

            if proportion >= 0.3:
                metadata.need_filtered = True
                break

        if not metadata.need_filtered:
            image_parser = ImageParser.get_parser()

            try:
                image_results = image_parser.parse(
                    Blob.from_data(
                        base64.b64decode(metadata.base64),
                        path=f'{file_path.name}-{parsed_image_index}.jpg'
                    )
                )
            except Exception as e:
                if re.match('.*大小.*不符合要求.*', str(e)):
                    logger.info(f'{file_path}的第{parsed_image_index}张图片太小，跳过。')
                    return

                logger.error(f'{file_path}的第{parsed_image_index}张图片解析失败')
                raise e

            if image_results:
                metadata.image_size = image_results[0].metadata.page_size[0]

            metadata.is_parsed = True

            page_content = ''
            metadata.boxes = []
            for image_result in image_results:
                if not isinstance(image_result, ParsedImage):
                    metadata.boxes += image_result.metadata.position
                    page_content += image_result.page_content
            if not parsed_image.page_content:
                parsed_image.page_content = page_content
        else:
            logger.info('图片应该是页脚页眉，跳过。')

    for index in tqdm(range(0, len(parsed_images), batch_size), desc=f'获取图片boxes（批大小为{batch_size}）'):
        futures = run_in_thread_pool(
            worker,
            [
                {
                    'parsed_image': parsed_image,
                    'parsed_image_index': parsed_image_index
                }
                for parsed_image_index, parsed_image in zip(
                        list(range(index, min(index + batch_size, len(parsed_images)))),
                        parsed_images[index:index + batch_size]
                )
            ],
            max_workers=DocParseConfig().config.get('image_boxes_batch_size', 4)
        )
        for _ in futures:
            pass


def load_files(
        parse_params: ParseParams,
        multi_thread=False,
        multi_modal=True,
        need_image_boxes=True
) -> Generator[LoadResult, None, None]:
    knowledge_base_name = parse_params.knowledge_base_name
    knowledge_base_id = parse_params.knowledge_base_id
    user_id = parse_params.user_id
    files = parse_params.files
    file_type = parse_params.file_type

    nacos_config = DocParseConfig().config
    use_ali = nacos_config['use_ali']
    use_fudan = nacos_config['use_fudan']
    use_text_in = nacos_config['use_text_in']
    use_mineru = nacos_config['use-mineru']
    bypass = nacos_config.get('bypass', True)
    garbage_filter = nacos_config.get('garbage_filter', False)
    multi_modal = multi_modal and nacos_config.get('use_multi_modal', False)

    def load_file(_file: FileParams, document_type: str) -> LoadResult:
        try:
            logger.info(f'开始解析：{_file.file_path}')
            single_file_timer = time.perf_counter()

            _file_path = Path(_file.file_path)
            file_name = _file_path.name
            ext = _file_path.suffix.lower()
            document_id = create_document_id(_file_path)
            blob = MinioFile(str(_file_path)).get_blob()

            # 有的解析工具并不将文档中图片的内容给出来 需要再次进行解析
            parse_image = False

            parser = None
            documents: list[ParsedText] | None = None

            try:
                if use_ali and AliParser.valid_file_name(file_name):
                    logger.info('使用ali parser')
                    parser = AliParser()
                    documents = parser.parse(blob)
                elif use_text_in and TextInParser.valid_file_name(file_name):
                    logger.info('使用TextIn parser')
                    parser = TextInParser()
                    documents = parser.parse(blob)
                elif use_fudan and FudanParser.valid_file_name(file_name):
                    logger.info('使用fudan parser')
                    parser = FudanParser()
                    documents = parser.parse(blob)
                elif use_mineru and MinerUParser.valid_file_name(file_name):
                    logger.info('使用minerU parser')
                    parser = MinerUParser()
                    documents = parser.parse(blob)
                    parse_image = True
            except Exception as e:
                if not bypass:
                    raise e

                logger.exception(e)
                logger.error('外部解析器解析失败，尝试使用自建解析')
                parser = None
                documents = None

            if parser is None:
                logger.info('使用parser')
                if ext == '.docx':
                    parser = DOCXParser.get_parser(document_type)
                elif ext == '.doc':
                    parser = DOCParser.get_parser()
                elif ext in {'.pptx', '.ppt'}:
                    parser = PPTParser.get_parser()
                elif ext == '.pdf':
                    parser = PDFParser.get_parser(
                        garbage_file_name=_file_path.stem,
                        document_type=document_type
                    )
                elif ext == '.txt':
                    parser = TXTParser.get_parser()
                elif ext in {'.xlsx', '.xls'}:
                    parser = ExcelParser.get_parser()
                    parser.document_type = document_type
                elif ext == '.html':
                    parser = HTMLParser.get_parser()
                elif ext == ".csv":
                    parser = CSVParser.get_parser()
                    parser.document_type = document_type
                elif ext == '.wps':
                    parser = WPSParser.get_parser()
                else:
                    if ImageParser.is_image(blob):
                        parser = ImageParser.get_parser()
                    else:
                        raise NotImplementedError(f'不支持格式“{ext}”')

                documents = parser.parse(blob)

            if parse_image:
                _parse_images(documents, _file_path)

            if multi_modal:
                if need_image_boxes:
                    _parse_images(documents, _file_path)

                # 如果被解析文件是图片 则判断是否进行多模态解析
                if ImageParser.is_image(blob):
                    metadata = ParsedTextMetadata(
                        source=_file.file_path,
                        file_path=_file.file_path,
                        type='text',
                        page_number=[1]
                    )

                    if documents:
                        image_size = documents[0].metadata.page_size[0]
                        metadata.page_size = [image_size]
                        boxes = []
                        page_content = ''

                        for document in documents:
                            if document.metadata.type == 'text':
                                boxes += document.metadata.position
                                page_content += document.page_content + '\n'
                        metadata.position = boxes

                        if image_need_multi_modal(image_size, boxes):
                            use_multi_modal = True
                        else:
                            use_multi_modal = False
                    else:
                        page_content = None
                        metadata.page_size = [ImageParser.get_image_size(blob)]
                        use_multi_modal = True

                    if use_multi_modal:
                        # 请求多模态
                        multi_modal_client = MultiModalClient(parse_params.multi_model_info)
                        prompt = ''
                        if page_content:
                            prompt += PROMPT_TEMPLATE.replace('{{content}}', page_content) + '\n\n'
                        prompt += QUERY
                        response = multi_modal_client.chat([
                            MultiModalMessage(
                                type='text',
                                content=prompt
                            ),
                            MultiModalMessage(
                                type='image',
                                content=blob.as_bytes()
                            )
                        ])

                        if documents:
                            new_documents = []
                            added_summary = True # 是否将图片的多模态总结的文字添加进去
                            for document in documents:
                                if document.metadata.type != 'text':
                                    new_documents.append(document)
                                    if added_summary:
                                        new_documents.append(ParsedText(
                                            page_content=response,
                                            metadata=metadata
                                        ))
                                    # not_added = False
                            documents = new_documents
                            del new_documents
                        else:
                            documents.append(ParsedText(
                                page_content=response,
                                metadata=metadata
                            ))

            if garbage_filter:
                documents = list(filter(lambda x: not x.metadata.need_filtered, documents))

            parsed_result = []
            image_documents = []
            table_documents = []

            for document in documents:
                if isinstance(document, ParsedTable):
                    parsed_result.append(document.page_content)
                    table_documents.append(document)
                elif isinstance(document, ParsedImage):
                    parsed_result.append(document.page_content)
                    image_documents.append(document)
                else:
                    parsed_result.append(document.page_content)

            # 用两个换行符是为了防止多个markdown表格连在一起无法正确显示的问题
            parsed_result = '\n\n'.join(parsed_result)

            if knowledge_base_id:
                logger.info('保存解析结果到minio')
                logger.info('parsed_result: ' + parsed_result)
                save_to_minio(
                    parsed_result,
                    image_documents,
                    table_documents,
                    knowledge_base_id,
                    user_id,
                    file_name,
                    _file.file_id,
                    txt_path=str(Path(*_file_path.parts[:-1]) / 'parsed' / (
                            file_name + '.txt')) if parse_params.save_txt else None,
                )
            else:
                logger.warning('知识库id未传入')

            revise_date = _get_revise_date(file_name)
            if not revise_date:
                revise_date = _get_revise_date(parsed_result)

            # 初始化起始的offset
            start_offset = 0
            for document in documents:
                metadata = document.metadata
                metadata.document_id = document_id
                metadata.file_id = _file.file_id
                metadata.knowledge_base_name = knowledge_base_name
                metadata.title = file_name
                metadata.file_size = _file.file_size
                metadata.revise_date = revise_date
                metadata.parent_file_name = _file.parent_file_name
                # R13-VER-10：版本号落进 chunk metadata，检索侧据此取"当前有效版本"
                metadata.version = getattr(_file, "version", None)
                metadata.labels = _file.labels
                metadata.folder_id = _file.folder_id

                # 给每个Document metadata添加offset key，value对应的是一个二元列表的列表，
                # 因为多个offset不连续的Documents可能被合并，所以需要保留多组坐标（坐标就是字符串索引）。
                # 每个二元列表的第一个元素是起始坐标，第二个是结束坐标。
                if isinstance(document, ParsedImage):
                    metadata.offset = [[start_offset, start_offset]]
                else:
                    end_offset = start_offset + len(document.page_content)
                    metadata.offset = [[start_offset, end_offset]]
                    start_offset = end_offset + 1  # 加1是因为获取解析后原文的时候会使用“'\n'.join(page_contents)”

            logger.info(f'解析{_file_path}花费时间：{(time.perf_counter() - single_file_timer):.2f}s')

            return LoadResult(
                success=True,
                file_path=_file.file_path,
                file_id=_file.file_id,
                documents=documents,
                revise_date=revise_date
            )
        except Exception as _e:
            logger.exception(_e)
            logger.error(f'{_file.file_path}解析失败')
            if not isinstance(_e, ApiError):
                _e = FileParseFailedError(str(_e))
            return LoadResult(success=False, file_path=_file.file_path, file_id=_file.file_id, exception=_e)

    if files:
        timer = time.perf_counter()

        if multi_thread:
            logger.debug('多线程读取')
            params = [
                {
                    "_file": file,
                    "document_type": file_type,
                } for file in files
            ]
            yield from run_in_thread_pool(load_file, params=params)
        else:
            logger.debug('单线程读取')
            for file in files:
                yield load_file(file, file_type)

        logger.info(f'解析花费时间：{(time.perf_counter() - timer):.2f}s')
