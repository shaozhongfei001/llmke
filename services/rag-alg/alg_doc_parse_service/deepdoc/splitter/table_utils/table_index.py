"""
表格索引代码，判断表格结构，使用对应的切分/压缩策略进行表格索引。
"""
import os
import traceback
import json
import numpy as np
import math
import pandas as pd
from bs4 import BeautifulSoup
from deepdoc.output_object.table import ParsedTable, ParsedTableCell
from deepdoc.splitter.table_utils.table_compress import compress_table
from deepdoc.splitter.table_utils.table_loader import *
from deepdoc.utils import llm_chat, llm_completions, request_table_indicators
from server.process_reporter import ProcessReporter
from server.api_param import ModelInfo
from log import logger


def get_sheet_range(table_cells: list[ParsedTableCell]):
    # 计算表格的起始和结束范围
    row_range = [table_cells[0].position[0], table_cells[0].position[0]]
    col_range = [table_cells[0].position[1], table_cells[0].position[1]]

    for i, cell in enumerate(table_cells):
        r, c = cell.position
        if r <= row_range[0]:
            row_range[0] = r
        elif r >= row_range[1]:
            row_range[1] = r

        if c <= col_range[0]:
            col_range[0] = c
        elif c >= col_range[1]:
            col_range[1] = c

    return row_range, col_range


def detect_multiple_tables(parsed_table: ParsedTable) -> list[SplitTable]:
    """利用广度优先识别一张大表格中独立的子表"""
    if not parsed_table.table_cells or len(parsed_table.table_cells) == 0:
        return []

    row_range, col_range = get_sheet_range(parsed_table.table_cells)
    max_row = row_range[1] + 1 - row_range[0]
    max_column = col_range[1] + 1 - col_range[0]

    visited = [[False] * max_column for _ in range(max_row)]

    # 拆分表格 BFS 找到sheet 中所有独立的表格
    tables = []
    table_ranges = []
    table_matrix: list[list[None | ParsedTableCell]] = [[None] * max_column for _ in range(max_row)]

    for i, cell in enumerate(parsed_table.table_cells):
        r, c = cell.position
        table_matrix[r][c] = parsed_table.table_cells[i]

    for r in range(max_row):
        for c in range(max_column):
            try:
                cell = table_matrix[r][c]
                if not visited[r][c] and cell and cell.value is not None:
                    visited[r][c] = True
                    cell_queue = [(r, c)]
                    table_cells = [SplitTableCell(**cell.__dict__)]

                    table_range = [r, r + 1, c, c + 1]  # 表格坐标范围 left, right, up, down

                    while cell_queue:
                        i, j = cell_queue.pop(0)
                        for delta_i, delta_j in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
                            new_r, new_c = i + delta_i, j + delta_j
                            if not (0 <= new_r < max_row) or not (0 <= new_c < max_column):
                                continue

                            new_cell = table_matrix[new_r][new_c]
                            if not visited[new_r][new_c] and new_cell and new_cell.value is not None:
                                table_cells.append(SplitTableCell(**new_cell.__dict__))
                                # 更新坐标
                                table_range[0], table_range[1] = min(table_range[0], new_r), max(table_range[1], new_r)
                                table_range[2], table_range[3] = min(table_range[2], new_c), max(table_range[3], new_c)
                                cell_queue.append((new_r, new_c))
                                visited[new_r][new_c] = True

                    tables.append(table_cells)
                    table_ranges.append(table_range)
            except:
                logger.error(f"识别表格边界报错，文件名: {parsed_table.metadata.file_path}\n"
                             f"traceback: {traceback.format_exc()}")

    # 合并表格
    removed_tables = []
    for i in range(len(tables)):
        for j in range(len(tables)):
            if i == j:
                continue
            if i in removed_tables or j in removed_tables:
                continue

            range_a, range_b = table_ranges[i], table_ranges[j]
            if range_a[0] <= range_b[0] <= range_b[1] <= range_a[1] and \
                range_a[2] <= range_b[2] <= range_b[3] <= range_a[3]:
                tables[i].extend(tables[j])
                removed_tables.append(j)
    # logger.debug(f"原始表格{len(tables)}个，找到{len(removed_tables)}个被合并的表")

    return [SplitTable(table_cells,
                       row_range=(table_ranges[i][0], table_ranges[i][1]),
                       col_range=(table_ranges[i][2], table_ranges[i][3]),
                       file_name=parsed_table.metadata.file_path,
                       sheet_name=parsed_table.metadata.table_name if isinstance(parsed_table.metadata.table_name, str) else None)
            for i, table_cells in enumerate(tables) if i not in removed_tables]


