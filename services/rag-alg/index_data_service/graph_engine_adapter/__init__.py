"""图引擎适配层（当前目标：HippoRAG）。身份与来源映射见 mapping.py。"""

from .mapping import (SCHEMA, InputUnit, SourceMap, input_unit_id, native_key,
                      units_from_chunks)  # noqa: F401
