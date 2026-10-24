import copy
from datetime import datetime, date, timedelta
from datetime import time as tm
from io import BytesIO
from typing import Iterator, List, Callable, Any

import xlrd
from langchain_core.document_loaders import Blob
from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import numbers
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import CALENDAR_MAC_1904
from openpyxl.workbook import Workbook
import pandas as pd
from tqdm import tqdm
from xlrd import evaluate_name_formula, XLRDError, Book
from xlrd.timemachine import REPR, fprintf
from xls2xlsx import XLS2XLSX

from log import logger
from server.nacos_utils import DocParseConfig
from server.utils import run_in_thread_pool
from .base_parser import BaseParser
from ..output_object import ParsedTableCell, ParsedTable, ParsedTableMetadata


def truncate_row_col(
        row_number: int,
        col_number: int,
        get_value_func: Callable[[int, int], Any],
        get=False,
        start_from_one=False
):
    max_row_number = row_number
    max_col_number = col_number

    # 获取每行的最大列数，如果空列过多，则进行裁剪。
    max_cols = []
    max_continuous_none = 100
    value_count = 0
    for r in range(max_row_number):
        truncate = False
        continuous_none_count = 0
        for c in range(max_col_number):
            if start_from_one:
                r_real = r + 1
                c_real = c + 1
            else:
                r_real = r
                c_real = c

            if get:
                value = get_value_func(r_real, c_real).value
            else:
                value = get_value_func(r_real, c_real)

            if not value:
                continuous_none_count += 1
            else:
                value_count += 1
                continuous_none_count = 0

            if continuous_none_count == max_continuous_none:
                max_cols.append(c - max_continuous_none + 1)
                truncate = True
                break

        if not truncate:
            if value_count == 0:
                max_cols.append(0)
            else:
                max_cols.append(max_col_number)

    # 获取最大行数，如果空行过多，则进行裁剪。
    continuous_none_count = 0
    for index, max_col in enumerate(max_cols):
        if max_col == 0:
            continuous_none_count += 1
        else:
            continuous_none_count = 0

        if continuous_none_count == max_continuous_none:
            max_row_number = index - max_continuous_none + 1
            break

    # 选择最大行数中最大的列数作为最终的最大列数
    if max_cols:
        max_col_number = max(max_cols[:max_row_number])

    return max_row_number, max_col_number


