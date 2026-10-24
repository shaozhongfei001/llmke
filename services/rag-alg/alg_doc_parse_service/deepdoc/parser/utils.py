from log import logger
from bs4 import BeautifulSoup


_PARSER_DICT = {
    'naive': '_NaiveParser',
    'book': '_BookParser',
    'laws': '_LawsParser',
    'table': '_TableParser'
}


def timer(func):
    import time

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        logger.debug(f'{func.__name__}函数的运行时间：{time.perf_counter() - start:.4f}s')
        return result

    return wrapper


# 根据cells生成HTML表格
def generate_html_table(table_cells):
    rows = {}
    for cell in table_cells:
        row_index = cell['row']
        if row_index not in rows:
            rows[row_index] = []
        rows[row_index].append(cell)
    # 生成HTML
    html = '<table border="1">'
    for _, row in rows.items():
        html += '<tr>\n'
        for cell in row:
            col_span = cell['col_span']
            row_span = cell['row_span']
            text = cell['text']
            html += f'<td colspan="{col_span}" rowspan="{row_span}">{text}</td>\n'
        html += '</tr>'
    html += '</table>'
    return html


# 自动识别表头层级
# 注：只考虑单表情况，合并后的多表需要先拆分
def identify_header_levels(table):
    levels = 0
    for tr in table.find_all('tr'):
        max_rowspan = 1
        for td in tr.find_all(['td', 'th']):
            rowspan = int(td.get('rowspan', 1))
            colspan = int(td.get('colspan', 1))
            if rowspan > max_rowspan:
                max_rowspan = rowspan
            if colspan > max_rowspan:
                max_rowspan = colspan
        if max_rowspan > levels:
            levels = max_rowspan
        if levels >= 3:  # 如果已经找到三级表头，可以提前退出
            break
    return levels


# 判断是否拆分, 拆分起始位置列表, 返回拆分结果
def is_split_table(html_table, split_section_positions, cells):
    def get_headers(cells, current_idx, header_len):
        return "".join([cells[current_idx+i]['text'] for i in range(header_len)])

    try:
        soup = BeautifulSoup(html_table, 'html.parser')
        table = soup.find('table')
        levels = identify_header_levels(table)
        flag_split = False
        if len(split_section_positions) <= 1:
            return flag_split, [], []
        headers = []
        headers_position = []
        # 找出按页拆分的起始位置
        # 考虑row不正确表示时默认levels*2
        for cell in cells:
            if cell['row'] < levels and len(headers) < levels * 2:
                headers.append(cell['text'])
            else:
                break
        if not headers:
            return flag_split, headers_position
        
        for idx, cell in enumerate(cells):
            if cell['text'] == headers[0] and idx + len(headers) < len(cells) and get_headers(cells, idx, len(headers)) == "".join(headers):
                headers_position.append(idx)
        if len(headers_position) != len(split_section_positions):
            return flag_split, [], []
        
        cells_split = [cells[i:j] for i, j in zip(headers_position, headers_position[1:] + [len(cells)])]
        html_table_split = list(map(lambda x: generate_html_table(x), cells_split))
        return True, cells_split, html_table_split
    except Exception as e:
        logger.warning(str(repr(e)))
        logger.warning("split_table ERROR")
        return False, [], []