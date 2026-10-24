"""
表格压缩
"""
import os

from openpyxl import load_workbook
from openpyxl.styles import PatternFill

from deepdoc.splitter.table_utils.table_loader import *


def highlight_anchors(src_file, dest_file, anchor_cells: dict):
    """高亮显示锚点
        anchor_cells: dict[(sheet_name: str, TableCells: List[TabelCell]])]
    """

    def color_cell(pos):
        # 定位到特定的单元格
        cell = ws[pos]  # 假设我们想要高亮显示A1单元格

        # 创建一个PatternFill对象，设置填充类型为实心填充，颜色为明黄色
        yellow_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

        # 将填充应用到单元格
        cell.fill = yellow_fill

    # 打开现有的Excel文件
    wb = load_workbook(src_file)
    for sheet_name, cells in anchor_cells.items():
        # 选择工作表
        ws = wb[sheet_name]
        positions = set(cell.abs_position for cell in cells)

        for cell in cells:
            if cell.is_merged_cell:
                pass
            pos = cell.cell_offset

    # 保存工作簿
    wb.save(dest_file)


def compress_table(table):
    """根据数据内容、结构，保留表格骨架，返回table类型"""

    def detect_discrepancies():
        anchor_points = set()
        for i, row in enumerate(table.table_matrix):
            row_type = table.row_value_types[i]

            for j, cell in enumerate(row):
                col_type = table.col_value_types[j]
                cell_type = cell.value_type
                if cell.is_merged_cell:  # 合并单元格的四角
                    left, right, up, down = _find_merged_range(cell.merged_positions)
                    if (cell.relative_position[0] == left or cell.relative_position[0] == right) and \
                            (cell.relative_position[1] == up or cell.relative_position[1] == right):
                        print("合并单元格四角", cell)
                        anchor_points.add(cell)
                elif (i == 0 or i == table.rows_count - 1) and (j == 0 or j == table.columns_count - 1):  # 首行/末行
                    print("首末行列", cell)
                    anchor_points.add(cell)
                # elif j == 0 or j == table.columns_count-1:  # 首列/末列
                #     anchor_points.add(cell)
                elif row_type != CellValueType.OTHER and cell_type != row_type:  # 不符合当前行整体格式
                    print("不符合行value_type", cell)
                    anchor_points.add(cell)
                elif col_type != CellValueType.OTHER and cell_type != col_type:  # 不符合当前行的
                    print("不符合列value_type", cell)
                    anchor_points.add(cell)
        return anchor_points

    anchors = detect_discrepancies()
    table_skeletons = anchors
    neighbour_count = 2

    # for cell in anchors:
    #     cell_r, cell_c = cell.relative_position
    #     for r in range(max(0, cell_r-neighbour_count),  min(cell_r + neighbour_count, table.rows_count)):
    #         table_skeletons.add(table.table_matrix[r][cell_c])
    #     for c in range(max(0, cell_c-neighbour_count),  min(cell_c + neighbour_count, table.columns_count)):
    #         table_skeletons.add(table.table_matrix[cell_r][c])

    print("锚点个数：", len(anchors))
    print("压缩前", table.shape[0] * table.shape[1])
    print("压缩后", len(table_skeletons))
    print(f"压缩比例：{len(table_skeletons) / (table.shape[0] * table.shape[1]) * 100:.2f}")
    return table_skeletons

    # table_skeletons = sorted(table_skeletons, key=lambda x: x.abs_position)
    # table_skeleton_matrix = []
    # row = []
    #
    # for i, cell in enumerate(table_skeletons):
    #     if i == 0:
    #         row.append(cell)
    #         cur_row = cell.abs_position[0]
    #     else:
    #         if cur_row == cell.abs_position[0]:
    #             row.append(cell)
    #         else:
    #             cur_row = cell.abs_position[0]
    #             table_skeleton_matrix.append(row)
    #             row = [cell]
    #
    # for row in table_skeleton_matrix:
    #     print(row)


def process_excel_file(file_path):
    sheet_blocks = read_excel(file_path)
    compress_sheet = {}
    for sheet, tables in sheet_blocks.items():

        print("=====" * 30)
        print("Excel 读取结果：")
        print("\tSheetName:", sheet)
        print("\tTableCount:", len(tables))
        if sheet != "功能":
            compress_sheet[sheet] = set()
            continue

        for table in tables:
            # index_table(table, sheet)

            cells = []
            for cell_dict in table:
                cell = SplitTableCell(**cell_dict)
                cells.append(cell)

            table_obj = SplitTable(sheet, cells)

            compress_sheet[sheet] = compress_table(table_obj)
        highlight_anchors(file_path, f"{os.path.split(file_path)[-1]}", compress_sheet)


if __name__ == '__main__':
    pass