def index_table(table: SplitTable, table_chunk_summary=True, model_info=ModelInfo):
    """表格索引"""
    # logger.debug("开始表格索引...")
    table_summary = None  # String
    table_chunks = []  # List[String]
    table_skeleton = None  # Table 压缩后表格

    if is_empty_table(table):
        return table_summary, table_chunks, table_skeleton

    # [table_chunk_summary]
    table_summary = ""
    if table.character_length <= 1000 or (len(table.cells) <= 20 and table.character_length <= 1500):  # 表格字数
        # 处理小型表格
        logger.debug("判断表格大小：小型表格")
        if table_chunk_summary:
            table_summary = summarize_table(markdown_encode(table.table_matrix), table, model_info)  # -> 存入表概述index
        
        title, headers = extract_table_info_from_summary(table_summary)
        logger.debug(f"表格摘要：{table_summary}")
        table_chunks = [(markdown_encode(table.table_matrix), get_chunk_position(table.table_matrix))]  # -> 存入表index
        logger.debug(f"表格内容：{table_chunks[0][0]}")
    else:
        logger.debug("判断表格大小：大型表格")
        if is_table_regular(table):
            logger.debug("判断表结构：规则表格")
            if table_chunk_summary:
                table_summary = summarize_table(table.markdown_encode(row_range=(0, 8)), table, model_info)

            title, headers = extract_table_info_from_summary(table_summary)
            table.title = title if title else table.title
            table.headers = headers

            table_chunks = split_regular_table(table)
            logger.debug("表格切片：")
            for chunk, pos in table_chunks[:2]:
                logger.debug("\n" + chunk)
            logger.debug(f"表格摘要：{table_summary}")
        else:
            logger.debug("判断表结构：不规则表格")
            table_skeleton = compress_table(table)
            if table_chunk_summary:
                table_summary = summarize_table(table_skeleton, table, model_info)

            title, headers = extract_table_info_from_summary(table_summary)

    table_chunks = [(chunk, pos) for chunk, pos in table_chunks if chunk.strip() != ""]
    return table_summary, table_chunks, table_skeleton


def _find_merged_range(positions):
    """找到合并单元格的四个角坐标"""
    _left, _right, _up, _down = 0, 0, 0, 0
    for i, pos in enumerate(positions):
        if i == 0:
            _left, _right = pos[1], pos[1]
            _up, _down = pos[0], pos[0]
        else:
            _left = min(_left, pos[1])
            _right = max(_right, pos[1])
            _up = min(_up, pos[0])
            _down = max(_down, pos[0])
    return _left, _right, _up, _down


def summarize_table(table_content: str, table_info: SplitTable, model_info) -> str:
    """利用大模型概括表格内容"""
    sys_prompt = """
    用精准的语言按照指定格式和要求为以下表格写一段文字描述，概括表格内容并且分析其中包含的信息。

    # 要求和说明
    1. 表格标题: 写出表格标题，可以按照表格内容和源文件名称总结。
    2. 表头: 列举表格表头行，用","分割。
    3. 表格内容: 描述表格内容，总结表格中的信息点。例如如果是某公司各年份的收益情况，那么可以进行各年份的趋势比较。
    4. 格式要求
        1. 按照格式返回，替换{}中的内容
        2. 表格以markdown形式提供
        3. 请注意超出长度的部分做了截断用"..."代表省略后文内容
        4. 表格中"[-]"表示省略了重复的合并单元格，代表着这个格子中的内容和上或左边的格子内容一致。

    # 格式
    表格标题: {}
    表头: {}
    表格内容: {}
    """
    if len(table_content) >= 5000:
        table_content = table_content[:5000] + "\n..."
        logger.warning(f"生成摘要表格太长截断.\n{table_content}")

    prompt = f"""
    源文件: {table_info.file_name or "/"}
    表格标题: {table_info.sheet_name or "/"}
    表格markdown:
    {table_content}
    """
    summary = llm_chat(sys_prompt=sys_prompt, user_prompt=prompt, model_info=model_info)
    summary = re.sub("<think>.*</think>", "", summary, flags=re.S).strip()
    file_info = ""
    if table_info.file_name:
        file_info = f"文件名：{os.path.split(table_info.file_name)[-1]}\n"
    if table_info.sheet_name:
        file_info = file_info + f"sheet名：{table_info.sheet_name}\n"
    return file_info + summary


def summarize_table_full(document, model_info) -> str:
    """利用大模型概括表格内容"""
    prompt = """<|im_start|>system
    You are a helpful assistant. 你是一个表格摘要助手<|im_end|>
    <|im_start|>user
    基于文件名、表格上文、表格内容markdown，生成表格摘要。
    约束条件：
    1.输出三个部分（表格摘要、行字段、列字段）；
    2.表格摘要以表上文与表格内容，用一句话总结简明扼要；
    3.行字段和列字段必须列举全，不能遗漏。

    ###文件名：{}
    ###表格上文：{}

    ###表格内容：
    {}

    /no_think<|im_end|>\n<|im_start|>assistant\n
    """
    def get_filename(file_path):
        if file_path:
            return file_path.split('/')[-1].rsplit('.', 1)[0]
        return file_path
    prompt = prompt.format(get_filename(document.metadata.file_path), document.metadata.table_preceding_context, document.metadata.table_html_content)
    summary = llm_completions(prompt, model_info)
    _char = "</think>"
    if _char in summary:
        summary = summary[summary.index(_char)+len(_char):].strip()
    return summary

def extract_date_type(document, model_info):
    """抽取期初期末"""
    prompt = """<|im_start|>system\nYou are a helpful assistant. 你是一个表格抽取助手<|im_end|>\n<|im_start|>user\n基于表格相关内容，识别表头且输出期初对应表头文本、期末对应表头文本。\n约束条件：\n1.输出json形式如：```json\n{"期初": "", "期末": ""}```;\n2.注意年报的期初非“本月数”，不能对应则为空，“本年累计数”可对应为年度期末，“上年累计数”可对应为年度期初;\n3.期初期末对应文本为表头文本，表达时间的列文本(如2024年、2023年等)\n"""
    prompt_tail = "\n/no_think<|im_end|>\n<|im_start|>assistant\n"
    date_type = {"期初": "", "期末": ""}
    table_preceding_context = document.metadata.table_preceding_context
    table_html_content = "\n\n###表格内容：" + document.metadata.table_html_content
    if table_preceding_context:
         prompt += "\n###表格上文：{}".format(table_preceding_context)
    prompt += table_html_content + prompt_tail
    response = llm_completions(prompt, model_info)
    pattern = r"```json\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, response)
    if matches:
        data = json.loads(matches[0])
        for k,v in data.items():
            if k in date_type:
                date_type[k] = v
    return date_type

