"""
定义表格切分过程中使用的Table & Cell 数据类型
"""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from openpyxl.utils import get_column_letter


@dataclass
class CellValueType:
    """单元格值的类型"""
    DIGIT = "DIGIT"  # 数字
    LABEL = "LABEL"  # 标签，一个中文字/没有空格的英文字段
    LONG_STRING = "LONG_STRING"
    SHORT_STRING = "SHORT_STRING"  # 字数比较短的文本
    DATE = "DATE"  # 时间日期
    EQUATION = "EQUATION"  # 公式
    EMPTY = "EMPTY"  # 空值
    OTHER = "OTHER"  # 其他


class SplitTableCell:
    def __init__(self, value, position, is_merged=False, merged_positions=None, **kwargs):
        # 单元格内容
        self.value = value
        # 绝对位置，从0开始
        self.abs_position = position
        # 相对位置，从0开始
        self.relative_position = position
        self.is_merged_cell = is_merged

        if not self.is_merged_cell:
            self.merged_positions = []
        else:
            assert self.is_merged_cell and merged_positions is not None, self
            # 相对位置，从0开始
            self.merged_positions = merged_positions.copy()
        self.value_type = self.find_value_type()

    def __repr__(self):
        return str(self.value) + f" ({self.cell_offset})"

    @property
    def cell_offset(self):
        """excel中对应的坐标位置"""
        return f"{get_column_letter(self.abs_position[1] + 1)}{self.abs_position[0] + 1}"

    def find_value_type(self):
        def _is_date_time():
            for date_format in ["%Y-%m-%d", "%Y/%m/%d"]:
                try:
                    datetime.strptime(self.value, date_format)
                    return True
                except (ValueError, TypeError):
                    continue  # Try the next format
            return False

        if self.value is None:
            return CellValueType.EMPTY
        if isinstance(self.value, (int, float)):
            return CellValueType.DIGIT

        elif isinstance(self.value, str):
            trimmed_value = self.value.strip()
            if len(trimmed_value) == 0:
                return CellValueType.EMPTY  # Consider empty strings as None

            if _is_date_time():
                return CellValueType.DATE

            if re.fullmatch("[\d.,%]+.", self.value):
                return CellValueType.DIGIT

            if re.fullmatch("[0-9a-zA-Z .()_/-]+", trimmed_value):  # 英文的
                if " " not in trimmed_value:
                    return CellValueType.LABEL

            elif len(trimmed_value) <= 10 or (
                    trimmed_value.isascii() and len(trimmed_value.split()) <= 5):  # 中文小于10个字或者英文小于5个单词
                return CellValueType.SHORT_STRING
            else:
                return CellValueType.LONG_STRING

        elif isinstance(self.value, datetime):
            return CellValueType.DATE

        return CellValueType.OTHER


