from deepdoc.splitter.book import BookSplitter
from deepdoc.splitter.intel import IntelSplitter
from deepdoc.splitter.laws import LawSplitter
from deepdoc.splitter.naive import NaiveSplitter
from deepdoc.splitter.table import TableSplitter
from deepdoc.splitter.table import FinancialTableSplitter

class Splitter:
    @staticmethod
    def get_splitter(document_type: str = 'naive', is_table: bool = False, *splitter_args, **splitter_kwargs):
        if is_table:
            if document_type in ('financial'):
                return FinancialTableSplitter(*splitter_args, **splitter_kwargs)
            return TableSplitter(*splitter_args, **splitter_kwargs)
        if document_type in ('financial'):
            return IntelSplitter(*splitter_args, **splitter_kwargs)
        elif document_type == 'naive':
            return NaiveSplitter(*splitter_args, **splitter_kwargs)
        elif document_type == 'laws':
            return LawSplitter(*splitter_args, **splitter_kwargs)
        elif document_type in ('intel', 'intelligent'):
            return IntelSplitter(*splitter_args, **splitter_kwargs)
        elif document_type == 'book':
            return BookSplitter(*splitter_args, **splitter_kwargs)
        else:
            return NaiveSplitter(*splitter_args, **splitter_kwargs)