def is_mutli_page_table(html_table_up, html_table_down, model_info):
    """判断是否是跨页表格"""
    prompt = """<|im_start|>system
    You are a helpful assistant. 你是一个表格助手<|im_end|>
    <|im_start|>user
    判断两个是否是跨页表格，返回YES/NO\n###表格1：\n{}\n###表格2：\n{}\n/no_think<|im_end|>\n<|im_start|>assistant\n"""
    prompt = prompt.format(html_table_up, html_table_down)
    response = llm_completions(prompt, model_info)
    if 'YES' in response:
        return True
    return False

def merge_multi_page_table(html_pages):
    # 多个分页HTML表格内容
    # 初始化一个空的BeautifulSoup对象
    merged_table = BeautifulSoup('<table></table>', 'html.parser')

    # 遍历所有HTML页面
    for html in html_pages:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                merged_table.table.append(row)

    # 构建最终HTML
    final_html = f"<html><body>{merged_table.prettify()}</table></body></html>"
    return final_html

def extract_company_info(document, model_info):
    """抽取公司信息、表名识别"""
    prompt = """<|im_start|>system
    You are a helpful assistant. 你是一个信息抽取助手<|im_end|>
    <|im_start|>user
    基于文件名、表格相关内容，抽取json信息。
    约束条件：
    1.输出json形式如：```json\n{"公司全称": "", "公司简称": "", "表名": "", "年份": "", "周期类型": ""}```；
    2.其中表名仅抽6种，合并资产负债表、合并利润表、合并现金流量表、母公司资产负债表、母公司利润表、母公司现金流量表，不在其中则为空字符；
    3.其中周期类型仅识别为“一季度、二季度、三季度、四季度、年度”中的一种，不在其中则为空字符\n
    """
    prompt_tail = "\n/no_think<|im_end|>\n<|im_start|>assistant\n"
    company_info = {"company_full_name": "", "company_short_name": "", "table_name": "", "year": "", "period_type": ""}
    company_info_mapping = {"公司简称": "company_short_name", "公司全称": "company_full_name", "年份": "year", "周期类型": "period_type"}
    table_name_mapping = {
        "资产负债表": "consolidated_balance",
        "利润表": "consolidated_income",
        "现金流量表": "consolidated_cash_flow",
        "损益表": "consolidated_income"
    }
    check_period = {"一季度", "二季度", "三季度", "四季度", "年度"}
    check_year = set(list(map(lambda x: str(x), range(1900,2100))))
    check_year = check_period | check_year
    def _transform(x, data):
        if x not in data:
            return ""
        if x == "年份" and data.get(x) in check_year:
            return data.get(x)
        if x == "周期类型" and data.get(x) in check_year:
            return data.get(x)
        if x == "公司简称" or x == "公司全称":
            return data.get(x)
        return ""
    def _transform_table_name(x, data):
        if x != "表名":
            return ""
        if "母公司" in data.get(x):
            return ""
        for k,v in table_name_mapping.items():
            if k in data.get(x):
                return v
        return ""
    # [跨页表格-其他页不需要处理]
    if document.metadata.table_multipage_flag and not document.metadata.table_html_content:
        return company_info
    filename = "###文件路径：" + document.metadata.file_path
    table_preceding_context = document.metadata.table_preceding_context
    table_html_content = "\n\n###表格内容：" + document.metadata.table_html_content
    if table_preceding_context:
        filename += "\n###表格上文：{}".format(table_preceding_context)
    prompt += filename + table_html_content + prompt_tail
    response = llm_completions(prompt, model_info)
    pattern = r"```json\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, response)
    if matches:
        data = json.loads(matches[0])
        for k,v in company_info_mapping.items():
            company_info[v] = _transform(k, data)
        company_info["table_name"] = _transform_table_name("表名", data)
    return company_info

