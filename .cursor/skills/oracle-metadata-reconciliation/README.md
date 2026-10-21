# Hermes Oracle Metadata Reconciliation Skill

本压缩包包含用于 Hermes Agent 的 Oracle 元数据自动汇总与人工数据字典核对 Skill。

## 文件说明

- `SKILL.md`：Skill 主文件，包含完整的目标、输入输出、执行流程、采信规则、差异报告规范和安全要求。
- `config.template.yaml`：推荐配置模板，可按实际 Oracle 连接信息和数据字典路径修改。

## 使用建议

1. 将 `SKILL.md` 放入 Hermes Skill 目录。
2. 根据实际环境复制并修改 `config.template.yaml`。
3. 使用只读 Oracle 账号执行元数据采集。
4. 不要在配置文件中明文保存生产密码，建议使用环境变量或密钥引用。
