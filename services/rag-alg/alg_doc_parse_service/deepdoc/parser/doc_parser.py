from typing import Iterator

from langchain_core.document_loaders import Blob
from tika import parser

from log import logger
from .base_parser import BaseParser
from ..output_object import ParsedTextMetadata, ParsedText


class _BaseParser(BaseParser):
    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        sections = self(blob)
        yield from [
            ParsedText(
                page_content=section,
                metadata=ParsedTextMetadata(source=blob.path, file_path=blob.path))
            for section in sections
        ]

    def __call__(self, file: str | Blob):
        if isinstance(file, Blob):
            parsed_doc = parser.from_buffer(file.as_bytes())
        else:
            parsed_doc = parser.from_file(file)

        if parsed_doc['content'] is None:
            logger.warning(f'tika返回结果错误：{parsed_doc}')
            parsed_doc['content'] = ''

        return parsed_doc['content'].split('\n')


class Parser:
    @staticmethod
    def get_parser() -> _BaseParser:
        return _BaseParser()
