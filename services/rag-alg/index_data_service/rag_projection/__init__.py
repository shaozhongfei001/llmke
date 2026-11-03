"""RAG 投影（快照 → 召回单元）。实现见 projection.py。"""

from .projection import (  # noqa: F401
    MODE_ENV,
    MODES,
    PROJECTION_VERSION,
    ProjectionPolicy,
    ProjectionRefused,
    ProjectionResult,
    load_artifact,
    mode_from_env,
    project,
)
