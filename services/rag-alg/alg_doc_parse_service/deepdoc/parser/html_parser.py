from typing import Iterator

from bs4 import BeautifulSoup
from langchain_core.document_loaders import Blob

from .base_parser import BaseParser
from ..output_object import ParsedTextMetadata, ParsedText
from ..utils import find_codec


class _BaseParser(BaseParser):
    def __init__(self, use_ocr=False):
        self.use_ocr = use_ocr

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        sections = self(blob)

        yield from [
            ParsedText(
                page_content=section,
                metadata=ParsedTextMetadata(source=blob.source, file_path=blob.source)
            ) for section in sections
        ]

    def __call__(self, file: str | Blob):
        if isinstance(file, Blob):
            blob_bytes = file.as_bytes()
            encoding = find_codec(blob_bytes)
            html_str = blob_bytes.decode(encoding, errors="ignore")
        else:
            with open(file, 'r') as f:
                html_str = f.read()

        if not self.use_ocr:
            soup = BeautifulSoup(html_str, 'html.parser')
            return [soup.get_text().strip()]
        else:
            raise NotImplemented('html解析暂时不支持使用ocr')


class Parser:
    @staticmethod
    def get_parser() -> _BaseParser:
        return _BaseParser()
