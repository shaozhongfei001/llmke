#!/usr/bin/env python3
"""R14-F06 离线构建清单生成器（不联网，只读本机构建产物与 ~/.m2）

产出：OFFLINE-BUILD-MANIFEST.tsv
列：kind / coords / name / version / scope / sha256 / local_path / how_to_obtain
     coords = groupId:artifactId:version（从本机 ~/.m2 路径反查，供目标机按坐标从内网镜像取）

口径说明（必须如实）：
  * java-runtime 行来自**实际 fat jar 的 BOOT-INF/lib**，是运行该 jar 真正需要的精确工件，
    坐标从本机 ~/.m2/repository 反查（groupId:artifactId:version）并给出 sha256。
  * java-build 行（parent pom、maven 插件）不在 fat jar 里，无法只靠本机离线枚举，
    因此不编造：改为在 BUILD-OFFLINE.md 里给出 `mvn -Dmaven.repo.local=... dependency:go-offline`
    与内网镜像 settings 的获取方法，由 resolve-maven-offline.sh 在可联网/内网镜像环境执行。
  * npm 依赖以 package-lock.json 为准（lock 即精确清单+integrity 哈希），
    这里给出 lock 的 sha256 和包数，获取方式见 resolve-npm-offline.sh。
  * python 依赖以 requirements.txt 为准，同样给 sha256 与包数。

用法: offline-build-manifest.py <repo_root> <out_tsv>
"""
import hashlib
import json
import os
import re
import sys
import zipfile


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def m2_index(m2: str) -> dict:
    """(artifactId, version) -> jar 路径，按 artifactId/version 目录反查。"""
    idx = {}
    for root, dirs, files in os.walk(m2):
        for fn in files:
            if not fn.endswith(".jar") or fn.endswith("-sources.jar") or fn.endswith("-javadoc.jar"):
                continue
            base = fn[:-4]
            art, _, ver = base.rpartition("-")
            if not art:
                continue
            idx.setdefault((art, ver), os.path.join(root, fn))
    return idx


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: offline-build-manifest.py <repo_root> <out_tsv>", file=sys.stderr)
        return 2
    repo, out = sys.argv[1], sys.argv[2]
    m2 = os.path.expanduser("~/.m2/repository")
    rows = []

    # ---- 1. Java 运行时依赖（从 fat jar 的 BOOT-INF/lib 提取）----
    jars = []
    parent = os.path.join(repo, "services/rag-java/rag-parent")
    if os.path.isdir(parent):
        for d in sorted(os.listdir(parent)):
            t = os.path.join(parent, d, "target")
            if os.path.isdir(t):
                for fn in sorted(os.listdir(t)):
                    if fn.endswith(".jar") and not fn.endswith("-sources.jar"):
                        jars.append(os.path.join(t, fn))
    libs = set()
    for jar in jars:
        try:
            with zipfile.ZipFile(jar) as z:
                for n in z.namelist():
                    m = re.match(r"BOOT-INF/lib/(.+\.jar)$", n)
                    if m:
                        libs.add(m.group(1))
        except zipfile.BadZipFile:
            print(f"  [!!] 不是合法 jar: {jar}", file=sys.stderr)
    idx = m2_index(m2) if os.path.isdir(m2) else {}
    no_local = 0
    for lib in sorted(libs):
        base = lib[:-4]
        art, _, ver = base.rpartition("-")
        local = idx.get((art, ver))
        if local:
            rel = os.path.relpath(os.path.dirname(local), m2)
            group = rel.rsplit("/", 1)[0].replace("/", ".")
            rows.append(("java-runtime", f"{group}:{art}:{ver}", art, ver, "jar",
                         sha256(local), local,
                         "内网 Maven 镜像按坐标取；或从构建机 ~/.m2 复制同路径"))
        else:
            no_local += 1
            rows.append(("java-runtime", f"UNKNOWN:{art}:{ver}", art, ver, "jar", "-", "-",
                         "本机 ~/.m2 未找到同版本（fat jar 内嵌），需按坐标从内网镜像取"))

    # ---- 2. 前端：以 lock 为精确清单 ----
    fe = os.path.join(repo, "frontend/plateform")
    for name, kind in (("package-lock.json", "npm-lock"), ("pnpm-lock.yaml", "pnpm-lock"),
                       ("yarn.lock", "yarn-lock"), ("package.json", "npm-package")):
        p = os.path.join(fe, name)
        if not os.path.isfile(p):
            continue
        cnt = ""
        if name == "package-lock.json":
            try:
                data = json.load(open(p, encoding="utf-8"))
                pkgs = data.get("packages") or {}
                cnt = f"packages={max(len(pkgs) - 1, 0)}"
            except Exception:
                cnt = "packages=?"
        rows.append((kind, "-", name, cnt, "file", sha256(p), p,
                     "内网 npm 镜像：npm ci --registry=<内网>；或构建机 npm ci 后打包 npm-cache"))

    # ---- 3. Python：requirements ----
    for name in ("requirements.txt", "requirements.lock"):
        p = os.path.join(repo, name)
        if not os.path.isfile(p):
            continue
        n = sum(1 for ln in open(p, encoding="utf-8", errors="ignore")
                if ln.strip() and not ln.strip().startswith("#"))
        rows.append(("python-requirements", "-", name, f"lines={n}", "file", sha256(p), p,
                     "内网 PyPI：pip download -r <file> -d wheels；目标机 pip install --no-index --find-links wheels"))

    # ---- 4. 构建配方文件 ----
    for rel in ("platform/r12/maven/settings-r12.xml",
                "services/rag-java/rag-parent/pom.xml",
                "frontend/plateform/vite.config.ts",
                "frontend/plateform/tsconfig.json"):
        p = os.path.join(repo, rel)
        if os.path.isfile(p):
            rows.append(("build-config", "-", rel, "", "file", sha256(p), p, "随包自带"))

    with open(out, "w", encoding="utf-8") as f:
        f.write("kind\tcoords\tname\tversion\tscope\tsha256\tlocal_path\thow_to_obtain\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    kinds = {}
    for r in rows:
        kinds[r[0]] = kinds.get(r[0], 0) + 1
    print("  [ok] OFFLINE-BUILD-MANIFEST.tsv: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    if no_local:
        print(f"  [!!] {no_local} 个 java 运行时工件在本机 ~/.m2 未找到，已标注为需按坐标获取（未编造哈希）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
