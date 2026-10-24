from deepdoc.output_object import ParsedText
from .base import BaseSplitter
from .utils import naive_merge, group_documents


class NaiveSplitter(BaseSplitter):
    def chunk(self, documents: list[ParsedText]) -> list[ParsedText]:
        documents_group_by_source = group_documents(documents)
        chunks = []

        for _, documents in documents_group_by_source.items():
            chunks += naive_merge(
                documents,
                self.chunk_size,
                self.length_function,
                self.split_regex,
                self.chunk_overlap
            )

        return chunks