def extract_indicator_rule(document, indicators, date_type, table_indicators):
    """根据html表格，期初期末，再获取到row名，得到指标值
    1.期初期末，获取所在列，考虑双栏表
    """
    def _get_row_cell(value, target_year):
        """
        1.优先完全匹配
        2.支持子字符串匹配
        """
        _indices = []
        if target_year in value:
            items_array = np.array(value)
            _indices = np.where(items_array == target_year)[0].tolist()
        if not _indices:
            for i, item in enumerate(value):
                if target_year in str(item):  # 判断 target_year 是否是 item 的子字符串
                    _indices.append(i)
        return _indices
    
    def _get_row(date_type, columns, values):
        """双栏，不考虑表头在第一列的情况"""
        """
        1.双栏，不考虑表头在第一列的情况
        2.考虑minerU的“2023年”变成“中位：元 2023年”
        """
        date_type_row = {"期初": [], "期末": []}
        for k, v in date_type.items():
            if v in columns:
                items_array = np.array(columns)
                indices = np.where(items_array == v)[0].tolist()
                date_type_row[k] = indices
                continue
            for value in values:
                indices = _get_row_cell(value, v)
                if indices:
                    date_type_row[k] = indices
                    break
        return date_type_row
    def _transform_value(v):
        """增加flag,考虑0.0为false"""
        try:
            if isinstance(v, str) and v:
                return True, round(float(v), 2)
            elif isinstance(v, float) and not math.isnan(v):
                return True, v
        except:
            pass
        return False, v
    def _update(cur_df, indicator_name, date_type_row, indicator_values, idx):
        """dataframe的名称全匹配、模糊匹配，更新value"""
        indicator_raw = ""
        for cur in cur_df.values.tolist():
            bop_idx =  [eop for eop in date_type_row["期初"] if eop > idx]
            eop_idx = [bop for bop in date_type_row["期末"] if bop > idx]
            if bop_idx:
                _flag, value = _transform_value(cur[bop_idx[0]])
                if _flag and not indicator_values[indicator_name]["期初"]:
                    indicator_values[indicator_name]["期初"] = value
                    indicator_raw = cur[idx]
            if eop_idx:
                _flag, value = _transform_value(cur[eop_idx[0]])
                if _flag and not indicator_values[indicator_name]["期末"]:
                    indicator_values[indicator_name]["期末"] = value
                    indicator_raw = cur[idx]
        return indicator_values, indicator_raw

    df = pd.read_html(document.metadata.table_html_content)[0]
    columns = list(df.columns)
    values = df.values.tolist()
    date_type_row = _get_row(date_type, columns, values)
    indicators_raw = {}
    for indicator_name, alias in indicators.items():
        for indicator in alias:
            for idx, col in enumerate(columns):
                if idx in date_type_row["期初"]:
                    continue
                if idx in date_type_row["期末"]:
                    continue
                # equal
                cur_df = df[df[col].eq(indicator).fillna(False)]
                table_indicators, indicator_raw = _update(cur_df, indicator_name, date_type_row, table_indicators, idx)
                if indicator_name not in indicators_raw or not indicators_raw[indicator_name]:
                    indicators_raw[indicator_name] = indicator_raw
                # contains
                if indicator_name == "负债合计":
                    continue
                if not table_indicators[indicator_name]["期初"] or not table_indicators[indicator_name]["期末"]:
                    cur_df = df[df[col].astype(str).str.contains(indicator, na=False)]
                    table_indicators, indicator_raw = _update(cur_df, indicator_name, date_type_row, table_indicators, idx)
                    if indicator_name not in indicators_raw or not indicators_raw[indicator_name]:
                        indicators_raw[indicator_name] = indicator_raw
    return table_indicators, indicators_raw

def extract_indicator_llm(document, indicators, date_type, table_indicators, model_info):
    """补充抽取结果-llm"""
    def _extract_bop_eop(bop_eop, v):
        _result = {}
        try:
            if isinstance(v, str) and v:
                _result[bop_eop] = round(float(v), 2)
            elif isinstance(v, float) and not math.isnan(v):
                _result[bop_eop] = v
        except Exception as e:
            pass
        return _result

    def _extract(_prompt):
        response = llm_completions(_prompt, model_info)
        pattern = r"```json\s*([\s\S]*?)\s*```"
        matches = re.findall(pattern, response)
        llm_extract = {}
        try:
            if matches:
                data = json.loads(matches[0])
                for k,v in data.items():
                    if k == '期初':
                        llm_extract.update(_extract_bop_eop(k, v))
                    if k == '期末':
                        llm_extract.update(_extract_bop_eop(k, v))
        except Exception as e:
            pass
        return llm_extract
    prompt = """<|im_start|>system\nYou are a helpful assistant. 你是一个表格抽取助手<|im_end|>\n<|im_start|>user\n基于表格内容，识别指定财务指标的期初值、期末值。"""
    
    prompt_date = "表格中期初为{}，期末为{}。".format(date_type['期初'], date_type['期末'])
    prompt_constraint = """\n约束条件：\n1.输出json形式如：```json\n{"期初": "", "期末": ""}```;"""
    prompt += prompt_date + prompt_constraint
    prompt_tail = "\n/no_think<|im_end|>\n<|im_start|>assistant\n"
    
    for indicator_name, alias in indicators.items():
        if table_indicators[indicator_name]["期初"] is None or table_indicators[indicator_name]["期末"] is None:
            prompt_indicator = "\n2.指定财务指标：{};\n3.若不存在该财务指标，不能编造，其值返回为空.\n".format(indicator_name)
            prompt_table_content = "\n\n###表格内容：{}\n".format(document.metadata.table_html_content)
            
            supplementary_extract = _extract(prompt+prompt_indicator+prompt_table_content+prompt_tail)
            for k, v in supplementary_extract.items():
                if isinstance(v, float): table_indicators[indicator_name][k] = v
    return table_indicators


def preprocess_excel():
    """xlsx、xls、csv预处理表格
    1.考虑双栏
    2.表头识别
    """
    pass

