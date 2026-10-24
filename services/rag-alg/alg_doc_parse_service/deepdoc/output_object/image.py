from typing import Literal

from pydantic import Field

from deepdoc.output_object.text import ParsedText, ParsedTextMetadata


class ParsedImageMetadata(ParsedTextMetadata):
    base64: str | None = Field(default=None, description='图片文件的base64编码')
    type: Literal['image'] = Field(default='image', description='类型')
    ext: str = Field(default='jpg', description='图片的编码格式')
    text_parent_id_list: list[int] = Field(default=[], description='和图片关联的文本在索引数据库的主键')
    image_path: str = Field(default='', description='图片对应的minio路径')
    image_size: list[int | float] = Field(default=[], description='图片大小')
    boxes: list[list[list[int | float]]] = Field(default=[], description='图片中多个文字框的位置')
    is_parsed: bool = Field(default=False, description='图片是否已经被解析')
    caption_nearby: Literal['previous', 'next'] | None = Field(default=None, description='上一个或者下一个是否是caption')
    # [R12-FIX-PARSE-02] 分开存 OCR 文本与 VLM 描述。
    # 原因：原实现用 VLM 输出直接覆盖 page_content，会丢掉 parser（OCR）已经抽到的文字；
    # 而 VLM 在多图/二次处理场景下会退化甚至虚构，不能作为唯一文本源。
    ocr_text: str | None = Field(default=None, description='该图 OCR 得到的文字（parser 产出，基线文本）')
    vlm_text: str | None = Field(default=None, description='多模态模型的描述/转录（仅作补充，不覆盖 ocr_text）')
    vlm_status: Literal['ok', 'failed', 'unavailable', 'over_budget', 'kv_starved', 'timeout', 'skipped'] | None = Field(
        default=None,
        description='多模态处理结果分档：ok/failed/unavailable(端点未运行)/over_budget(超ctx)/kv_starved(KV不足)/timeout/skipped(不需要VLM)'
    )


class ParsedImage(ParsedText):
    metadata: ParsedImageMetadata = Field(default=ParsedImageMetadata(), description='用于补充描述的元数据')
