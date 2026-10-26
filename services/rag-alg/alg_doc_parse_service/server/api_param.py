from typing import Literal

from fastapi import UploadFile, File
from pydantic import BaseModel, Field, field_validator, model_validator

from .nacos_utils import DocParseConfig


class FileParams(BaseModel):
    file_path: str = Field(description='文件的minIO路径', examples=['dev-rag-data/测试/测试.pdf'])
    file_id: int = Field(description='文件id', examples=[3421, 353333])
    file_size: str = Field(description='文件大小，以MB为单位', examples=['10'], default=None)
    parent_file_name: str = Field(description='父文件名称', default=None)
    version: str = Field(description='文件版本号(V0/V1...)', default=None)
    labels: list[str] = Field(default=[], description='用户自定义文件标签')
    folder_id: int | None = Field(default=None, description='文件夹id')


class ModelInfo(BaseModel):
    model_id: str = Field(description='openai api中的model')
    url: str = Field(description='模型的url', examples=['http://ip:port/v1/chat/completions'])
    key: str | None = Field(description='openai api key', default=None)


class ParseParams(BaseModel):
    knowledge_base_name: str = Field(description='知识库名称', examples=['samples'])
    knowledge_base_id: int | None = Field(description='知识库id', examples=['49288294'], default=None)
    user_id: str | None = Field(description='用户id', examples=['abc123'], default=None)
    files: list[FileParams] = Field(description='待解析的文件', default=[], examples=[
        FileParams(
            file_path='dev-rag-data/测试/测试.pdf',
            file_id=3421
        )
    ])
    file_type: str = Field('naive', description='文档类型，目前支持三种类型，详见examples。',
                           examples=['naive', 'laws', 'book'])
    chunk_size: int = Field(DocParseConfig().config['chunk_size'], description='知识库中单段文本最大长度')
    chunk_overlap: int = Field(DocParseConfig().config['overlap_size'], description='知识库中相邻文本重合长度')
    length_function: Literal['char', 'token'] | None = Field(
        description='长度计算方式：char、token。前者按照字符计算长度，后者按照token。',
        default='char'
    )
    split_regex: list[str] = Field(description='切分正则表达式列表，优先级从高到低。', default=[])
    save_txt: bool = Field(description='是否将解析结果的文字全文保存到minio的txt文件中', default=False)
    need_chunk: bool = Field(description='是否需要进行切分和索引', default=True)
    index_name: str = Field(description='milvus和es要用到的建表名称', default='')
    model_info: ModelInfo = Field(description='llm配置')
    embedding_model_info: ModelInfo = Field(description='embedding模型配置')
    multi_model_info: ModelInfo = Field(description='多模态模型配置')
    task_id: int | None = Field(description='异步接口时需要的任务ID', default=None)

    @model_validator(mode='after')
    def model_validate(self):
        if not self.index_name:
            self.index_name = str(self.knowledge_base_id)

        if self.knowledge_base_id and not self.user_id:
            raise ValueError('传入knowledge_base_id的时候必须使用user_id')

        if self.chunk_size < 1:
            raise ValueError('chunk_size必须大于等于1')

        if self.chunk_overlap < 0:
            raise ValueError('chunk_overlap必须大于0')

        return self


class ReviseDateParams(ParseParams):
    @field_validator('knowledge_base_id')
    @classmethod
    def validate_messages(cls, knowledge_base_id):
        """
        强制将这个参数设置为None，因为loader会根据他来决定是否将解析结果保存到minio中。
        由于本model是用于获取修订日期的接口，因此不需要将解析结果保存到minio中。
        """
        return


class OCRParams(BaseModel):
    image_path: str = Field(description='文件的minIO路径')


class UploadParams(BaseModel):
    file: UploadFile = File()


