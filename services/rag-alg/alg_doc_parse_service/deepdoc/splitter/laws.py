from deepdoc.output_object import ParsedText
from deepdoc.splitter.utils import group_documents
from .base import BaseSplitter
from .section_splitter import SectionSplitter


class LawSplitter(BaseSplitter):
    def chunk(self, documents: list[ParsedText]) -> list[ParsedText]:
        documents_group_by_source = group_documents(documents)
        chunks = []
        splitter = SectionSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators
        )
        for source, documents in documents_group_by_source.items():
            # split_results = splitter.split_documents(documents, source.split("/")[-1])
            chunks += splitter.split_documents(documents, source.split("/")[-1])
            # chunks += naive_merge(documents, self.chunk_size, self.length_function)
        return chunks
