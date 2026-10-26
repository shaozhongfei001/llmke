from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator, field_validator


class ParsedTextMetadata(BaseModel):
    source: str | None = Field(default=None, description='传入文档的minio路径')
    file_path: str | None = Field(default=None, description='传入文档的minio路径')
    document_id: str | None = Field(default=None, description='文档id')
    file_id: int | None = Field(default=None, description='传入的文件id')
    knowledge_base_name: str | None = Field(default=None, description='传入的知识库名称')
    file_size: str | None = Field(default=None, description='传入的文件大小')
    title: str | None = Field(default=None, description='文件名')
    type: Literal['text'] = Field(default='text', description='类型')
    position: list[list[list[int | float]]] = Field(
        default=[],
        description='content对应文本框四个顶点的坐标位置，可能包括多个位置（跨页）',
        examples=[
            [
                [[0, 0], [1, 0], [1, 1], [0, 1]],
                [[0, 0], [1, 0], [1, 1], [0, 1]]
            ]
        ]
    )
    page_number: list[int] = Field(default=[], description='所在页码（如果有的话）')
    page_size: list[list[int | float]] = Field(default=[], description='所在页的尺寸（如果有的话）')
    offset: list[list[int]] = Field(default=[], description='对应原文的字符串角标范围')
    revise_date: str | None = Field(default=None, description='修订日期')
    parent_file_name: str | None = Field(default=None, description='传入的父文件名称')
    version: str | None = Field(default=None, description='文件版本号（V0/V1…），检索按当前有效版本去重')
    pk: int | None = Field(default=None, description='存到索引数据库中的主键')
    pic_url_list: list[str] = Field(default=[], description='关联图片的minio路径')
    pic_offset_list: list[int] = Field(default=[], description='关联图片的坐标和pic_url_list一一对应')
    pic_children_id_list: list[int] = Field(default=[], description='关联图片在索引数据库中的主键')
    need_filtered: bool = Field(default=False, description='是否是页脚页眉侧边栏等需要过滤掉的')
    title_path: str = Field(default='', description='当前chunk的章节目录')
    chunk_index: int = Field(default=-1, description='当前chunk的顺序')
    labels: list[str] = Field(default=[], description='用户自定义文件标签')
    folder_id: int | None = Field(default=None, description='文件夹id')
    parsed_chunk_index: int = Field(default=0, description='切分后保留的chunk_index')
    base64: str | None = Field(default="", description='图片文件的base64编码')

    @model_validator(mode='after')
    def model_validate(self):
        if not self.title and self.file_path:
            self.title = Path(self.file_path).name

        return self


class ParsedText(BaseModel):
    page_content: str = Field(default='', description='块对应的纯文本内容')
    metadata: ParsedTextMetadata = Field(default=ParsedTextMetadata(), description='用于补充描述的元数据')

    @field_validator('page_content')
    @classmethod
    def validate_page_content(cls, page_content: str):
        return page_content.strip()
