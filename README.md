# LLMKE V1.1.1 技术施工冻结基线

本基线在 2026-10-20 原框架基础覆盖修订。18份受控合同、角色分工、原资产复用登记和可执行门禁已落地；不含真实业务实现、完整旧源码、生产 DDL 或独立 QA 批准。

**技术控制文件冻结与业务开工是两层。** 原业务四P0仍OPEN；L0合同修复/LD资料核验可运行；L1–L4由真实关闭证据及复用决议放行。验收结果见 docs/baseline/validation，不能把测试夹具的签名当正式QA。

## 安装与核验

Python 3.12；独立 venv/uv，禁止装入系统Python。OpenSSL 3.0+用于外部Ed25519批准；make用于门禁。Java/Maven及数据库环境待迁移首切片就绪后提供。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
make framework-verify
make p0-gate
```

最后一个命令当前必须非零：四P0仍OPEN。不得把它改成成功以获得全绿。离线环境先备齐 requirements.lock 对应平台wheels，再以 `--no-index --find-links /path/to/wheels` 安装；本包未伪称包含这些wheels。

`make framework-verify`执行合同生成/语义与联动、规则镜像、追溯、登记完整性、秘密模式扫描、框架测试及冻结文件校验。业务测试在输入/实现未到位时明确阻断，不用skip/恒真夹具充当交付。

## 工作入口

- 冻结变更：docs/baseline/COMPATIBILITY-DECISIONS.yaml、FROZEN-MANIFEST.json。
- 合同：contracts/registry.yaml；generated仅为**保留完整约束的验证包/索引**，不是已编译的Java/Python DTO SDK。Java消费者必须在相应切片提供实际DTO/验证器与共享样本回放。
- 角色：docs/roles/ROLE-MATRIX.yaml；派工：docs/dispatch。
- 流程：docs/SDD-ENGINEERING.md、LOOP-ENGINEERING.md、SHARED-MEMORY.md、MULTI-CONTRACT.md、API-LAYERING.md。
- 业务约束：docs/policies/AUTHORIZATION.md、INDEX-LIFECYCLE.md、CONTEXT-AND-SSE.md。
- 原资产：docs/reuse，逐项保留/适配/重写/退役，不按文件数计算工期。

## 分批运行

```bash
make run-dev LOOP=L0-contract-baseline EXECUTOR=integration-agent
make run-dev LOOP=LD-legacy-discovery EXECUTOR=legacy-owner
```

上述只做开发自检。QA仍需外部受保护环境，见 docs/ci/QA-TRUST.md。先按LD派工取得完整发布源码、实际DDL和真实政策，关闭原P0，再以带 revision 的 arm 武装对应业务批次；不要手改 STATE。

覆盖安装使用交付包顶层 apply_patch.py；它备份所有覆盖/删除项并保留无关业务文件。scripts/installer.py 仅用于框架初装，不用于本次覆盖。版本演进需更新决议、重新冻结并取得外部信任基线批准，不能改哈希文件冒充旧版本。
