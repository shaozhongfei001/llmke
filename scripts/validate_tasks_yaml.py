#!/usr/bin/env python3
"""校验 docs/v2-tasks/TASKS.yaml：重复键 + 任务 id 唯一。

PyYAML 默认静默覆盖重复键（T-A7 的 artifacts 曾被 T-A1 产物覆盖而无人发现）。
这里用自定义 Loader 在构造 mapping 时检查重复键。
"""
import sys
from pathlib import Path

import yaml


class DuplicateKeyError(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def main() -> int:
    path = Path(__file__).resolve().parents[1] / "docs/v2-tasks/TASKS.yaml"
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=StrictLoader)
    tasks = data["tasks"] if isinstance(data, dict) and "tasks" in data else data
    ids = [t["id"] for t in tasks]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        print(f"FAIL duplicate task ids: {sorted(dup)}")
        return 1
    print(f"OK tasks={len(ids)} duplicate_keys=0 duplicate_ids=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
