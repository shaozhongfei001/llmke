"""
规则版本识别
算法版本识别
"""
import re

from server.nacos_utils import DocParseConfig

from deepdoc.utils import llm_chat

DocParse = DocParseConfig()
server_config = DocParse.config


class DatabaseDesc:

    def __init__(self, database_desc_params):
        self.database_id = database_desc_params.database_id
        self.database_name = database_desc_params.database_name
        self.database_description = database_desc_params.database_description
        self.physical_name = database_desc_params.physical_name
        self.business_name = database_desc_params.business_name
        self.description = database_desc_params.description
        self.column_count = database_desc_params.column_count
        self.row_count = database_desc_params.row_count
        self.columns = database_desc_params.columns
        self.model_info = database_desc_params.model_info
        self.success = True

    def data_base_desc_build(self):
        sys_prompt, desc_prompt = self.build_desc_prompt()
        summary = self.get_database_desc(sys_prompt, desc_prompt)
        return summary

    def build_desc_prompt(self):
        """
        构建生成描述的prompt
        """
        sys_prompt = "你是一个语言学家，请严格按照用户的需求回答问题"
        columns_prompt = ""
        for column in self.columns:
            description =  column.get("description") if column.get("description", "") else ""
            columns_prompt = columns_prompt + f'''
                       字段英文名称: {column["physical_name"]}
                       字段中文名称: {column["business_name"]}
                       类型名称: {column["data_type"]}
                       字段描述: {description}
                       样例数据: {column["sample_values"]}
                       '''

        desc_prompt = f'''请基于以下提供的数据库与数据表相关信息，总结出该数据表的描述信息。总结时需满足以下要求：语言务必简洁凝练，描述内容务必严格控制在150字符以内，同时确保完整涵盖关键信息，不得遗漏核心内容，表描述采用自然语言描述。
需参考的信息如下：
1.数据库名称：{self.database_name}
2.数据库描述：{self.database_description}
3.数据表英文名称：{self.physical_name}
4.数据表中文名称：{self.business_name}
5.数据表描述：{self.description}
6.数据表字段详情：{columns_prompt}
请仅围绕上述信息进行总结，避免添加无关内容，最终呈现的数据表描述需清晰体现数据表在对应数据库中的定位、核心功能及关键字段特征。
以下为参考模板，可以不严格按照参考模板内容输出描述内容，但需要严格按照参考模板格式输出描述内容：
（表格名称或简称）表格主要展示了（场景名称）场景的数据，包含（主要字段可以写一个或多个，用顿号分隔）等主要字段，支持用户查询(介绍需要查询的方向)问题。
           '''

        if self.column_count > 0:
            desc_prompt =  desc_prompt + f'''字段数量: {self.column_count}'''

        if self.row_count > 0:
            desc_prompt =  desc_prompt + f'''数据量: {self.row_count}'''
        return sys_prompt, desc_prompt

    def get_database_desc(self, sys_prompt, desc_prompt):
        summary = llm_chat(sys_prompt=sys_prompt, user_prompt=desc_prompt, model_info=self.model_info)
        summary = re.sub("<think>.*</think>", "", summary, flags=re.S).strip()
        return summary


if __name__ == "__main__":
    pass

