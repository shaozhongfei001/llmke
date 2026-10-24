from typing import Iterator

from langchain_core.document_loaders import Blob

from log import logger
from .base_parser import BaseParser
from ..output_object import ParsedText, ParsedTextMetadata
from ..utils import find_codec


class _BaseParser(BaseParser):
    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        return self(blob)

    def __call__(self, blob: Blob) -> Iterator[ParsedText]:
        binary = blob.as_bytes()
        encoding = find_codec(binary)
        logger.debug(f'文件编码格式为：{encoding}')
        txt = binary.decode(encoding, errors="ignore")

        yield from [
            ParsedText(page_content=paragraph,
                       metadata=ParsedTextMetadata(source=blob.source, file_path=blob.source))
            for paragraph in txt.split('\n')
        ]


class Parser:
    @staticmethod
    def get_parser() -> _BaseParser:
        return _BaseParser()
