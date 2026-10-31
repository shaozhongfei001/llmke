"""图引擎适配层（当前目标：HippoRAG）。身份与来源映射见 mapping.py。"""

from .assertions import (DENSE_FALLBACK, GRAPH, Assertion, AssertionStore, SourceRef,
                         decide_route)  # noqa: F401
from .capabilities import describe  # noqa: F401
from .mapping import (SCHEMA, InputUnit, SourceMap, input_unit_id, native_key,
                      units_from_chunks)  # noqa: F401
