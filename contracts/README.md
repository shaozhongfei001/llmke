# 受控合同 V1.1.0

18份合同见registry。11份JSON Schema共享core并保留完整约束，3API只引用共享schema；其余为semantic/evidence/evaluation/error规则。make generate空目录生成；make check验证语义、跨合同一致性和精确产物联动。generated为验证包，不是已编译DTO SDK。业务状态机另运行contract_runtime与业务回放；政策文件不代表真实批准。