def get_table_indicator(x, url_table_indicator):
    """
    从接口获取表对应的指标名称及别名
    """
    table_indicators_expand = {
        "consolidated_balance": {"货币资金": ["货币资金"], "短期投资": ["短期投资"], "交易性金融资产": ["交易性金融资产"], "应收票据": ["应收票据"], "应收账款": ["应收账款", "应收帐款"], "预付账款": ["预付账款", "预付款项"], "应收利息": ["应收利息"], "应收股利": ["应收股利"], "其他应收款": ["其他应收款"], "存货": ["存货"], "一年内到期的非流动资产": ["一年内到期的非流动资产"], "其他流动资产": ["其他流动资产"], "结算备付金": ["结算备付金"], "拆成资金": ["拆成资金"],"以公允价值计量且其变动计入当期损益的金融资产": ["以公允价值计量且其变动计入当期损益的金融资产"],"衍生金融资产": ["衍生金融资产"],"应收款项融资": ["应收款项融资"],"应收保费": ["应收保费"],"应收分保账款": ["应收分保账款"],"应收分保合同准备金": ["应收分保合同准备金"],"买入返售金融资产": ["买入返售金融资产"],"合同资产": ["合同资产"],"持有待售资产": ["持有待售资产"],"流动资产合计": ["流动资产合计"], "可供出售金融资产": ["可供出售金融资产"], "持有至到期投资": ["持有至到期投资"], "长期应收款": ["长期应收款"], "长期股权投资": ["长期股权投资"], "长期合债权反投资": ["长期合债权反投资"], "投资性房地产": ["投资性房地产"], "固定资产原价": ["固定资产原价"], "累计折旧": ["累计折旧"], "在建工程": ["在建工程"],  "固定资产清理": ["固定资产清理"], "生产性生物资产": ["生产性生物资产"], "油气资产": ["油气资产"], "无形资产": ["无形资产"], "开发支出": ["开发支出"], "商誉": ["商誉"], "长期待摊费用": ["长期待摊费用"], "递延所得税资产": ["递延所得税资产"], "其他非流动资产": ["其他非流动资产"], "发放贷款及垫款": ["发放贷款及垫款"], "债券投资": ["债券投资"],"其他债券投资": ["其他债券投资"],"其他权益工具投资": ["其他权益工具投资"],"其他非流动金融资产": ["其他非流动金融资产"],"固定资产": ["固定资产"],"固定资产减值准备": ["固定资产减值准备"], "使用权资产": ["使用权资产"],"非流动资产合计": ["非流动资产合计"], "资产总计": ["资产总计"], "短期借款": ["短期借款"], "交易性金融负债": ["交易性金融负债"], "应付票据": ["应付票据"], "应付账款": ["应付账款"], "预收账款": ["预收账款", "预收款项"], "应付职工薪酬": ["应付职工薪酬"], "应交税费": ["应交税费"], "应付利息": ["应付利息"], "应付利润": ["应付利润"], "应付股利": ["应付股利"], "其他应付款": ["其他应付款"], "一年内到期的非流动负债": ["一年内到期的非流动负债"], "其他流动负债": ["其他流动负债"], "向中央银行借款": ["向中央银行借款"], "拆入资金": ["拆入资金"],"衍生金融负债": ["衍生金融负债"],"合同负债": ["合同负债"],"卖出回购金融资产款": ["卖出回购金融资产款"],"吸收存款及同业存放": ["吸收存款及同业存放"],"代理买卖证券款": ["代理买卖证券款"],"代理承销证券款": ["代理承销证券款"],"应付手续费及佣金": ["应付手续费及佣金"],"应付分保账款": ["应付分保账款"],"持有待售负债": ["持有待售负债"],"流动负债合计": ["流动负债合计"],"长期借款": ["长期借款"], "应付债券": ["应付债券"], "应付债券-优先股": ["应付债券-优先股"], "应付债券-永续债": ["应付债券-永续债"], "长期应付款": ["长期应付款"], "专项应付款": ["专项应付款"], "预计负债": ["预计负债"], "递延收益": ["递延收益"], "递延所得税负债": ["递延所得税负债"], "其他非流动负债": ["其他非流动负债"], "保险合同准备金": ["保险合同准备金"],"租赁负债": ["租赁负债"],"非流动负债合计": ["非流动负债合计"], "负债合计": ["负债合计"], "实收资本（或股本）": ["实收资本", "股本"], "资本公积": ["资本公积"], "库存股": ["库存股"], "盈余公积": ["盈余公积"], "未分配利润": ["未分配利润"], "外币报表折算差额": ["外币报表折算差额"], "少数股东权益": ["少数股东权益"], "其他权益工具": ["其他权益工具"],"其他权益工具-优先股": ["其他权益工具-优先股"],"其他权益工具-永续债": ["其他权益工具-永续债"], "其他综合收益": ["其他综合收益"],"专项储备": ["专项储备"],"一般风险准备": ["一般风险准备"],"归属于母公司股东权益合计": ["归属于母公司股东权益合计"],"所有者权益合计": ["所有者权益（或股东权益）合计", "所有者权益合计"], "负债和所有者权益总计": ["负债和所有者权益总计", "负债和所有者权益（或股东权益）总计"]},
        "consolidated_income": {"营业总收入": ["营业总收入"], "营业收入": ["营业收入"], "营业总成本": ["营业总成本"], "营业成本": ["营业成本"], "营业税金及附加": ["营业税金及附加"], "销售费用": ["销售费用"], "管理费用": ["管理费用"], "资产减值损失": ["资产减值损失"], "公允价值变动收益": ["公允价值变动收益"], "投资收益": ["投资收益"], "财务费用": ["财务费用"], "营业利润": ["营业利润"], "营业外收入": ["营业外收入"], "营业外支出": ["营业外支出"], "所得税费用": ["所得税费用"], "归属母公司所有者的净利润": ["归属母公司所有者的净利润"], "少数股东损益": ["少数股东损益"], "利润总额": ["利润总额", '利润总额（亏损以"-"号表示）'], "净利润": ["净利润", '净利润（亏损以"-"号表示）'], "利息支出": ["利息支出"], "每股收益": ["每股收益"], "利息费用": ["利息费用"]},
        "consolidated_cash_flow": {"销售商品、提供劳务收到的现金": ["销售商品、提供劳务收到的现金"], "收到的税费返还": ["收到的税费返还"], "收到其他与经营活动有关的现金": ["收到其他与经营活动有关的现金"], "经营活动现金流入小计": ["经营活动现金流入小计"], "购买商品、接受劳务支付的现金": ["购买商品、接受劳务支付的现金"], "支付给职工以及为职工支付的现金": ["支付给职工以及为职工支付的现金"], "支付的各项税费": ["支付的各项税费"], "支付其他与经营活动有关的现金": ["支付其他与经营活动有关的现金"], "经营活动现金流出小计": ["经营活动现金流出小计"], "经营活动产生的现金流量净额": ["经营活动产生的现金流量净额"], "收回投资收到的现金": ["收回投资收到的现金"], "取得投资收益收到的现金": ["取得投资收益收到的现金"], "处置固定资产、无形资产和其他长期资产收回的现金净额": ["处置固定资产、无形资产和其他长期资产收回的现金净额"], "处置子公司及其他营业单位收到的现金净额": ["处置子公司及其他营业单位收到的现金净额"], "收到其他与投资活动有关的现金": ["收到其他与投资活动有关的现金"], "投资活动现金流入小计": ["投资活动现金流入小计"], "购建固定资产、无形资产和其他长期资产支付的现金": ["购建固定资产、无形资产和其他长期资产支付的现金", "购建固定资产、无形资产和其他长期资产所支付的现金"], "投资支付的现金": ["投资支付的现金"], "取得子公司及其他营业单位支付的现金净额": ["取得子公司及其他营业单位支付的现金净额"], "支付其他与投资活动有关的现金": ["支付其他与投资活动有关的现金"], "投资活动现金流出小计": ["投资活动现金流出小计"], "投资活动产生的现金流量净额": ["投资活动产生的现金流量净额"], "吸收投资收到的现金": ["吸收投资收到的现金"], "取得借款收到的现金": ["取得借款收到的现金"], "收到其他与筹资活动有关的现金": ["收到其他与筹资活动有关的现金"], "筹资活动现金流入小计": ["筹资活动现金流入小计"], "偿还债务支付的现金": ["偿还债务支付的现金"], "分配股利、利润或偿付利息支付的现金": ["分配股利、利润或偿付利息支付的现金"], "支付其他与筹资活动有关的现金": ["支付其他与筹资活动有关的现金"], "筹资活动现金流出小计": ["筹资活动现金流出小计"], "筹资活动产生的现金流量净额": ["筹资活动产生的现金流量净额"], "汇率变动对现金及现金等价物的影响": ["汇率变动对现金及现金等价物的影响"], "现金及现金等价物净增加额": ["现金及现金等价物净增加额"], "期初现金及现金等价物余额": ["期初现金及现金等价物余额"], "期末现金及现金等价物余额": ["期末现金及现金等价物余额"]}
    }
    # return table_indicators_expand[x]
    def get_alias(item):
        if not item.get('alias'):
            return [item['indicatorName']]
        alias = {item['indicatorName']}
        for indicator_alias in item.get('alias'):
            for n in indicator_alias.split('、'):
                alias.add(n.strip())
        return list(alias)
        
    table_name_mapping = {"consolidated_balance": "合并资产负债表", "consolidated_income": "合并利润表","consolidated_cash_flow": "合并现金流量表"}
    table_indicators_mapping = {k: {} for k, _ in table_name_mapping.items()}
    for k, _ in table_indicators_mapping.items():
        table_indicators = request_table_indicators(table_name_mapping[k], url_table_indicator)
        for item in table_indicators:
            table_indicators_mapping[k][item['indicatorName']] = get_alias(item)

    
    for k, v in table_indicators_expand.items():
        if k not in table_indicators_mapping:
            continue
        for name in v:
            if name not in table_indicators_mapping[k]:
                continue
            table_indicators_mapping[k][name] = list(set(table_indicators_mapping[k][name]) & set(v[name]))
    return table_indicators_mapping[x]

