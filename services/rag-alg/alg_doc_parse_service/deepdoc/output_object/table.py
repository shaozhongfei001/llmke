import copy
from typing import Any, Literal, TypeVar, Callable, Iterable, ClassVar

from bs4 import BeautifulSoup
from pydantic import Field, BaseModel, model_validator

from .text import ParsedTextMetadata, ParsedText

_data_T = TypeVar('_data_T')
_row_T = TypeVar('_row_T')
_cell_T = TypeVar('_cell_T')


class ParsedTableMetadata(ParsedTextMetadata):
    type: Literal['table', 'table_summary'] = Field(default='table', description='类型')
    table_summary_id: int | None = Field(default=None, description='关联table summary中数据对应的主键')
    table_name: str | None = Field(default='', description='表格名称')
    table_footnote: str | None = Field(default=None, description='表格脚注')
    table_preceding_context: str | None = Field(default='', description='表格上文')
    table_html_content: str | None = Field(default='', description='表格html内容')
    table_multipage_flag: bool = Field(default=False, description='跨页表格标志')


class ParsedTableCell(BaseModel):
    value: Any = Field()
    position: tuple[int, int] = Field()  # 表格绝对坐标(row, column) 行列信息
    is_merged: bool = Field(default=False)
    merged_positions: list[tuple[int, int]] = Field(default=[])
    is_header: bool = Field(default=False)


