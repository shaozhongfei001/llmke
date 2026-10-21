# 独立QA与外部批准配置

本包没有真实QA公钥、私钥或签署记录。测试中临时生成的密钥只证明验签逻辑，不能认作独立QA。

## 受保护环境

管理员在实现者不可改写的runner/CI配置中，挂载外部JSON信任根，设置LLMKE_TRUST_ROOT到该文件。复制TRUST-ROOT.example.json，填当前FROZEN-MANIFEST文件SHA256和真实principal/public-key/roles；示例保持UNCONFIGURED。文件必须在实现工作区之外，且不是由任务Agent自行生成的“信任”。私钥只在外部签发方，禁止提交或传给实现会话。

principals以key_id索引，内容为 principal_id、enabled=true、roles（qa-owner、baseline-owner、相应业务owner）、public_key_pem。实现者不得拥有其所需独立QA的签发权；受保护配置还需核对当前源码作者/实现者清单，不能只信CLI名称。

## QA执行与接收

1. 独立runner校验基线hash，检出固定源码/制品，运行对应loop的dev先决门及真实qa-run。QA候选结果仍是QA_PENDING。
2. 从候选record导出qa_subject，签名payload须含 purpose=QA_ATTESTATION、principal_id、issued_at/expires_at（不超过7天）、subject_sha256及subject所有字段；subject包含loop/gate、gate定义摘要、源码摘要、基线摘要、日志摘要、真实检查集和PASS结果。
3. 使用外部私钥运行qa_sign.py签署。接收方验证签名/时效/主体/批准基线，主体不得在该切片implementation_principals内；同一份日志随证据移交，不能用本地另一轮日志冒认。
4. accept-qa成功仅将该gate记PASS；finish再次检查全部门与源码新鲜度，才允许DONE。

```bash
python3 scripts/loop_guard.py qa-run --loop L0-contract-baseline --gate independent_qa_gate --executor qa-external
python3 scripts/qa_payload.py --loop L0-contract-baseline --gate independent_qa_gate --principal-id qa-external --out /path/to/unsigned-payload.json
# 独立签发环境：qa_sign.py --key-file /protected/key.pem --key-id <真实key_id> --payload /path/to/unsigned-payload.json --out /path/to/signed-envelope.json
python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline --gate independent_qa_gate --attestation /path/to/signed-envelope.json
python3 scripts/loop_guard.py finish --loop L0-contract-baseline
```

先依实际revision交棒给QA holder；上例不是免前置捷径。无信任根时accept-qa必须失败。

P0关闭：每个D01…都有结论与非空哈希证据，当前snapshot匹配，真实测试PASS，owner和baseline-owner外部批准P0_APPROVAL。waiver保留原影响，不通过strict。

评测政策：先签EVALUATION_POLICY_APPROVAL（dataset_sha256、阈值、policy_version），后测量；结果由QA签EVALUATION_RESULT。不能将结果hash塞到“测量前政策签署”制造先后矛盾。

所有本地完整性检查仅证明在给定受信配置下成立；实现者同时控制代码、日志与外部信任配置时，不存在独立验收保证。生产保护必须在仓库之外落实。

测试执行阶段不得接触签名私钥；签发阶段用独立身份/服务读取受保护作业产物后签署。不能让待验代码与私钥在同一可读权限域执行。