def insert_indicator_to_sql(company_info, indicators, table_indicators, indicators_raw, user_id, knowledge_base_name, knowledge_base_id, file_path, file_id):
    """
    指标值，插入到mysql
    """
    bop_eop_mapping = {"期初": 0, "期末": 1}
       
    if not file_path or not file_id:
        return
    with ProcessReporter() as process_reporter:
        for k in indicators:
            table_info = {"creator_id": user_id, "knowledge_base_name": knowledge_base_name,
                  "knowledge_base_id": knowledge_base_id if knowledge_base_id else None,
                  "file_path": file_path, "file_id": file_id
                  }
            table_info["company_short_name"] = company_info['company_short_name']
            table_info["year"] = company_info['year']
            table_info["period_type"] = company_info['period_type']
            table_info["company_full_name"] = company_info['company_full_name'] if company_info['company_full_name'] else None
            for bop_eop, date_type in bop_eop_mapping.items():
                if table_indicators[k][bop_eop] is None:
                    table_info["indicator_name"] = k
                    table_info["indicator_raw"] = str(indicators_raw.get(k, '')) if indicators_raw.get(k, '') else str(k)
                    table_info["date_type"] = date_type
                    table_info["indicator_value"] = None
                    table_info["status"] = 0
                else:
                    table_info["indicator_name"] = k
                    table_info["indicator_raw"] = str(indicators_raw.get(k, '')) if indicators_raw.get(k, '') else str(k)
                    table_info["date_type"] = date_type
                    table_info["indicator_value"] = str(table_indicators[k][bop_eop])
                    table_info["status"] = 1
                process_reporter.dao.insert(company_info['table_name'], **table_info)


