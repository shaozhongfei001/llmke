from abc import ABC, abstractmethod
from typing import Callable, Optional

from deepdoc.output_object import ParsedText
from server.api_param import ModelInfo
from pydantic import Field

class BaseSplitter(ABC):
    def __init__(
            self,
            chunk_size: int = 500,
            chunk_overlap: int = 20,
            separators: list[str] = None,
            split_regex: list[str] = None,
            length_function: Callable[[str], int] = len,
            user_id: str = "",
            knowledge_base_id: Optional[int] = None,
            model_info: ModelInfo = Field(description='llm配置'),
            embedding_model_info: ModelInfo = Field(description='embedding模型配置'),
            multi_model_info: ModelInfo = Field(description='多模态模型配置')
    ):
        # if not split_regex:
        #     split_regex = ['(?<=[。？！?!])', '(?<=[，,])']

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.split_regex = split_regex
        self.separators = ['。', '？', '！', '，']
        self.length_function = length_function
        self.user_id = user_id
        self.knowledge_base_id = knowledge_base_id
        self.model_info = model_info
        self.embedding_model_info = embedding_model_info
        self.multi_model_info = multi_model_info

    @abstractmethod
    def chunk(
            self,
            documents: list[ParsedText], *args, **kwargs
    ) -> list[ParsedText]:
        pass