def to_xlsx(self, filename=None):
    """Convert to xlsx using openpyxl.  If filename is not None, then the result
    is written to that file, and the filename is returned, else the workbook is returned.
    openpyxl工具库的重写，为了解决日期格式导致的错误
    """

    if self.h2x:
        return self.h2x.to_xlsx(filename=filename)

    if self.book is None and self.ignore_workbook_corruption:
        return None  # Couldn't be loaded - nothing we can do

    wb = Workbook()  # creates one worksheet
    ws = wb.active

    wb.properties.lastModifiedBy = self.book.user_name
    if self.date_mode:
        wb.epoch = CALENDAR_MAC_1904

    ws_list = []
    for sheet in self.book.sheets():
        if ws:
            ws.title = sheet.name
        else:
            ws = wb.create_sheet(sheet.name)

        ws_list.append(ws)
        ws = None

    def worker(_sheet, _ws):
        logger.info(f'转换sheet：{_sheet.name}')

        for col_ndx, info in _sheet.colinfo_map.items():
            col = get_column_letter(col_ndx + 1)
            if info.hidden:
                _ws.column_dimensions[col].hidden = True
            else:
                _ws.column_dimensions[col].width = self.xls_width_to_xlsx(info.width)
        for row_ndx, info in _sheet.rowinfo_map.items():
            row = row_ndx + 1
            if info.hidden:
                _ws.row_dimensions[row].hidden = True
            else:
                _ws.row_dimensions[row].height = self.xls_height_to_xlsx(info.height)
            _ws.row_dimensions[row].thickTop = info.additional_space_above
            _ws.row_dimensions[row].thickBot = info.additional_space_below

        rows, columns = truncate_row_col(_sheet.nrows, _sheet.ncols, _sheet.cell_value)

        for row in range(rows):
            for col in range(columns):
                cell_type = _sheet.cell_type(row, col)
                value = _sheet.cell_value(row, col)
                if cell_type == xlrd.XL_CELL_DATE:
                    try:  # Issue #5: Just keep 'bad' dates as float numbers
                        value = self.xls_date_to_xlsx(value)
                    except Exception:
                        pass
                elif cell_type == xlrd.XL_CELL_NUMBER:
                    try:
                        ival = int(value)
                        if ival == value:
                            value = ival
                    except Exception:
                        pass
                elif cell_type == xlrd.XL_CELL_ERROR:
                    if value in xlrd.biffh.error_text_from_code:
                        value = xlrd.biffh.error_text_from_code[value]
                    else:
                        value = '#N/A'
                elif cell_type in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    value = ''
                elif cell_type == xlrd.XL_CELL_BOOLEAN:
                    value = ('false', 'true')[value]

                rw = row + 1
                cc = col + 1
                _ws.cell(rw, cc).value = value
                font, fill, border, alignment, number_format, protection = self.xls_style_to_xlsx(
                    _sheet.cell_xf_index(row, col))
                number_format = number_format or 'General'
                # if number_format != 'General':
                # print(f'({rw},{cc}).number_format = {number_format}')
                if isinstance(value, str):
                    if '\n' in value and not alignment.wrap_text:
                        alignment = copy.deepcopy(alignment)
                        alignment.wrap_text = True
                    if value[-1:] == '%' and number_format == 'General':
                        number_format = numbers.FORMAT_PERCENTAGE
                elif isinstance(value, datetime):
                    if number_format == 'General':
                        number_format = r'm\/d\/yyyy h\:mm\:ss AM/PM'
                    elif '/d/yy ' in number_format:
                        # For some unknown reason, 2-digit year formats are being stored
                        # when the user is specifying a 4-digit year
                        number_format = number_format.replace('/d/yy ', '/dd/yyyy ')
                    elif '/d\\/yy ' in number_format:
                        # For some unknown reason, 2-digit year formats are being stored
                        # when the user is specifying a 4-digit year
                        number_format = number_format.replace('/d\\/yy ', '/dd\\/yyyy ')
                    elif '/yy ' in number_format:
                        number_format = number_format.replace('/yy ', '/yyyy ')
                elif isinstance(value, date):
                    if number_format == 'General':
                        number_format = r'm\/d\/yyyy'
                    elif number_format.endswith('/d/yy'):
                        number_format = number_format.replace('/d/yy', '/dd/yyyy')
                    elif number_format.endswith('/d\\/yy'):
                        number_format = number_format.replace('/d\\/yy', '/dd\\/yyyy')
                    elif number_format.endswith('/yy'):
                        number_format += 'yy'  # Change to yyyy
                elif isinstance(value, tm):
                    if number_format == 'General':
                        number_format = r'h\:mm\:ss AM/PM'
                elif isinstance(value, timedelta):
                    if number_format == 'General':
                        number_format = '[h]:mm:ss'
                _ws.cell(rw, cc).font = font
                _ws.cell(rw, cc).fill = fill
                _ws.cell(rw, cc).border = border
                _ws.cell(rw, cc).alignment = alignment
                # if number_format != 'General':
                # print(f'({rw},{cc}).number_format = {number_format}, .value = {value}, type = {type(value)}')
                _ws.cell(rw, cc).number_format = number_format
                _ws.cell(rw, cc).protection = protection
                if protection.locked or protection.hidden:
                    _ws.protection.sheet = True
                tup = (row, col)
                if tup in _sheet.hyperlink_map:
                    hyperlink = _sheet.hyperlink_map[tup].url_or_path
                    _ws.cell(rw, cc).hyperlink = hyperlink
                    # ws.cell(rw, cc).style = 'Hyperlink'
                if tup in _sheet.cell_note_map:
                    comment = _sheet.cell_note_map[tup]
                    _ws.cell(rw, cc).comment = Comment(comment.text, comment.author)

        for crange in _sheet.merged_cells:
            rlo, rhi, clo, chi = crange
            _ws.merge_cells(start_row=rlo + 1,
                            start_column=clo + 1,
                            end_row=rhi,
                            end_column=chi)

        if _sheet.visibility:
            _ws.sheet_state = 'hidden'

        if _sheet.vert_split_pos != 0 or _sheet.horz_split_pos != 0:
            row = _sheet.horz_split_pos + 1
            col = min(_sheet.vert_split_pos + 1, 18278)
            _ws.freeze_panes = f'{get_column_letter(col)}{row}'

        _ws = None

    for _ in tqdm(
            run_in_thread_pool(
                worker,
                params=[{'_sheet': sheet, '_ws': ws} for sheet, ws in zip(self.book.sheets(), ws_list)],
                max_workers=DocParseConfig().config.get('excel_parse_max_worker', 1),
            ),
            total=len(self.book.sheets()),
            desc='xls转xlsx'
    ):
        pass

    if filename:
        wb.save(filename=filename)
        return filename
    return wb