def extract_pipeline(document, user_id, knowledge_base_id, url_table_indicator, model_info):
    """
    1.xlsx、xls、csv预处理表格，考虑双栏
    2.pdf：公司信息、表名抽取-获取表指标-指标值抽取-插入mysql
    """
    company_info = extract_company_info(document, model_info)
    if not company_info['company_short_name'] or \
        not company_info['table_name'] or \
        not company_info["period_type"] or \
            not company_info["year"]:
        return
    
    indicators = get_table_indicator(company_info["table_name"], url_table_indicator)
    date_type = extract_date_type(document, model_info)
    if not date_type["期初"] or not date_type["期末"]:
        return
    table_indicators = {k: {"期初": None, "期末": None} for k in indicators}
    table_indicators, indicators_raw = extract_indicator_rule(document, indicators, date_type, table_indicators)
    table_indicators = extract_indicator_llm(document, indicators, date_type, table_indicators, model_info)
    insert_indicator_to_sql(company_info, indicators, table_indicators, indicators_raw, user_id, document.metadata.knowledge_base_name, knowledge_base_id, document.metadata.file_path, document.metadata.file_id)
 

def extract_table_info_from_summary(summary_text: str) -> (str, [str]):
    """从大模型输出的表格summary 中提取标题、表头信息"""

    title_pattern = re.search("表格标题[:：](.*)", summary_text)
    header_pattern = re.search("表头[:：](.*)", summary_text)

    title = ""
    headers = []

    if title_pattern:
        title = title_pattern.group(1).strip()

    if header_pattern:
        header_string = header_pattern.group(1).strip()
        headers = header_string.split(",")
    return title, headers


def is_table_regular(table: SplitTable) -> bool:
    """
    判断表格是否规则。
    判断依据：表格除了首行/尾行/首列/末列，结构一致，不存在合并单元格等问题。
    """

    # for cell in table.cells:
    #     if not cell.is_merged_cell:
    #         continue
    #     left, right, up, down = _find_merged_range(cell.merged_positions)
    #     # 合并单元格在首列或者末列
    #     if left <= 1 or right >= table.columns_count-1:
    #         continue
    #     # 合并单元格在首行或者首列
    #     if up <= 3 or down >= table.columns_count-1:
    #         continue
    #     return False
    return True


def is_empty_table(table: SplitTable) -> bool:
    """判断表格是否为空"""
    if all([cell.value is None or str(cell.value).strip() == "" for cell in table.cells]):
        return True
    if len(table.cells) <= 2:
        return True
    return False


def split_regular_table(table: SplitTable, neighbour=3):
    """
    标准表格切分，保留表头、表尾、首末行
    neighbour: 每个块包含的行数/列数，动态调整
    """

    def get_split_strategy() -> bool:
        """确定表格的切分方向。 True 按行切分; False 按列切分
            判定规则：
            1. 如果大模型摘要中找到了表头信息，那么根据headers 的情况确定切分方向
            2. 其他：按照行列的数据类型来判定。
        """

        if table.headers and table.columns_count != table.rows_count:
            if len(table.headers) == table.columns_count:  # 大模型提取的表头个数和 列数一样，说明可以按行切。
                return True
            if len(table.headers) == table.rows_count:
                return False

        table_row_type_counter = Counter(table.row_value_types)
        table_col_type_counter = Counter(table.col_value_types)
        # 判断这个表格是按列切分还是按行切分
        if table_row_type_counter.get(CellValueType.OTHER, 0) >= table.rows_count * 0.6:
            return True
        if table.col_value_types[0] in [CellValueType.DIGIT, CellValueType.DATE]:  # 首列是序号或者日期
            return True
        if table.rows_count >= table.columns_count * 3:  # 行数比列数多很多
            return True

        if all(
            vt in [CellValueType.SHORT_STRING, CellValueType.LONG_STRING, CellValueType.EMPTY, CellValueType.OTHER] for
            vt in table.row_value_types) \
            and all(
            vt in [CellValueType.SHORT_STRING, CellValueType.LONG_STRING, CellValueType.EMPTY, CellValueType.OTHER] for
            vt in table.col_value_types):
            # 行、列都大多为string 不符合常规的表格形式
            return True
        return False

    split_by_row = get_split_strategy()
    logger.debug(f"按行切分: {split_by_row}")

    # 根据字符长度动态调整块大小
    if table.character_length > 600:
        if table.character_length > 5000:
            neighbour = 10
        elif table.character_length >= 3000:
            neighbour = 5
        else:
            neighbour = 3
    else:
        neighbour = 3

    # 根据表格的行数和列数进一步调整
    if table.rows_count > 50:
        neighbour = max(neighbour, 5)
    elif table.rows_count < 10:
        neighbour = min(neighbour, 2)

    if table.columns_count > 10:
        neighbour = max(neighbour, 4)

    i = 0
    table_chunks = []
    headers = []
    if split_by_row:
        if table.title_positions:
            # 跳过标题行
            title_row = set(pos[0] for pos in table.title_positions)
        else:
            title_row = set()

        while i < table.rows_count and all(cell.value_type == CellValueType.EMPTY for cell in table.table_matrix[i]):
            i += 1

        if split_by_row and len(table.headers) == table.rows_count:
            headers = table.headers
        else:
            start_i = i
            while i < len(table.row_value_types) and table.row_value_types[i] in [CellValueType.SHORT_STRING,
                                                                                  CellValueType.LONG_STRING]:
                if i not in title_row:
                    headers.append(table.table_matrix[i])
                i += 1

            # 表头行数太长，可能是表头未正确识别造成的
            if len(headers) > 3:
                headers = []
                i = start_i

        logger.debug(f"headers: {len(headers)}")
        for h in headers:
            logger.debug(f"# {h}")

        # 切分表格
        while i < table.rows_count:
            table_chunk = []
            di = 0
            content_length = 0
            while di < neighbour and i + di < table.rows_count and content_length <= 400:
                table_chunk.append(table.table_matrix[i + di])
                content_length += sum([len(str(cell.value)) for cell in table.table_matrix[i + di] if cell.value])
                di += 1
            table_chunks.append(table_chunk)
            i += di
    else:
        headers = []
        if len(table.headers) == table.columns_count:
            headers = table.headers
        else:
            start_i = i
            while i < len(table.col_value_types) and table.col_value_types[i] in [CellValueType.SHORT_STRING,
                                                                                  CellValueType.LONG_STRING]:
                headers.append([row[i] for row in table.table_matrix])
                i += 1

            # 表头行数太长，可能是表头未正确识别造成的
            if len(headers) > 3:
                headers = []
                i = start_i

        logger.debug(f"headers: {len(headers)}")
        for h in headers:
            logger.debug(f"# {h}")

        while i < table.rows_count:
            table_chunks.append([row[i:i + neighbour] for row in table.table_matrix])
            i += neighbour

    chunks = []
    for chunk in table_chunks:
        chunk_string = markdown_encode(chunk, headers)
        if len(chunk_string) >= 8000:
            logger.warning(f"表格切片过长 截断")
            chunk_string = chunk_string[:8000]
        chunk_position = get_chunk_position(chunk)
        chunks.append([chunk_string, chunk_position])

    return chunks


