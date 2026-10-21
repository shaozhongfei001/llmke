# 多合同边界

当前注册18份：3 API、11 JSON Schema、semantic/evidence/evaluation/rules 各1。全部由registry登记；没有第二个OpenAPI目录。

- core 是共享 wire/domain 模型，不在三个API重复定义字段；API通过可解析ref引用。
- retrieval-model 是core统一命中的入口；ContextManifest、AuthContext、SSE和KB操作有明确消费者。
- generation-manifest 是不可变内容；generation-lifecycle 是可变BuildRun；发布状态与激活指针在业务存储维护，按INDEX-LIFECYCLE实现。
- error-register 是真实数据；error-codes schema同时校验登记数据与受控词汇，checker确认闭集一致。
- semantic 是实体类型规则；evidence 是证据使用政策；evaluation 是决策与验收规则。合同文件不是签字，真实题库/阈值批准另存受信审批。
- reuse-decision/db-migration 是决议/迁移证据的数据契约，不是从CSV猜出的生产DDL。

每份合同有producer/consumer、owner、版本、兼容决议和validator。编译DTO可选成熟工具或手写显式映射；无论方式如何，Java/Python均必须消费同一共享样本，满足oneOf/allOf、required/null/enum和运行时不变量。现有generated是lossless验证包，不宣传为已完成SDK。