class ParsedTable(ParsedText):
    table_cells: list[ParsedTableCell] = Field(default=[])
    metadata: ParsedTableMetadata = Field(default=ParsedTableMetadata(), description='用于补充描述的元数据')
    markdown_encode: ClassVar
    html_to_table_cells: ClassVar
    html_encode: ClassVar

    @model_validator(mode='after')
    def model_validate(self):
        if not (self.table_cells or self.page_content):
            return self

        if not self.page_content:
            self.page_content = self.markdown_encode()

        if not self.table_cells:
            self.table_cells = self.html_to_table_cells()

        return self

    def html_to_table_cells(self) -> list[ParsedTableCell]:
        soup = BeautifulSoup(self.page_content, 'html.parser')
        table = soup.find('table')

        if not table:
            return []

        self.metadata.table_name = table.find('caption')

        return ParsedTable.get_table_cells(
            table,
            get_rows_func=lambda x: x.find_all('tr'),
            get_cells_from_row_func=lambda x: x.find_all(['td', 'th']),
            get_row_span_from_cell=lambda x: int(x.get('rowspan', '1')),
            get_col_span_from_cell=lambda x: int(x.get('colspan', '1')),
            get_header_from_row=lambda x: bool(x.find_all('th')),
            get_text_from_cell=lambda x: x.text.strip()
        )

    @staticmethod
    def get_table_cells(
            data: _data_T,
            *,
            get_rows_func: Callable[[_data_T], Iterable[_row_T]] = lambda x: x,
            get_cells_from_row_func: Callable[[_row_T], Iterable[_cell_T]] = lambda x: x,
            get_row_span_from_cell: Callable[[_cell_T], int] = lambda x: 1,
            get_col_span_from_cell: Callable[[_cell_T], int] = lambda x: 1,
            get_header_from_row: Callable[[_row_T], bool] = lambda x: False,
            get_text_from_cell: Callable[[_cell_T], str]
    ) -> list[ParsedTableCell]:
        # 获取可迭代的行
        rows = list(get_rows_func(data))

        # 处理空情况
        if not rows:
            return []

        # 初始化二维的ParsedTableCell列表（最后需要转换成一维返回出去）
        table: list[list[ParsedTableCell]] = []

        # 根据首行的colspan判断表格的列大小
        col_size = [sum(map(get_col_span_from_cell, get_cells_from_row_func(row))) for row in rows]
        col_size = max(col_size)

        # 初始化table（此时的行大小可能不正确，不过迭代的过程中会动态添加）
        for row_index in range(len(rows)):
            table.append([])
            for col_index in range(col_size):
                table[row_index].append(ParsedTableCell(
                    value='',
                    position=(row_index, col_index),
                ))

        # 初始化row index和col index
        row_index = -1
        col_index = 0

        # 用于设置col index并且跳过合并单元格
        def set_col_index_and_skip_merged_cells(start_col_index=0):
            nonlocal col_index
            col_index = start_col_index
            try:
                for _table_cell in table[row_index][start_col_index:]:
                    if _table_cell.merged_positions:
                        col_index += 1
                    else:
                        break
            except Exception as e:
                pass

        # 开始迭代
        for row in rows:
            row_index += 1

            # 判断该行是否为表头
            is_header = get_header_from_row(row)

            # 判断本行的rowspan是否为冗余的
            # 当本行的所有colspan等于列大小的时候
            # 如果rowspan都相等则判断为冗余（这是为了处理复旦解析的表格结果）
            row_spans = []
            col_span_count = 0
            for cell in get_cells_from_row_func(row):
                col_span_count += get_col_span_from_cell(cell)
                row_spans.append(get_row_span_from_cell(cell))
            if col_span_count == col_size and len(set(row_spans)) == 1:
                redundant_row_span = True
            else:
                redundant_row_span = False

            # 初始化起始的col index并跳过开头的合并单元格
            set_col_index_and_skip_merged_cells()

            # 大于列大小代表整行都被合并单元格占满（需要动态添加新行）
            # 需要新增一行并且更新row index和重置col index
            if col_index >= col_size:
                table.append([ParsedTableCell(
                    value='',
                    position=(len(table), _),
                ) for _ in range(col_size)])
                row_index += 1
                set_col_index_and_skip_merged_cells()

            # 遍历该行的所有单元格内容
            for cell in get_cells_from_row_func(row):
                set_col_index_and_skip_merged_cells(col_index)
                if col_index >= col_size:
                    break

                # 获取colspan
                col_span = get_col_span_from_cell(cell)

                # 获取table中对应位置的单元格引用
                try:
                    table_cell = table[row_index][col_index]
                except:
                    pass

                # 如果行中出现已经赋值的合并单元格则跳过本次col index
                if not table_cell.merged_positions:
                    # 获取单元格的rowspan
                    # 如果是冗余的则设置为1
                    row_span = get_row_span_from_cell(cell) if not redundant_row_span else 1

                    # 设置单元格的对应属性
                    table_cell.value = get_text_from_cell(cell)
                    table_cell.is_header = is_header
                    table_cell.is_merged = col_span + row_span > 2

                    # 处理复旦表格的span和行数对应不上的问题
                    # 如果rowspan超过了行数则增加缺失的行
                    row_end_index = row_index + row_span
                    if row_end_index > len(table):
                        for _ in range(row_end_index - len(table)):
                            table.append([ParsedTableCell(
                                value='',
                                position=(len(table), _),
                            ) for _ in range(col_size)])

                    # 处理表格的span和列数对应不上的问题
                    # 如果colspan超过了列数则增加缺失的列
                    col_end_index = col_index + col_span
                    if col_end_index > col_size:
                        col_diff = col_end_index - col_size
                        for diff_index in range(col_diff):
                            for table_row_index, table_row in enumerate(table):
                                table_row.append(ParsedTableCell(
                                    value='',
                                    position=(table_row_index, col_size + diff_index),
                                ))
                        col_size += col_diff

                    # 如果该单元格为未赋值的合并单元格
                    # 则设置其他需要合并的单元格
                    if table_cell.is_merged:
                        for row_merge_index in range(row_index, row_end_index):
                            for col_merge_index in range(col_index, col_end_index):
                                table_cell.merged_positions.append((row_merge_index, col_merge_index))

                        for row_merge_index, col_merge_index in table_cell.merged_positions:
                            try:
                                table[row_merge_index][col_merge_index] = copy.deepcopy(table_cell)
                                table[row_merge_index][col_merge_index].position = (
                                    row_merge_index,
                                    col_merge_index
                                )
                            except:
                                continue

                col_index += col_span

        return [table_cell for row in table for table_cell in row]

    def markdown_encode(self) -> str:
        markdown = []
        cells = sorted(self.table_cells, key=lambda x: x.position)
        row_size, col_size = cells[-1].position
        row_size += 1
        col_size += 1

        # 一维转二维
        table = []
        for row_index in range(row_size):
            table.append([])
            for col_index in range(col_size):
                table[row_index].append(cells[col_index + row_index * col_size])

        # 如果首列是标题列则进行转置
        if len(table) > 1 and table[0][0].is_header and table[1][0].is_header:
            new_table = []
            for col_index in range(col_size):
                new_table.append([])
                for row_index in range(row_size):
                    new_table[col_index].append(table[row_index][col_index])
            table = new_table
            del new_table

        # 构建markdown
        for row in table:
            markdown_row = ['']
            for col in row:
                markdown_row.append(f' {col.value} '.replace('\n', '<br>'))
            markdown_row.append('')
            markdown.append('|'.join(markdown_row))

        # 插入标题控制行
        markdown.insert(1, '|'.join([''] + [' :----: ' for _ in range(col_size)] + ['']))

        return '\n'.join(markdown)

    def html_encode(self) -> str:
        """将表格以html形式输出"""
        # 将表格还原成二维的
        cells = sorted(self.table_cells, key=lambda x: x.position)
        cur_row = 0
        row = []
        table_matrix = []
        for i, cell in enumerate(cells):
            if i == 0:
                cur_row = cell.position[0]
                row = [cell]
            else:
                if cell.position[0] == cur_row:
                    row.append(cell)
                else:
                    table_matrix.append(row)
                    cur_row = cell.position[0]
                    row = [cell]
        table_matrix.append(row)

        table_html = "<table>"
        table_name = self.metadata.table_name
        if table_name:
            table_html += f"<caption>{table_name}</caption>\n"

        for row in table_matrix:
            table_html += '<tr>'
            for c in row:
                if c.value is None:
                    table_html += '<td></td>'
                else:
                    table_html += f'<td>{c.value}</td>'
            table_html += '</tr>\n'
        table_html += '</table>'
        return table_html
