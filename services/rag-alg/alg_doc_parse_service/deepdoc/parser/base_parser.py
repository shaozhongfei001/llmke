from typing import Iterator, Pattern

from langchain_core.document_loaders import BaseBlobParser, Blob

from ..output_object import ParsedText


class BaseParser(BaseBlobParser):
    supported_formats: list[Pattern[str]] = []
    document_type: str = ""

    def parse(self, blob: Blob) -> list[ParsedText]:
        return list(self.lazy_parse(blob))

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        raise NotImplementedError

    @classmethod
    def valid_file_name(cls, file_name: str, supported_formats: list[Pattern[str]] | None = None) -> bool:
        if not supported_formats:
            supported_formats = cls.supported_formats

        for support_format in supported_formats:
            if support_format.match(file_name):
                return True
        return False
