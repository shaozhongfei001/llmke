import csv
from typing import Iterator
import io
import pandas as pd
from langchain_core.document_loaders import Blob

from .base_parser import BaseParser
from ..output_object import ParsedTableCell, ParsedTable, ParsedTableMetadata
from ..utils import find_codec


class _BaseParser(BaseParser):
    def lazy_parse(self, blob: Blob) -> Iterator[ParsedTable]:
        table = self(blob)
        yield table

    def __call__(self, file: str | Blob) -> ParsedTable:
        """读取csv表格"""
        if isinstance(file, str):
            with open(file, mode='rb') as f:
                file_bytes = f.read()
        else:
            file_bytes = file.as_bytes()

        csv_data = file_bytes.decode(find_codec(file_bytes))
        csv_reader = csv.reader(csv_data.splitlines())

        table = []
        max_col_size = 0
        for row_index, csv_row in enumerate(csv_reader):
            table_row = []
            col_size = 0
            for col_index, value in enumerate(csv_row):
                cell = ParsedTableCell(value=value,
                                       position=(row_index, col_index),
                                       is_merged=False,
                                       merged_positions=[])
                table_row.append(cell)
                col_size += 1
            max_col_size = max(max_col_size, col_size)
            table.append(table_row)

        for row_index, row in enumerate(table):
            row_length = len(row)
            diff = max_col_size - row_length

            if diff > 0:
                for i in range(diff):
                    row.append(ParsedTableCell(
                        value='',
                        position=(row_index, row_length + i),
                        is_merged=False,
                        merged_positions=[]
                    ))

        table_cells = [table_cell for row in table for table_cell in row]
        metadata = ParsedTableMetadata(source=file.source, file_path=file.source)
        # [html表格]
        if self.document_type == 'financial':
            df = pd.read_csv(io.BytesIO(file_bytes),on_bad_lines='skip')
            table_html_content = df.to_html(index=False, classes='table table-bordered', escape=False)
        else:
            table_html_content = ""
        metadata = ParsedTableMetadata(source=file.source, file_path=file.source, table_html_content=table_html_content)
        table = ParsedTable(table_cells=table_cells, metadata=metadata)
        return table


class Parser:
    @staticmethod
    def get_parser() -> _BaseParser:
        return _BaseParser()
