# -*- coding: utf-8 -*-


from typing import List
import httpx
import traceback
import re
import json
from app.operators.retriever.base import Retriever
from app.base import CECTableRetrieveConfig
from app.operators.client.llm_client import LLMClient


class DBRetriever(Retriever):

    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
        self.client = LLMClient(
            config=config,
            logger=logger
        )

    async def get_table_indicators(self, url_table_indicator):
        """
        从接口获取表对应的指标名称及别名
        """
        table_indicators_expand = {
            "consolidated_balance": {"货币资金": ["货币资金"], "短期投资": ["短期投资"], "交易性金融资产": ["交易性金融资产"], "应收票据": ["应收票据"], "应收账款": ["应收账款", "应收帐款"], "预付账款": ["预付账款", "预付款项"], "应收利息": ["应收利息"], "应收股利": ["应收股利"], "其他应收款": ["其他应收款"], "存货": ["存货"], "一年内到期的非流动资产": ["一年内到期的非流动资产"], "其他流动资产": ["其他流动资产"], "结算备付金": ["结算备付金"], "拆成资金": ["拆成资金"],"以公允价值计量且其变动计入当期损益的金融资产": ["以公允价值计量且其变动计入当期损益的金融资产"],"衍生金融资产": ["衍生金融资产"],"应收款项融资": ["应收款项融资"],"应收保费": ["应收保费"],"应收分保账款": ["应收分保账款"],"应收分保合同准备金": ["应收分保合同准备金"],"买入返售金融资产": ["买入返售金融资产"],"合同资产": ["合同资产"],"持有待售资产": ["持有待售资产"],"流动资产合计": ["流动资产合计"], "可供出售金融资产": ["可供出售金融资产"], "持有至到期投资": ["持有至到期投资"], "长期应收款": ["长期应收款"], "长期股权投资": ["长期股权投资"], "长期合债权反投资": ["长期合债权反投资"], "投资性房地产": ["投资性房地产"], "固定资产原价": ["固定资产原价"], "累计折旧": ["累计折旧"], "在建工程": ["在建工程"],  "固定资产清理": ["固定资产清理"], "生产性生物资产": ["生产性生物资产"], "油气资产": ["油气资产"], "无形资产": ["无形资产"], "开发支出": ["开发支出"], "商誉": ["商誉"], "长期待摊费用": ["长期待摊费用"], "递延所得税资产": ["递延所得税资产"], "其他非流动资产": ["其他非流动资产"], "发放贷款及垫款": ["发放贷款及垫款"], "债券投资": ["债券投资"],"其他债券投资": ["其他债券投资"],"其他权益工具投资": ["其他权益工具投资"],"其他非流动金融资产": ["其他非流动金融资产"],"固定资产": ["固定资产"],"固定资产减值准备": ["固定资产减值准备"], "使用权资产": ["使用权资产"],"非流动资产合计": ["非流动资产合计"], "资产总计": ["资产总计"], "短期借款": ["短期借款"], "交易性金融负债": ["交易性金融负债"], "应付票据": ["应付票据"], "应付账款": ["应付账款"], "预收账款": ["预收账款", "预收款项"], "应付职工薪酬": ["应付职工薪酬"], "应交税费": ["应交税费"], "应付利息": ["应付利息"], "应付利润": ["应付利润"], "应付股利": ["应付股利"], "其他应付款": ["其他应付款"], "一年内到期的非流动负债": ["一年内到期的非流动负债"], "其他流动负债": ["其他流动负债"], "向中央银行借款": ["向中央银行借款"], "拆入资金": ["拆入资金"],"衍生金融负债": ["衍生金融负债"],"合同负债": ["合同负债"],"卖出回购金融资产款": ["卖出回购金融资产款"],"吸收存款及同业存放": ["吸收存款及同业存放"],"代理买卖证券款": ["代理买卖证券款"],"代理承销证券款": ["代理承销证券款"],"应付手续费及佣金": ["应付手续费及佣金"],"应付分保账款": ["应付分保账款"],"持有待售负债": ["持有待售负债"],"流动负债合计": ["流动负债合计"],"长期借款": ["长期借款"], "应付债券": ["应付债券"], "应付债券-优先股": ["应付债券-优先股"], "应付债券-永续债": ["应付债券-永续债"], "长期应付款": ["长期应付款"], "专项应付款": ["专项应付款"], "预计负债": ["预计负债"], "递延收益": ["递延收益"], "递延所得税负债": ["递延所得税负债"], "其他非流动负债": ["其他非流动负债"], "保险合同准备金": ["保险合同准备金"],"租赁负债": ["租赁负债"],"非流动负债合计": ["非流动负债合计"], "负债合计": ["负债合计"], "实收资本（或股本）": ["实收资本", "股本"], "资本公积": ["资本公积"], "库存股": ["库存股"], "盈余公积": ["盈余公积"], "未分配利润": ["未分配利润"], "外币报表折算差额": ["外币报表折算差额"], "少数股东权益": ["少数股东权益"], "其他权益工具": ["其他权益工具"],"其他权益工具-优先股": ["其他权益工具-优先股"],"其他权益工具-永续债": ["其他权益工具-永续债"], "其他综合收益": ["其他综合收益"],"专项储备": ["专项储备"],"一般风险准备": ["一般风险准备"],"归属于母公司股东权益合计": ["归属于母公司股东权益合计"],"所有者权益合计": ["所有者权益（或股东权益）合计", "所有者权益合计"], "负债和所有者权益总计": ["负债和所有者权益总计", "负债和所有者权益（或股东权益）总计"]},
            "consolidated_income": {"营业总收入": ["营业总收入"], "营业收入": ["营业收入"], "营业总成本": ["营业总成本"], "营业成本": ["营业成本"], "营业税金及附加": ["营业税金及附加"], "销售费用": ["销售费用"], "管理费用": ["管理费用"], "资产减值损失": ["资产减值损失"], "公允价值变动收益": ["公允价值变动收益"], "投资收益": ["投资收益"], "财务费用": ["财务费用"], "营业利润": ["营业利润"], "营业外收入": ["营业外收入"], "营业外支出": ["营业外支出"], "所得税费用": ["所得税费用"], "归属母公司所有者的净利润": ["归属母公司所有者的净利润"], "少数股东损益": ["少数股东损益"], "利润总额": ["利润总额", '利润总额（亏损以"-"号表示）'], "净利润": ["净利润", '净利润（亏损以"-"号表示）'], "利息支出": ["利息支出"], "每股收益": ["每股收益"], "利息费用": ["利息费用"]},
            "consolidated_cash_flow": {"销售商品、提供劳务收到的现金": ["销售商品、提供劳务收到的现金"], "收到的税费返还": ["收到的税费返还"], "收到其他与经营活动有关的现金": ["收到其他与经营活动有关的现金"], "经营活动现金流入小计": ["经营活动现金流入小计"], "购买商品、接受劳务支付的现金": ["购买商品、接受劳务支付的现金"], "支付给职工以及为职工支付的现金": ["支付给职工以及为职工支付的现金"], "支付的各项税费": ["支付的各项税费"], "支付其他与经营活动有关的现金": ["支付其他与经营活动有关的现金"], "经营活动现金流出小计": ["经营活动现金流出小计"], "经营活动产生的现金流量净额": ["经营活动产生的现金流量净额"], "收回投资收到的现金": ["收回投资收到的现金"], "取得投资收益收到的现金": ["取得投资收益收到的现金"], "处置固定资产、无形资产和其他长期资产收回的现金净额": ["处置固定资产、无形资产和其他长期资产收回的现金净额"], "处置子公司及其他营业单位收到的现金净额": ["处置子公司及其他营业单位收到的现金净额"], "收到其他与投资活动有关的现金": ["收到其他与投资活动有关的现金"], "投资活动现金流入小计": ["投资活动现金流入小计"], "购建固定资产、无形资产和其他长期资产支付的现金": ["购建固定资产、无形资产和其他长期资产支付的现金", "购建固定资产、无形资产和其他长期资产所支付的现金"], "投资支付的现金": ["投资支付的现金"], "取得子公司及其他营业单位支付的现金净额": ["取得子公司及其他营业单位支付的现金净额"], "支付其他与投资活动有关的现金": ["支付其他与投资活动有关的现金"], "投资活动现金流出小计": ["投资活动现金流出小计"], "投资活动产生的现金流量净额": ["投资活动产生的现金流量净额"], "吸收投资收到的现金": ["吸收投资收到的现金"], "取得借款收到的现金": ["取得借款收到的现金"], "收到其他与筹资活动有关的现金": ["收到其他与筹资活动有关的现金"], "筹资活动现金流入小计": ["筹资活动现金流入小计"], "偿还债务支付的现金": ["偿还债务支付的现金"], "分配股利、利润或偿付利息支付的现金": ["分配股利、利润或偿付利息支付的现金"], "支付其他与筹资活动有关的现金": ["支付其他与筹资活动有关的现金"], "筹资活动现金流出小计": ["筹资活动现金流出小计"], "筹资活动产生的现金流量净额": ["筹资活动产生的现金流量净额"], "汇率变动对现金及现金等价物的影响": ["汇率变动对现金及现金等价物的影响"], "现金及现金等价物净增加额": ["现金及现金等价物净增加额"], "期初现金及现金等价物余额": ["期初现金及现金等价物余额"], "期末现金及现金等价物余额": ["期末现金及现金等价物余额"]}
        }
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
            table_indicators = await self.request_table_indicators(table_name_mapping[k], url_table_indicator)
            for item in table_indicators:
                table_indicators_mapping[k][item['indicatorName']] = get_alias(item)

        
        for k, v in table_indicators_expand.items():
            if k not in table_indicators_mapping:
                continue
            for name in v:
                if name not in table_indicators_mapping[k]:
                    continue
                table_indicators_mapping[k][name] = list(set(table_indicators_mapping[k][name]) & set(v[name]))
        return table_indicators_mapping

    @staticmethod
    def get_table_indicator(indicator_name, table_indicators_mapping):
        indicator_table = {}
        for table_name, indicators in table_indicators_mapping.items():
            for k, v in indicators.items():
                for alias in v:
                    indicator_table[alias] = table_name
        return indicator_table.get(indicator_name)
    
    async def request_table_indicators(self, table_ch_name, url_table_indicator):
        """请求按表查询指标接口"""
        try:
            inputs = {
                "sourceType": table_ch_name
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                response = await client.get(url_table_indicator, params=inputs)
                table_indicators = response.json().get("data")
                return table_indicators
        except Exception as e:
            self.logger.exception(f'按表查询指标接口报错：{e}')
            table_indicators = []
        return table_indicators

    async def request_mysql(self, url, table_name, company_short_name, company_full_name, year, period_type):
        try:
            if isinstance(self.config.knowledge_base_name, str):
                knowledge_base_name = int(self.config.knowledge_base_name)
            elif isinstance(self.config.knowledge_base_name, List) and self.config.knowledge_base_name:
                knowledge_base_name = int(self.config.knowledge_base_name[0])
            else:
                knowledge_base_name = ""
            if isinstance(self.config.kb_file_list.get(str(knowledge_base_name)), List):
                file_id = list(map(lambda x: int(x), self.config.kb_file_list.get(str(knowledge_base_name))))
            else:
                self.logger.info('request_mysql file_id: {}'.format(str(self.config.kb_file_list)))
                file_id = []
            data = {
                "knowledge_base_id": knowledge_base_name,
                "company_short_name": company_short_name,
                "file_id": file_id,
                "table_name": table_name,
                "year": year,
                "period_type": period_type
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                response = await client.post(url, json=data, headers={"Content-Type": "application/json"})
                indicators = response.json().get('results', [])
            if not indicators:
                data = {
                    "knowledge_base_id": knowledge_base_name,
                    "company_full_name": company_full_name,
                    "file_id": file_id,
                    "table_name": table_name,
                    "year": year,
                    "period_type": period_type
                }
                async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                    response = await client.post(url, json=data, headers={"Content-Type": "application/json"})
                    indicators = response.json().get('results', [])
            if not indicators and company_full_name:
                data = {
                    "knowledge_base_id": knowledge_base_name,
                    "company_short_name": company_full_name,
                    "file_id": file_id,
                    "table_name": table_name,
                    "year": year,
                    "period_type": period_type
                }
                async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                    response = await client.post(url, json=data, headers={"Content-Type": "application/json"})
                    indicators = response.json()['results']
            if not indicators and company_short_name:
                data = {
                    "knowledge_base_id": knowledge_base_name,
                    "company_full_name": company_short_name,
                    "file_id": file_id,
                    "table_name": table_name,
                    "year": year,
                    "period_type": period_type
                }
                async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                    response = await client.post(url, json=data, headers={"Content-Type": "application/json"})
                    indicators = response.json().get('results', [])
        except Exception:
            msg = traceback.format_exc().replace('\n', '\t')
            self.logger.error('request_mysql error: {}'.format(msg))
            indicators = []
        return indicators
    
    @staticmethod
    def _transform(x, data, check_year):
        date_type_mapping = {"期初": 0, "期末": 1}
        if x not in data:
            return ""
        if x == "年份" and data.get(x) in check_year:
            return data.get(x)
        if x == "周期类型" and data.get(x) in check_year:
            return data.get(x)
        if x == "公司简称" or x == "公司全称" or x == "财务指标":
            return data.get(x)
        if x == "日期类型" and data.get(x) in check_year:
            return date_type_mapping[data.get(x)]
        return ""
    
    async def extract_company_info(self, query):
        check_period = {"一季度", "二季度", "三季度", "四季度", "年度", "期初", "期末"}
        check_year = set(list(map(lambda x: str(x), range(1900,2100))))
        check_year = check_period | check_year
        company_info = {"company_full_name": "", "company_short_name": "", "year": "", "period_type": "", "indicator_name": "", "date_type": ""}
        company_info_mapping = {"公司简称": "company_short_name", "公司全称": "company_full_name", "年份": "year", "周期类型": "period_type", "日期类型": "date_type", "财务指标": "indicator_name"}
        _prompt = """<|im_start|>system\nYou are a helpful assistant. 你是一个信息抽取助手<|im_end|>\n<|im_start|>user\n基于用户问题抽取信息。\n约束条件：\n1.输出json形式如：```json\n{\"公司全称\": \"\", \"公司简称\": \"\", \"年份\": \"\", \"周期类型\": \"\", \"财务指标\": \"\", \"日期类型\": \"\"}```;\n2.其中周期类型仅识别为“一季度、二季度、三季度、四季度、年度”中的一种，不在其中则为空字符;\n3.其中日期类型仅识别为“期初、期末”中的一种，不在其中可默认为期末.\n\n###用户问题："""
        _prompt_tail = "\n/no_think<|im_end|>\n<|im_start|>assistant\n"
        _prompt += query + _prompt_tail
        generation_params = {
            "temperature": 0.2,
            "max_tokens": 1000
        }
        response = await self.client.completions(
            prompt=_prompt,
            generation_params=generation_params
        )
        pattern = r"```json\s*([\s\S]*?)\s*```"
        matches = re.findall(pattern, response)
        if matches:
            data = json.loads(matches[0])
            for k,v in company_info_mapping.items():
                company_info[v] = self._transform(k, data, check_year)
        return company_info
    
    async def retrieve_query(self, url, query, query_list, query_indicators, url_table_indicator):

        company_short_name: str = ""
        company_full_name: str = ""
        year: str = ""
        period_type: str = ""
        indicator_name: str = ""
        date_type: int = None
        table_indicators_mapping = await self.get_table_indicators(url_table_indicator)
        indicators_final = []
        _flag = False
        # [直接的指标查询优先]
        for item in query_indicators:
            indicator_name = item.get("indicator_name")
            company_full_name = item.get("company_full_name")
            company_short_name = item.get("company_short_name")
            year = item.get("year")
            period_type = item.get("period_type")
            date_type = item.get("date_type")
            if not indicator_name:
                continue
            table_name = self.get_table_indicator(indicator_name, table_indicators_mapping)
            indicators = await self.request_mysql(url, table_name, company_short_name, company_full_name, year, period_type)
            for item in indicators:
                if indicator_name == item["indicator_name"] or indicator_name == item["indicator_raw"] or indicator_name in table_indicators_mapping.get(table_name, {}).get(item["indicator_name"], []):
                    if item['status'] == 1 and item['date_type'] == date_type:
                        indicators_final.append(item)
                        _flag = True
        if _flag:
            return _flag, indicators_final
        # [query+query_list查询]
        query_list.append(query)
        for q in query_list:
            company_info = await self.extract_company_info(q)
            company_short_name = company_info["company_short_name"]
            company_full_name = company_info["company_full_name"]
            year = company_info["year"]
            period_type = company_info["period_type"] if company_info["period_type"] else '年度'
            date_type = company_info["date_type"]
            indicator_name = company_info["indicator_name"]
            table_name = self.get_table_indicator(indicator_name, table_indicators_mapping)
            indicators = await self.request_mysql(url, table_name, company_short_name, company_full_name, year, period_type)
            for item in indicators:
                if indicator_name == item["indicator_name"] or indicator_name == item["indicator_raw"] or indicator_name in table_indicators_mapping.get(table_name, {}).get(item["indicator_name"], []):
                    if item['status'] == 1 and item['date_type'] == date_type:
                        indicators_final.append(item)
                        _flag = True
        if _flag:
            return _flag, indicators_final
        return False, []