def names_epilogue(self):
    blah = self.verbosity >= 2
    f = self.logfile
    if blah:
        print("+++++ names_epilogue +++++", file=f)
        print("_all_sheets_map", REPR(self._all_sheets_map), file=f)
        print("_extnsht_name_from_num", REPR(self._extnsht_name_from_num), file=f)
        print("_sheet_num_from_name", REPR(self._sheet_num_from_name), file=f)
    num_names = len(self.name_obj_list)
    for namex in range(num_names):
        nobj = self.name_obj_list[namex]
        # Convert from excel_sheet_index to scope.
        # This is done here because in BIFF7 and earlier, the
        # BOUNDSHEET records (from which _all_sheets_map is derived)
        # come after the NAME records.
        if self.biff_version >= 80:
            sheet_index = nobj.excel_sheet_index
            if sheet_index == 0:
                intl_sheet_index = -1  # global
            elif 1 <= sheet_index <= len(self._all_sheets_map):
                intl_sheet_index = self._all_sheets_map[sheet_index - 1]
                if intl_sheet_index == -1:  # maps to a macro or VBA sheet
                    intl_sheet_index = -2  # valid sheet reference but not useful
            else:
                # huh?
                intl_sheet_index = -3  # invalid
        elif 50 <= self.biff_version <= 70:
            sheet_index = nobj.extn_sheet_num
            if sheet_index == 0:
                intl_sheet_index = -1  # global
            else:
                sheet_name = self._extnsht_name_from_num[sheet_index]
                intl_sheet_index = self._sheet_num_from_name.get(sheet_name, -2)
        nobj.scope = intl_sheet_index

    for namex in range(num_names):
        nobj = self.name_obj_list[namex]
        # Parse the formula ...
        if nobj.macro or nobj.binary: continue
        if nobj.evaluated: continue
        try:
            evaluate_name_formula(self, nobj, namex, blah=blah)
        except XLRDError as e:
            if 'Excessive indirect references in NAME formula' != str(e):
                raise e
            logger.warning(f'{e}: {nobj.name}', exc_info=True)

    if self.verbosity >= 2:
        print("---------- name object dump ----------", file=f)
        for namex in range(num_names):
            nobj = self.name_obj_list[namex]
            nobj.dump(f, header="--- name[%d] ---" % namex)
        print("--------------------------------------", file=f)
    #
    # Build some dicts for access to the name objects
    #
    name_and_scope_map = {}  # (name.lower(), scope): Name_object
    name_map = {}  # name.lower() : list of Name_objects (sorted in scope order)
    for namex in range(num_names):
        nobj = self.name_obj_list[namex]
        name_lcase = nobj.name.lower()
        key = (name_lcase, nobj.scope)
        if key in name_and_scope_map and self.verbosity:
            fprintf(f, 'Duplicate entry %r in name_and_scope_map\n', key)
        name_and_scope_map[key] = nobj
        sort_data = (nobj.scope, namex, nobj)
        # namex (a temp unique ID) ensures the Name objects will not
        # be compared (fatal in py3)
        if name_lcase in name_map:
            name_map[name_lcase].append(sort_data)
        else:
            name_map[name_lcase] = [sort_data]
    for key in name_map.keys():
        alist = name_map[key]
        alist.sort()
        name_map[key] = [x[2] for x in alist]
    self.name_and_scope_map = name_and_scope_map
    self.name_map = name_map


