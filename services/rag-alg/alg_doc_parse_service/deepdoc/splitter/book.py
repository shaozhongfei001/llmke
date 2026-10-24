from deepdoc.output_object import ParsedText
from .base import BaseSplitter
from .section_splitter import SectionSplitter
from .utils import (
    naive_merge,
    group_documents,
    bullets_category
)


class BookSplitter(BaseSplitter):
    def chunk(self, documents: list[ParsedText]) -> list[ParsedText]:
        documents_group_by_source = group_documents(documents)
        chunks = []

        for source, documents in documents_group_by_source.items():
            if bullets_category(documents):
                section_splitter = SectionSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separators=self.separators
                )
                chunks += section_splitter.split_documents(documents, source.split("/")[-1])
            else:
                chunks += naive_merge(documents, self.chunk_size, self.length_function)

        return chunks
