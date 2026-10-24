from .doc_parser import _BaseParser


class Parser:
    @staticmethod
    def get_parser() -> _BaseParser:
        return _BaseParser()