def markdown_encode(table_matrix: list[list[SplitTableCell]], headers=None, empty_token="", merge_token="[-]") -> str:
    """
    table_matrix:
    headers: markdown 标题行
    empty_token: 表示cell为空的标记
    merge_token: 表示合并单元格省略标记
    """

    def _get_cell_string_matrix(matrix: list[list[SplitTableCell]]):
        """获取矩阵值"""
        visited_cells = set()
        cell_string_matrix = [[empty_token] * len(matrix[0]) for _ in range(len(matrix))]
        cell_position_matrix = [[None] * len(matrix[0]) for _ in range(len(matrix))]
        for i, row in enumerate(matrix):
            for j, cell in enumerate(row):
                cell_value = str(cell.value).replace("\n", "")

                if tuple(cell.relative_position) in visited_cells and (
                    len(cell_value) >= 30 or len(cell.merged_positions) >= 5):
                    cell_string_matrix[i][j] = merge_token
                    cell_position_matrix[i][j] = cell.relative_position
                else:
                    if cell_value.strip() == "" or cell_value == "None":
                        continue
                    cell_string_matrix[i][j] = cell_value
                    cell_position_matrix[i][j] = cell.relative_position
                    for pos in cell.merged_positions:
                        visited_cells.add(tuple(pos))
        return cell_string_matrix, cell_position_matrix

    # print("# headers")
    # print(headers)
    # for row in table_matrix:
    #     print(row)
    markdown_lines = []
    if not table_matrix:
        return ""
    column_size = len(table_matrix[0])
    have_header = True
    if not headers:
        header = [empty_token] * column_size
        have_header = False
    elif isinstance(headers[0], str):
        header = headers
    elif len(headers) == 1:  # 标题行不存在合并单元格
        header = _get_cell_string_matrix(headers)[0][0]
    else:
        header_matrix, _ = _get_cell_string_matrix(headers)
        header = []
        for head_cells in zip(*header_matrix):
            head_cell = "-".join([cell for cell in head_cells if cell != empty_token and cell != merge_token])
            header.append(head_cell)
    if len(header) < column_size:
        header.extend([empty_token] * (column_size - len(headers[0])))
    if have_header:
        markdown_lines.append('|'.join(header))
        markdown_lines.append('|'.join([' :---: ' for _ in range(column_size)]))

    table_string_matrix, position_string_matrix = _get_cell_string_matrix(table_matrix)
    for row in table_string_matrix:
        line = "|".join(row)
        markdown_lines.append(line)

    markdown_string = "\n".join([f"|{line}|" for line in markdown_lines])
    return markdown_string


def get_chunk_position(table_matrix: list[list[SplitTableCell]]) -> list[list[int]]:
    chunk_positions = []
    for row in table_matrix:
        for cell in row:
            chunk_positions.append(cell.abs_position)
    return chunk_positions

# def process_excel_file(file_path):
#     sheet_blocks = read_excel(file_path)
#     for sheet, tables in sheet_blocks.items():
#         logger.debug("====="*30)
#         logger.debug("Excel 读取结果：")
#         logger.debug("\tSheetName:", sheet)
#         logger.debug("\tTableCount:", len(tables))
#         for table in tables:
#             index_table(table, sheet)