class SplitTable:
    def __init__(self, cells: list[SplitTableCell], row_range=None, col_range=None, file_name=None, sheet_name=None):
        self.cells: list[SplitTableCell] = cells  # 单元格
        self.sheet_name = sheet_name  # excel文件的sheet_name，其他文件中sheet name为空
        self.file_name = file_name  # 文件路径
        self.title_name = ""
        self.headers = []  # 表头行
        self.row_range = row_range
        self.col_range = col_range
        self.rows_count = 0
        self.columns_count = 0
        self._init_table()

    def _init_table(self):
        self.cells = sorted(self.cells, key=lambda x: x.abs_position)

        if self.row_range is None or self.col_range is None:
            # 计算表格的起始和结束范围
            self.row_range = [self.cells[0].abs_position[0], self.cells[0].abs_position[0]]
            self.col_range = [self.cells[0].abs_position[1], self.cells[0].abs_position[1]]

            for i, cell in enumerate(self.cells):
                r, c = cell.abs_position
                if r <= self.row_range[0]:
                    self.row_range[0] = r
                elif r >= self.row_range[1]:
                    self.row_range[1] = r

                if c <= self.col_range[0]:
                    self.col_range[0] = c
                elif c >= self.col_range[1]:
                    self.col_range[1] = c

        self.rows_count = self.row_range[1] + 1 - self.row_range[0]
        self.columns_count = self.col_range[1] + 1 - self.col_range[0]

        self.table_matrix = []
        for r in range(self.rows_count):
            row = []
            for c in range(self.columns_count):
                row.append(SplitTableCell(None, (r, c), is_merged=False))
            self.table_matrix.append(row)

        for cell in self.cells:
            r, c = cell.abs_position
            cell.relative_position = [r - self.row_range[0], c - self.col_range[0]]
            if cell.is_merged_cell:
                for i, merged_pos in enumerate(cell.merged_positions):
                    merged_r, merged_c = merged_pos
                    cell.merged_positions[i] = [merged_r - self.row_range[0], merged_c - self.col_range[0]]
            self.table_matrix[r - self.row_range[0]][c - self.col_range[0]] = cell

        # 判断行列的类型
        self.row_value_types, self.col_value_types = self.get_types()
        self.title, self.title_positions = self.find_title()

    def html_encode(self) -> str:
        """将表格转化为html-encoding格式或者 markdown-encoding 或者 json 具体看测评效果"""
        pass

    def json_encode(self):
        """"""
        pass

    def markdown_encode(self, row_range: tuple = None, col_range: tuple = None) -> str:
        """以markdown格式显示表格"""
        table_string = ""
        if row_range is None:
            row_start, row_end = 0, self.rows_count
        else:
            row_start, row_end = row_range

        if col_range is None:
            col_start, col_end = 0, self.columns_count
        else:
            col_start, col_end = row_range

        for row in self.table_matrix[row_start: row_end]:
            row_string = "| " + "| ".join(
                [str(cell.value) if cell.value else "" for cell in row[col_start:col_end]]) + "|"
            table_string = "\n".join([table_string, row_string])
        return table_string

    @property
    def character_length(self):
        """表格中包含的文本字符长度"""
        return len(" ".join([str(cell.value) for cell in self.cells]))

    @property
    def shape(self):
        """表格行数、列数"""
        return self.rows_count, self.columns_count

    def find_title(self):
        """找到表格的标题
        标题判断规则:
        1. 首行一整行 是一个合并单元格
        return: title_string, [(int, int), (int, int)]
        """

        def is_first_row_columns(cell):
            _rows = [pos[0] for pos in cell.merged_positions]
            _columns = [pos[1] for pos in cell.merged_positions]
            try:
                if min(_rows) <= self.row_range[0] + 1 and max(_rows) >= self.row_range[1] - 2:
                    return True
                if min(_columns) <= self.col_range[0] + 1 and max(_columns) >= self.col_range[1] - 2:
                    return True
            except:
                pass
            return False

        for cell in self.cells:
            if cell.is_merged_cell and is_first_row_columns(cell):
                return cell.value, cell.merged_positions
        return "", None

    def get_types(self):
        """判断每行、每列都是什么类型"""

        def get_dominate_type(cell_values, dominate_ratio=0.8):
            """找到主导数据类型，例：10个元素中，1个是string，9个是digit，主导类型是digit。无法判断则为other"""
            # 若某行/列 前10个格子 有内容，最后3个格子没有内容为空，则不将为空的格子纳入统计

            striped_cell_values = []
            temp_cells = []
            for cell in cell_values:
                if cell != CellValueType.EMPTY:
                    striped_cell_values.extend(temp_cells)
                    temp_cells = []
                    striped_cell_values.append(cell)
                else:
                    temp_cells.append(cell)
            type_counts = Counter(striped_cell_values)
            all_count = len(striped_cell_values)
            if len(type_counts) == 0:
                return CellValueType.EMPTY
            if len(type_counts) == 1:
                return striped_cell_values[0]

            for value, count in type_counts.items():
                if count >= all_count * dominate_ratio:
                    return value
            if type_counts[CellValueType.LONG_STRING] + type_counts[CellValueType.SHORT_STRING] >= all_count * dominate_ratio:
                return CellValueType.LONG_STRING
            return CellValueType.OTHER

        row_types = []
        col_types = []

        # row
        for row in self.table_matrix:
            row_type = get_dominate_type([cell.value_type for cell in row])
            row_types.append(row_type)
            # print("row", row_type, [cell.value for cell in row if cell])

        # col
        for i in range(self.columns_count):
            col_cell_types = [row[i].value_type for row in self.table_matrix]
            col_type = get_dominate_type(col_cell_types)
            col_types.append(col_type)
            # print("col", col_type, [row[i].value for row in self.table_matrix if row[i]])
        return row_types, col_types
