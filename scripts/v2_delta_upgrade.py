#!/usr/bin/env python
"""离线差分升级：在"已装基线"的环境上只装新增/替换的 wheel。

为什么要有这个而不是"重新装一遍"：
- 干净机首次部署用完整 manifest 没问题；但**升级**时重装全部 wheel 会把已在跑的
  环境整个换掉（包括那些没变的包），升级窗口变长、回滚更难；
- 真正需要知道的只有三件事：新增了哪些、替换了哪些、删掉了哪些（后者不会自动卸）。

本脚本不猜依赖关系：它按 manifest 的 `file`+`sha256` 做集合差，装的时候靠 pip 的
`--no-index --find-links`，缺依赖会立刻失败——不会"看起来装完了其实少包"。

两条硬规则（都是踩出来的）：
1. **替换必须显式授权**（`--allow-replace`）。把 models 包直接并进 parse 会把
   numpy 1.26.4 顶成 2.x、pandas 跟着 ABI 崩，而"升级成功"的日志一切正常；
2. **改完必须能回锁**（`--repin`）。升级完再 `numpy==1.26.4` 这一步不能靠人记。
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def load_manifest(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    wheels = {w["file"]: w for w in doc.get("wheels") or []}
    return doc, wheels


def resolve_dirs(base_wheels, base_dir, add_sets):
    """file → 所在目录。装在多目录时 pip 用绝对路径最稳（裸文件名会被当成本地文件）。"""
    where = {name: base_dir for name in base_wheels}
    for wheels, directory in add_sets:
        for name in wheels:
            where[name] = directory
    return where


def pkg_key(filename):
    """wheel 文件名 → **包名**（不含版本）。按包比而不是按文件名比。

    踩过两次：
    - numpy-1.26.4 与 numpy-2.4.6 是两个不同文件名，只比文件名会把它算成"新增"，
      于是差分升级悄悄装上 numpy 2.x，pandas 运行期 ABI 崩——日志看着一切正常；
    - 把版本塞进 key 又会让"同包两版本"各占一格（hf-xet 1.7.0/1.8.0 同时进安装列表），
      pip 直接 ResolutionImpossible。所以 key 只留包名，版本另行比较。
    """
    stem = filename[:-4] if filename.endswith(".whl") else filename
    return stem.split("-")[0].lower().replace("-", "_")


def pkg_version(filename):
    stem = filename[:-4] if filename.endswith(".whl") else filename
    parts = stem.split("-")
    return parts[1] if len(parts) > 1 else ""


def diff(base_wheels, add_sets):
    """base_wheels / add_sets 都是 {文件名: 条目}；返回按**包**算出来的差集。

    多份 add 清单之间同包不同版本时，**后给的覆盖先给的**，并把被覆盖的记进 superseded。
    不这样做就会让同一个包的两个版本同时进安装列表，pip 直接 ResolutionImpossible
    （实测 hf-xet 1.7.0 与 1.8.0）。
    """
    base_by_pkg = {pkg_key(n): (n, w) for n, w in base_wheels.items()}
    add_by_pkg, superseded = {}, []
    for wheels in add_sets:
        for name, entry in wheels.items():
            key = pkg_key(name)
            if key in add_by_pkg and add_by_pkg[key][0] != name:
                superseded.append({"package": key,
                                   "dropped": add_by_pkg[key][0], "kept": name})
            add_by_pkg[key] = (name, entry)

    added = sorted(name for key, (name, _e) in add_by_pkg.items() if key not in base_by_pkg)
    removed = sorted(name for key, (name, _e) in base_by_pkg.items() if key not in add_by_pkg)
    replaced = sorted(
        name for key, (name, entry) in add_by_pkg.items()
        if key in base_by_pkg and base_by_pkg[key][1]["sha256"] != entry["sha256"])
    install = added + replaced            # 替换的包内容变了，目标侧同样要装
    return {"added": added, "removed": removed, "replaced": replaced,
            "install": install, "superseded": superseded}


def inventory(python):
    """venv 当前装了哪些包（name → version）。用 pip 自己的视图，不猜 dist-info。"""
    proc = subprocess.run([python, "-m", "pip", "list", "--format=json"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"pip list 失败：{(proc.stderr or '')[-200:]}")
    return {item["name"].lower().replace("_", "-"): item["version"]
            for item in json.loads(proc.stdout)}


def snapshot(python, path, *, note=None):
    """升级前快照：只存"包名→版本"，不复制整个环境。

    为什么不复制 venv：几百 MB 到几 GB，而且 venv 里写死了绝对路径，搬走也未必能用。
    版本清单 + 离线 wheelhouse 足以精确重建。
    """
    snap = {"schema": "llmke.env-snapshot.v1", "python": python,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "packages": inventory(python), "note": note}
    Path(path).write_text(json.dumps(snap, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    return snap


def rollback(python, path, find_links):
    """按快照把版本装回去。**不卸载**快照里没有的包，只报出来。

    自动卸载是把"回滚"变成"再炸一次"的典型做法：新装包可能被别的包依赖，
    卸掉它会让原本正常的组件起不来。所以 extras 只报告，由人决定。
    """
    snap = json.loads(Path(path).read_text(encoding="utf-8"))
    want = {k.lower().replace("_", "-"): v for k, v in snap["packages"].items()}
    have = inventory(python)
    restore = sorted(f"{name}=={ver}" for name, ver in want.items()
                     if have.get(name) != ver)
    extras = sorted(name for name in have if name not in want)
    report = {"schema": "llmke.env-rollback.v1", "snapshot": os.path.basename(path),
              "snapshot_at": snap.get("at"),
              "restore_count": len(restore), "restore": restore[:40], "extras": extras,
              "status": "PLANNED"}
    if restore:
        args = ["--no-index"]
        for directory in find_links:
            args += ["--find-links", directory]
        rc, tail = pip(python, args + restore)
        report["rc"] = rc
        report["tail"] = tail
        report["status"] = "PASS" if rc == 0 else "FAIL"
    else:
        report["status"] = "PASS"        # 已经在快照状态，无事可做
    report["after"] = {k: v for k, v in inventory(python).items() if k in want}
    report["matches_snapshot"] = report["after"] == want
    return report


def pip(python, args, timeout=3600):
    proc = subprocess.run([python, "-m", "pip", "install", "-q"] + args,
                          capture_output=True, text=True, timeout=timeout)
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-4:]
    return proc.returncode, tail


def main(argv=None):
    ap = argparse.ArgumentParser()
    # 回滚模式不需要 manifest；升级模式在下面显式校验，避免 argparse 把回滚挡在门外
    ap.add_argument("--base-manifest")
    ap.add_argument("--base-wheel-dir")
    ap.add_argument("--add-manifest", action="append", default=[])
    ap.add_argument("--add-wheel-dir", action="append", default=[])
    ap.add_argument("--python", default=sys.executable, help="目标 venv 的 python")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--allow-replace", action="store_true",
                    help="允许替换基线里已存在的包（不授权则直接拒绝，避免悄悄顶版本）")
    ap.add_argument("--repin", action="append", default=[],
                    help="升级后回锁，如 numpy==1.26.4（可重复）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--snapshot", default=None,
                    help="升级前把 venv 的包版本快照写到该路径（回滚用）")
    ap.add_argument("--rollback", default=None,
                    help="回滚模式：按该快照文件把版本装回去（忽略 base/add 参数）")
    args = ap.parse_args(argv)

    if args.rollback:
        dirs = [args.base_wheel_dir] + list(args.add_wheel_dir or [])
        report = rollback(args.python, args.rollback, dirs)
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                      encoding="utf-8")
        print(json.dumps({"status": report["status"], "restore": report["restore_count"],
                          "extras": len(report["extras"]),
                          "matches": report["matches_snapshot"]}, ensure_ascii=False))
        return 0 if report["status"] == "PASS" and report["matches_snapshot"] else 1

    if not args.base_manifest or not args.add_manifest:
        raise SystemExit("升级模式需要 --base-manifest 与 --add-manifest")
    if len(args.add_manifest) != len(args.add_wheel_dir):
        raise SystemExit("--add-manifest 与 --add-wheel-dir 必须一一对应")

    _, base_wheels = load_manifest(args.base_manifest)
    merged = dict(base_wheels)
    per_manifest, add_sets = [], []
    for manifest, directory in zip(args.add_manifest, args.add_wheel_dir):
        _, wheels = load_manifest(manifest)
        per_manifest.append({"manifest": os.path.basename(manifest), "wheels": len(wheels)})
        add_sets.append((wheels, directory))
        merged.update(wheels)          # 后给的覆盖先给的（升级语义）

    snap = None
    if args.snapshot and not args.plan_only:
        snap = snapshot(args.python, args.snapshot,
                        note=f"before upgrade {os.path.basename(args.base_manifest)}")

    plan = diff(base_wheels, [wheels for wheels, _ in add_sets])
    plan["replaced_risky"] = plan["replaced"][:]
    report = {"schema": "llmke.delta-upgrade.v1",
              "base": {"manifest": os.path.basename(args.base_manifest),
                       "wheels": len(base_wheels)},
              "add": per_manifest,
              "plan": {k: (v if k != "install" else len(v)) for k, v in plan.items()},
              "plan_detail": plan, "installed": None, "status": "PLANNED",
              "snapshot": {"path": args.snapshot, "packages": len(snap["packages"])}
              if snap else None}

    if plan["replaced"] and not args.allow_replace:
        # 不授权就不动：悄悄把 numpy 顶到 2.x 的后果是 pandas 在运行期崩，日志里看不出来
        report["status"] = "REFUSED_REPLACEMENTS"
        report["plan_detail"]["replaced"] = plan["replaced"]
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                      encoding="utf-8")
        print(json.dumps({"status": report["status"], "replaced": len(plan["replaced"]),
                          "sample": plan["replaced"][:3]}, ensure_ascii=False))
        return 2

    if not args.plan_only:
        where = resolve_dirs(base_wheels, args.base_wheel_dir, add_sets)
        find_links = []
        for directory in [args.base_wheel_dir] + args.add_wheel_dir:
            find_links += ["--find-links", directory]
        paths = [str(Path(where[name]) / name) for name in plan["install"] if name in where]
        rc, tail = pip(args.python, ["--no-index", *find_links, *paths])
        report["installed"] = {"count": len(paths), "rc": rc, "tail": tail}
        report["status"] = "PASS" if rc == 0 else "FAIL"

        if rc == 0 and args.repin:
            rrc, rtail = pip(args.python, ["--no-index", *find_links, *args.repin])
            report["repin"] = {"pkgs": args.repin, "rc": rrc, "tail": rtail}
            if rrc != 0:
                report["status"] = "FAIL"

    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                  encoding="utf-8")
    print(json.dumps({"status": report["status"], "plan": report["plan"],
                      "installed": (report["installed"] or {}).get("count")},
                     ensure_ascii=False))
    return 0 if report["status"] in ("PLANNED", "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
