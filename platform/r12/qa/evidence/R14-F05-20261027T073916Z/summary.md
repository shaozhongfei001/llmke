# R14-F05 权限域对照 20261027T073916Z

总计 9/9 PASS

- 问题：客户访前准备的日均存款是多少？
- kb_9 专属事实标记：2,983,333.33（来源 docx-plain.docx，仅存在于 kb_9）

| 用例 | 结果 | 说明 |
|---|---|---|
| F05-A0 前置：admin 在 kb_9 上可回答该问题 | PASS | http=200 status=2 refs=2 err=None |
| F05-A1 前置：admin 引用不含 kb_9 之外的来源（否则对照组无意义） | PASS | refs=2 空source=1 域外=[] |
| F05-A2 r13_reader 在 kb_9 上可正常回答（授权域内可用，显式自有配置） | PASS | http=200 status=2 configId=10 answer_len=22 refs=2 err=None |
| F05-A3 r13_reader 引用 100% 落在 kb_9（跨域引用=泄露） | PASS | refs=2 含kb_9=1 空source=1 域外=[] |
| F05-A4 r13_reader 答案与引用中不含 kb_10 痕迹 | PASS | 引用含 kb_10=[] 答案含'kb_10'=False |
| F05-A5 不传 configId：要么回落默认助手作答，要么给出**可判读的拒绝**（400+4014，不得 5xx/空体） | PASS | http=200 status=2 answer_len=22 err=None | 裸POST http=None errorCode=None 判定=回落成功 body='' |
| F05-A6 拒绝态不得把『缺少助手』复用成越权码 30016，且必须带可读文案 | PASS | http=None errorCode=None 文案含'缺少默认助手'=False msg='' |
| F05-B1 配置只指向 kb_10 时，kb_9 专属提问被拒绝或明确无召回 | PASS | http=403 status=None denied=True refs=0 引用含kb_9=[] 答案含kb_9专属事实(2,983,333.33)=False answer_len=0 err=None |
| F05-B2 不存在'答得出但无引用'的跨域泄露形态（答案含 kb_9 事实即判泄露） | PASS | http=403 答案长度=0 引用数=0 答案含kb_9专属事实=False |

## 夹具动作

- r13_reader 登录成功（口令来自 security_acceptance 夹具，非新建）
- r13_reader 自有配置 configId=10（指向 kb_9，is_default=0；由 security/revoke 夹具建立或本脚本补齐）
- 助手配置 fixture configId=26（create_by=r13_reader, is_default=0, knowledge_base_name=kb_10）: 新建
- 已软删 fixture configId=26（is_del=-1，改名留痕；未改任何既有配置/授权行）

## 边界

- 本脚本只验证"授权域外内容不得经引用/答案泄露"，不重复 SEC/REVOKE 的 403 全矩阵。
- kb_10 内容与 kb_9 高度重叠（同名 product-loan/ledger 均存在），故 kb_9 专属标记只取 `docx-plain.docx` 的日均存款数值，属文件集合事实，不依赖模型措辞。
- 多版本（V0/V1）维度的跨域对照依赖 C 的多版本夹具，本脚本未覆盖。
