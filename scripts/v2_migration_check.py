#!/usr/bin/env python3
"""在**隔离恢复副本**上验证 V2_0001 迁移：正向幂等、语义可用、回退对称。

只连 `--db` 指定的库，且库名必须包含 `restore`/`v2`（防呆：绝不在生产库跑 ALTER）。
口令从环境变量 `R12_MYSQL_PASSWORD` 读，不接受命令行明文，避免落进 shell history。

退出码：0 全通过；1 校验失败；2 环境/参数/依赖问题。
"""

import argparse
import json
import os
import re
import subprocess
import sys

MIGRATORS = ("V2_0001_parse_artifact.sql", "V2_0001_parse_artifact_rollback.sql")
COLUMNS = {
    "knowledge_base_list": ("content_uid", "parse_artifact_id", "artifact_generation"),
    "file_parse_task": ("content_uid", "parse_artifact_id", "artifact_generation"),
}
INDEXES = {"knowledge_base_list": ("idx_kbl_parse_artifact", "idx_kbl_content_uid"),
           "file_parse_task": ("idx_fpt_parse_artifact",)}


def _mysql(args, db, sql):
    cmd = ["mysql", f"-h{args.host}", f"-P{args.port}", f"-u{args.user}",
           f"-p{args.password}", "--batch", "--skip-column-names", "-e", sql]
    if db:
        cmd.append(db)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"mysql 失败: {proc.stderr.strip()[:300]}\nsql: {sql[:200]}")
    return proc.stdout.strip()


def _columns(args, db, table):
    out = _mysql(args, None, "SELECT column_name FROM information_schema.columns "
                             f"WHERE table_schema='{db}' AND table_name='{table}'")
    return set(x for x in out.split("\n") if x)


def _indexes(args, db, table):
    out = _mysql(args, None, "SELECT DISTINCT index_name FROM information_schema.statistics "
                             f"WHERE table_schema='{db}' AND table_name='{table}'")
    return set(x for x in out.split("\n") if x)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", default="13306")
    ap.add_argument("--user", default="root")
    ap.add_argument("--db", default="gienrag_v2_restore")
    ap.add_argument("--migrations", default="db/migrations")
    args = ap.parse_args(argv)
    args.password = os.environ.get("R12_MYSQL_PASSWORD") or ""
    if not args.password:
        print("R12_MYSQL_PASSWORD 未设置", file=sys.stderr)
        return 2
    if not re.search(r"(restore|v2)", args.db, re.I):
        print(f"refusing: --db={args.db} 看起来不是隔离副本（须含 restore/v2）", file=sys.stderr)
        return 2

    report = {"db": args.db, "steps": [], "status": "OK"}

    def fail(msg):
        report["status"] = "FAILED"
        report["error"] = msg
        return 1

    try:
        before = {t: len(_columns(args, args.db, t)) for t in COLUMNS}
        report["steps"].append({"step": "baseline_columns", "value": before})

        for _ in range(2):                      # 连跑两次验幂等
            subprocess.run(["mysql", f"-h{args.host}", f"-P{args.port}", f"-u{args.user}",
                            f"-p{args.password}", args.db, "-e",
                            f"source {os.path.join(args.migrations, MIGRATORS[0])}"],
                           capture_output=True, text=True, check=True)
        got = {t: _columns(args, args.db, t) for t in COLUMNS}
        missing = {t: [c for c in cols if c not in got[t]] for t, cols in COLUMNS.items()}
        if any(missing.values()):
            return fail(f"迁移后缺列: {missing}")
        report["steps"].append({"step": "apply_twice_idempotent",
                                "columns": {t: sorted(got[t]) for t in got}})

        idx = {t: _indexes(args, args.db, t) for t in INDEXES}
        missing_idx = {t: [i for i in cols if i not in idx[t]] for t, cols in INDEXES.items()}
        if any(missing_idx.values()):
            return fail(f"迁移后缺索引: {missing_idx}")
        report["steps"].append({"step": "indexes", "value": {t: sorted(idx[t]) for t in idx}})

        # 语义探针：用 LIKE 建影子表插一条，验证新列可写可查（不碰真实表数据）
        _mysql(args, args.db, "DROP TABLE IF EXISTS v2_probe_kbl")
        _mysql(args, args.db, "CREATE TABLE v2_probe_kbl LIKE knowledge_base_list")
        _mysql(args, args.db,
               "INSERT INTO v2_probe_kbl (kb_id, content_uid, parse_artifact_id, artifact_generation) "
               "VALUES (1, REPEAT('a', 64), "
               "'a846ab142d8d24afe3f552f95888c4b261dd7c8908921a16a2932c4a7838fa1d', 1)")
        probe = _mysql(args, args.db,
                       "SELECT artifact_generation FROM v2_probe_kbl WHERE parse_artifact_id LIKE 'a846ab%'")
        _mysql(args, args.db, "DROP TABLE v2_probe_kbl")
        if probe != "1":
            return fail(f"语义探针失败: {probe!r}")
        report["steps"].append({"step": "semantic_probe", "value": "ok"})

        for _ in range(2):                      # 回退也要幂等
            subprocess.run(["mysql", f"-h{args.host}", f"-P{args.port}", f"-u{args.user}",
                            f"-p{args.password}", args.db, "-e",
                            f"source {os.path.join(args.migrations, MIGRATORS[1])}"],
                           capture_output=True, text=True, check=True)
        after = {t: _columns(args, args.db, t) for t in COLUMNS}
        leftover = {t: [c for c in cols if c in after[t]] for t, cols in COLUMNS.items()}
        if any(leftover.values()):
            return fail(f"回退后仍残留: {leftover}")
        report["steps"].append({"step": "rollback_twice_idempotent", "columns": before})

        # 再把正向跑一次，证明回退后可重放（升级路径真实可用）
        subprocess.run(["mysql", f"-h{args.host}", f"-P{args.port}", f"-u{args.user}",
                        f"-p{args.password}", args.db, "-e",
                        f"source {os.path.join(args.migrations, MIGRATORS[0])}"],
                       capture_output=True, text=True, check=True)
        replay = _columns(args, args.db, "knowledge_base_list")
        if "parse_artifact_id" not in replay:
            return fail("回退后重放失败")
        report["steps"].append({"step": "replay_after_rollback", "value": "ok"})
        return 0
    except subprocess.CalledProcessError as exc:
        return fail(f"执行迁移失败: {(exc.stderr or '')[:300]}")
    except Exception as exc:  # noqa: BLE001
        return fail(f"{type(exc).__name__}: {exc}")
    finally:
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
