from io import BytesIO
from typing import Iterator

import PIL
import numpy as np
from PIL import Image
from langchain_core.document_loaders import Blob

from log import logger
from server.nacos_utils import DocParseConfig
from server.utils import load_local_ocr
from .base_parser import BaseParser
from .mineru_parser import MinerUParser
from .text_in_parser import TextInParser
from ..output_object import ParsedText, ParsedTextMetadata
from ..vision import Recognizer


class _BaseParser(BaseParser):
    def __init__(self):
        self.ocr = load_local_ocr()['ocr']
        self.size: tuple[int, int] | None = None
        self.zoomin = 3

    def lazy_parse(self, blob: Blob) -> Iterator[ParsedText]:
        return self.__call__(blob)

    def get_ocr_boxes(self, file: Blob):
        image = Image.open(BytesIO(file.as_bytes()))
        # image.mode为"p",image.size = [height, weight]
        # image.mode为"RGB", image.size = [height, weight, 3]
        if image.mode != "RGB":
            image = image.convert("RGB")

        image_array = np.array(image)
        # TODO 处理RGBA图片 暂时忽略掉Alpha通道
        if len(image_array.shape) != 3:
            raise ValueError('不合法的图片，图片应为一个三阶张量。')
        else:
            # 如果最后一个维度大于3 则说明不是RGB图片 很有可能是RGBA
            if image_array.shape[-1] > 3:
                image_array = image_array[:, :, 0:3]

        self.size = list(image.size)

        boxes = self.ocr.detect(image_array)

        if not boxes:
            return []

        boxes = [(line[0], line[1][0]) for line in boxes]
        boxes = Recognizer.sort_Y_firstly(
            [
                {
                    'x0': box[0][0] / self.zoomin,
                    'x1': box[1][0] / self.zoomin,
                    'top': box[0][1] / self.zoomin,
                    'text': '',
                    'txt': t,
                    'bottom': box[-1][1] / self.zoomin
                } for box, t in boxes if box[0][0] <= box[1][0] and box[0][1] <= box[-1][1]
            ],
            0
        )

        for box in boxes:
            if not box['text']:
                left = box['x0'] * self.zoomin
                right = box['x1'] * self.zoomin
                top = box['top'] * self.zoomin
                bott = box['bottom'] * self.zoomin
                box['text'] = self.ocr.recognize(
                    image_array,
                    np.array([[left, top], [right, top], [right, bott], [left, bott]], dtype=np.float32)
                )
            yield box

        return None

    def __call__(self, file: Blob) -> Iterator[ParsedText]:
        doc_parse_config = DocParseConfig().config
        if doc_parse_config['use_text_in']:
            text_in_parser = TextInParser(polling_time=0.5)
            # TODO 应该使用return text_in_parser.lazy_parse(file)
            #  不知道为什么会无法返回结果
            yield from text_in_parser.parse(file)
        elif doc_parse_config['use-mineru']:
            mineru_parser = MinerUParser()
            yield from mineru_parser.parse(file)
        else:
            for box in filter(lambda x: x['text'], self.get_ocr_boxes(file)):
                yield ParsedText(
                    page_content=box['text'],
                    metadata=ParsedTextMetadata(
                        source=file.source,
                        file_path=file.path,
                        position=[[
                            [box['x0'], box['top']],
                            [box['x1'], box['top']],
                            [box['x1'], box['bottom']],
                            [box['x0'], box['bottom']]
                        ]],
                        page_number=[1],
                        page_size=[list(self.size)]
                    )
                )


class Parser:
    @staticmethod
    def get_parser() -> _BaseParser:
        return _BaseParser()

    @staticmethod
    def is_image(blob: Blob) -> bool:
        try:
            Image.open(BytesIO(blob.as_bytes()))
            return True
        except PIL.UnidentifiedImageError as e:
            logger.info(f'不是图片：{e}')
            return False

    @staticmethod
    def get_image_size(file: Blob):
        image = Image.open(BytesIO(file.as_bytes()))
        return list(image.size)
