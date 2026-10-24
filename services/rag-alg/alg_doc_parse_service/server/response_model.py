import os

from pydantic import BaseModel, Field, model_validator


class BaseResponse(BaseModel):
    success: bool = Field(description='是否成功', default=False)
    msg: str | None = Field(description='状态信息', default=None)

    @model_validator(mode='after')
    def model_validate(self):
        if not self.success:
            self.msg = (self.msg + f' LOG_ID: {os.getpid()}') if self.msg is not None else f'LOG_ID: {os.getpid()}'

        return self

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "msg": "成功"
                },
                {
                    "success": False,
                    "msg": "失败"
                }
            ]
        }


class TaskResult(BaseModel):
    file_path: str = Field(description='文件的minio路径')
    file_id: int = Field(description='文件id')
    success: bool = Field(description='是否成功')
    fail_reason: str | None = Field(description='失败原因', default=None)
    revise_date: str | None = Field(description='文件对应的修订时间', default=None)
    code: int | None = Field(description='解析任务状态码', default=200)


class ParseResponse(BaseResponse):
    task_id: int | None = Field(description='异步接口时用到的任务ID', default=None)
    task_statuses: list[TaskResult] = Field(description='任务状态', default=[])

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "msg": None,
                    "task_statuses": None
                },
                {
                    "success": False,
                    "msg": "failed",
                    "task_statuses": [
                        {
                            "file_path": "abc/test.pdf",
                            'success': False,
                            'fail_reason': "no such file",
                            'code': 1100
                        },
                        {
                            "file_path": "abc/test2.pdf",
                            'success': True,
                            'fail_reason': None,
                            'code': 200
                        }
                    ]
                }
            ]
        }


class Box(BaseModel):
    x0: float | None = Field(description='文本框的左边位置', default=None)
    x1: float | None = Field(description='文本框的右边位置', default=None)
    top: float | None = Field(description='文本框的上边位置', default=None)
    bottom: float | None = Field(description='文本框的下边位置', default=None)
    text: str | None = Field(description='文本框内识别的文字', default=None)


class OCRResponse(BaseResponse):
    boxes: list[Box] = Field(description='文字框列表', default=[])

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "msg": None,
                    "boxes": [
                        {
                            "x0": 9.1,
                            "x1": 119.0,
                            "top": 19.666,
                            "bottom": 34.5622,
                            "text": "文字"
                        },
                        {
                            "x0": 9.1,
                            "x1": 119.0,
                            "top": 35.666,
                            "bottom": 48.5622,
                            "text": "文字2"
                        }
                    ]
                },
                {
                    "success": False,
                    "msg": "failed",
                    "boxes": []
                }
            ]
        }


class MultiVersionResponse(BaseResponse):
    data: list[dict] = []

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "msg": None,
                    "data": [
                        {
                            "id": "ID1234",
                            "name": "file name",
                            "group_id": "GroupId1234"
                        },
                        {
                            "id": "ID1345",
                            "name": "file name",
                            "group_id": "GroupId1234"
                        }
                    ]
                },
                {
                    "success": False,
                    "msg": "failed",
                    "data": []
                }
            ]
        }

class DataBaseDescResponse(BaseResponse):
    table_description: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "msg": None,
                    "table_description": "表描述内容"}
            ]
        }

class IndicatorGroupbyResponse(BaseResponse):
    success: bool
    request_id: str
    msg: str
    results: list[dict]

    class Config:
        json_schema_extra = {
            "examples": [
            ]
        }


class IndicatorResponse(BaseResponse):
    success: bool
    results: list
    request_id: str
    msg: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "msg": "",
                    "results": [{
                        "id": 1,
                        "company_full_name": "芜湖三江高频焊管有限公司",
                        "company_short_name": "三江高频",
                        "year": "2024",
                        "period_type": "年度",
                        "date_type": 0,
                        "indicator_name": "货币资金",
                        "indicator_raw": "货币资金",
                        "indicator_value": "3629238.92",
                        "fixed_value": None,
                        "indicator_unit": "元",
                        "indicator_value_position": None,
                        "indicator_value_page_size": None,
                        "indicator_value_offset": None,
                        "indicator_value_page_number": None,
                        "parsed_file_path": None,
                        "file_name": None,
                        "file_path": "dev-rag-data/intelbrain-dw/1000/hs-三江高频/三江高频2024.12资产负债表.xls/V0/三江高频2024.12资产负债表.xls",
                        "file_id": 84905,
                        "knowledge_base_name": "hs-三江高频",
                        "knowledge_base_id": 2505,
                        "status": 1,
                        "adopt": None,
                        "table_name": "consolidated_balance"
                    }],
                    "request_id": "4417a102-b5bc-3494-9fbc-a9b813f954d2"
                },
                {
                    "success": False,
                    "msg": "failed",
                    "results": [],
                    "request_id": "4417a102-b5bc-3494-9fbc-a9b813f954d2"
                }
            ]
        }

class IndicatorGroupbyResponse(BaseResponse):
    success: bool
    request_id: str
    msg: str
    results: list[dict]
    class Config:
        json_schema_extra = {
            "examples": [
            ]
        }