class FileVersionParams(BaseModel):
    knowledge_base_name: str  # 知识库名字，根据内容进行版本计算的时候使用
    need_version_doc: list[dict] = []  #
    have_version_doc: list[dict] = []
    status: str  # 调用时, 0表示只根据文件名进行处理，1表示根据文件名+文件内容
    ori_file_n_chunk: int = 4
    recall_file_top_n_chunk: int = 4
    score_threshold: float = 120
    max_score_threshold: float = 0.75
    model_info: ModelInfo = Field(description='llm配置')


class IndicatorQueryParams(BaseModel):
    knowledge_base_name: str = Field(default=None, description='知识库名称', examples=['samples'])  # 知识库名称
    knowledge_base_id: int | None = Field(default=None, description='知识库ID', examples=['samples'])  # 知识库ID
    file_id: list[int] | None = Field(default=None, description='文件id')  # 文件id
    company_short_name: str = Field(default=None, description='公司简称')  # 公司简称
    company_full_name: str | None = Field(default=None, description='公司全称')  # 公司全称
    year: str | None = Field(default=None, description='年报年份', examples=['2023'])  # 年报年份，如："2023"
    period_type: str | None = Field(default=None, description='周期类型',
                                    examples=['年报', '一季度', '二季度', '三季度',
                                              '四季度'])  # 周期类型：年报、一季度、二季度、三季度、四季度
    table_name: str | None = Field(default=None, description='表名，为空则默认取所有表。',
                                   examples=['consolidated_balance', 'consolidated_balance',
                                             'consolidated_cash_flow'])  # 表名（consolidated_balance、consolidated_income、consolidated_cash_flow）


class IndicatorGroupbyParams(BaseModel):
    knowledge_base_id: int = Field(description='知识库id', examples=[1])  # 知识库id
    file_id: list[int] | None = Field(default=None, description='文件id', examples=[[1, 2, 3]])  # 文件id


class IndicatorModifyParams(BaseModel):
    modified_by: str = Field(description='修改用户id')
    table_names: list[str] = Field(description='表名列表',
                                   examples=['consolidated_balance', 'consolidated_balance', 'consolidated_cash_flow'])
    ref_ids: list[int] = Field(description='主键id', examples=[[1, 2, 3]])  # 主键id
    fixed_value: str | None = Field(default=None, description='修改后指标值', examples=['123.45'])
    adopt_index: int | None = Field(default=None, description='采用ref_ids中的index', examples=[0])

class IndicatorAddParams(BaseModel):
    knowledge_base_id: int = Field(description='知识库id')
    knowledge_base_name: str | None = Field(description="知识库名称")
    table_name: str = Field(description="表名")
    company_short_name: str | None = Field(description="公司简称")
    company_full_name: str = Field(description="公司全称")
    year: str | None = Field(description="年报年份")
    period_type: str | None = Field(default=None, description='周期类型', examples=['年报', '一季度', '二季度', '三季度', '四季度'])
    date_type: int | None = Field(description="日期类型", examples=[0, 1])
    indicator_name: str | None = Field(description="标准财务指标名称")
    fixed_value: str = Field(description="更新指标值")
    indicator_unit: str = Field(description="指标单位")
    creator_id: str | None = Field(description="创建人")
    indicator_raw: str | None = Field(description="原文财务指标名称")
    file_path: str | None = Field(default=None, description='原始文件的存储路径')






class DatabaseDescConfig(BaseModel):
    database_id: int = Field(description='数据库编号', examples=[1])
    database_name: str | None = Field(default=None, description='数据库名称')
    database_description: str | None = Field(default=None, description='数据库描述')
    physical_name: str | None = Field(default=None, description='数据表名称（英文）')
    business_name: str | None = Field(default=None, description='数据表业务名称（中文）')
    description: str | None = Field(default=None, description='数据表描述')
    column_count: int | None = Field(default=0, description='字段数量')
    row_count: int | None = Field(default=0, description='数据量')
    model_info: ModelInfo = Field(description='llm配置')
    columns: list[dict] = Field(description='数据表字段详情', examples=["table_name 表名","name 字段名称","type 类型","type_name 类型转化后名称","description 字段描述","sample_values 示例数据"])
