# 离线安装包（wheelhouse + 清单）

仓库**只存清单**，不存 wheel（3.5 GB 无法进 git）。清单与冻结清单必须同级存放。

## 组装

```bash
pip download --no-deps -r locks/hipporag-2.0.0a4-requirements.txt -d /path/to/wheels
python scripts/build_offline_bundle.py \
  --wheel-dir /path/to/wheels \
  --requirements offline/hipporag-2.0.0a4-requirements.txt \
  --name hipporag-2.0.0a4-py311-linux-x86_64 --python 3.11 \
  --out offline/hipporag-2.0.0a4-py311-linux-x86_64.manifest.json
```

## 安装（目标机断网）

```bash
python3.11 -m venv /opt/hipporag-venv
python scripts/install_offline_bundle.py \
  --manifest offline/hipporag-2.0.0a4-py311-linux-x86_64.manifest.json \
  --wheel-dir /path/to/wheels --pip /opt/hipporag-venv/bin/pip
```

安装器会先逐文件校验 sha256 与大小、再校验冻结清单哈希，任一不符直接失败。

## 两条不能忘的事实

1. 必须 `--no-deps`：冻结清单里有历史钉版冲突，带解析会 `ResolutionImpossible`；
2. 必须先校验再装：离线环境最隐蔽的故障是"同名不同内容的旧 wheel"。

## 校验

```bash
pytest tests/test_offline_bundle_manifest.py -q   # 清单自洽 + 冻结清单未漂移
```