Book.names_epilogue = names_epilogue


class _BaseParser(BaseParser):
    def lazy_parse(self, blob: Blob) -> Iterator[ParsedTable]:
        tables = self(blob)
        yield from tables

    def __call__(self, file: Blob) -> List[ParsedTable]:
        max_continuous_none = 100
        file_bytes = file.as_bytes()

        if file.path.endswith(".xlsx"):
            try:
                workbook = load_workbook(BytesIO(file_bytes), data_only=True)
            except OSError as e:
                if 'File contains no valid workbook part' in str(e):
                    logger.warning('监测到xlsx文件为xls编码，按照xls进行解析。')
                    workbook = to_xlsx(XLS2XLSX(file_bytes))
                else:
                    raise e
        else:
            try:
                workbook = to_xlsx(XLS2XLSX(file_bytes))
            except ValueError as e:
                if 'Excel xlsx file; not supported' in str(e):
                    logger.warning('监测到xls文件为xlsx编码，按照xlsx进行解析。')
                    workbook = load_workbook(BytesIO(file_bytes), data_only=True)
                else:
                    raise e

        sheet_names = workbook.sheetnames
        tables: list[ParsedTable | None] = [None for _ in range(len(sheet_names))]

        def worker(index, sheet_name):
            logger.info(f'解析sheet：{sheet_name}')

            sheet = workbook[sheet_name]
            max_row = sheet.max_row
            max_col = sheet.max_column
            # [html表格]
            data = sheet.values
            
            if max_row == 1:
                logger.info(f'解析sheet：{sheet_name}为空')
                return 
            columns = next(data)  # 第一行作为列名
            if self.document_type == 'financial':
                df = pd.DataFrame(data, columns=columns)
                table_html_content = df.to_html(index=False, classes="table table-striped", border=0)
            else:
                table_html_content = ""
            metadata = ParsedTableMetadata(source=file.source, file_path=file.source, table_name=sheet_name, table_html_content=table_html_content)

            # 记录合并单元格位置和值
            merged_cells = list(sheet.merged_cells.ranges)
            merged_cell2value = dict()
            merged_cell2position = dict()
            for merged_cell in merged_cells:
                cell_value = merged_cell.start_cell.internal_value
                cell_positions: list = list(merged_cell.cells)
                # 将excel 中的坐标信息，调整为从0开始
                for i in range(len(cell_positions)):
                    cell_positions[i] = (cell_positions[i][0] - 1, cell_positions[i][1] - 1)

                for pos in cell_positions:  # pos = (1,2)
                    merged_cell2value[pos] = cell_value
                    merged_cell2position[pos] = cell_positions

            max_row, max_col = truncate_row_col(max_row, max_col, sheet.cell, get=True, start_from_one=True)

            # 将包含合并单元格的拆开，合并单元格内的每个cell 都赋予merged cell 的值
            table_cells = []
            for r in range(max_row):
                for c in range(max_col):
                    if (r, c) in merged_cell2value:
                        cell = ParsedTableCell(value=merged_cell2value[(r, c)],
                                               position=(r, c),
                                               is_merged=True,
                                               merged_positions=merged_cell2position[(r, c)])
                        merged_cell2value.pop((r, c))
                        merged_cell2position.pop((r, c))
                    else:
                        cell = ParsedTableCell(value=sheet.cell(r + 1, c + 1).value,
                                               position=(r, c),
                                               is_merged=False)
                    table_cells.append(cell)
            tables[index] = ParsedTable(table_cells=table_cells, metadata=metadata)

        for _ in tqdm(
                run_in_thread_pool(
                    worker,
                    [{'index': index, 'sheet_name': sheet_name} for index, sheet_name in enumerate(sheet_names)],
                    max_workers=DocParseConfig().config.get('excel_parse_max_worker', 1),
                ),
                total=len(sheet_names),
                desc='解析excel'
        ):
            pass

        return list(filter(None, tables))


class Parser:
    @staticmethod
    def get_parser(document_type='naive') -> _BaseParser:
        return _BaseParser()
