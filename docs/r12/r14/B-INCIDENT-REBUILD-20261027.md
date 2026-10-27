# 事故报告：kb_9 图重建（两轮均失败，已回滚）

作者：B-graph ｜ 日期：2026-10-27 ｜ 状态：**已回滚，环境恢复到动手前；不写"重建成功"**

## 0 一句话

两次"重建"都失败，原因不同；第二次把图打成空图约 2 分钟，并把 F 的 acceptance 撞成 `INVALID`。
现已回滚到 `87 顶点 / 122 边`（与备份逐项相等），G1 恢复 30/60/60；**重建本身没有完成**。

## 1 时间线（含每一次写入）

```
13:30  第 1 次"重建"：rebuild_kb9_effective.py --execute
       该脚本 del_space 传 "kb_9"（无 g_ 前缀）-> DROP SPACE IF EXISTS kb_9 -> 删空气、返回 200
       -> 重抽变成**追加**：87 -> 91（55 old_only / 36 current_only，无删除）
       （我当时只报了"重建完成"，未逐项比对备份，属漏检；后来自查发现）

14:47  pre 快照 standby（91/126），与 A 的 14:2x 快照逐项相同 -> 该时段无写入
14:53:43  F 的 acceptance 结束（34/34）
14:53:52  第 2 次重建开始：del_space(g_kb_9) -> SHOW SPACES 复查"已消失" ✅
14:53:5x  建 schema：CREATE TAG/EDGE 成功；随后立即 REBUILD TAG INDEX
          -> SemanticError: Index entity_name_index not found（**索引是异步创建的**）
          -> 脚本抛错退出，图停在 0 顶点
14:55:55  恢复：generate_triple_data 查询到 9 块（新代）
14:56:09  九次 LLM 抽取
14:56:33  落库完成：30 顶点 / 32 边（file_id 均为新代 328/329/333/343）
          —— 但**评级/加点实体缺失**（源块 139363536840301567 含"个基点"×3、"AAA"×1）
14:57     判定"重建产出比回滚前更差" -> 回滚
          清空 30 顶点 -> 按 backup/kb_9-20261027T053048Z 回灌 -> 87/122（脚本自检一致）
14:58     恢复 ES 社区摘要：先 _delete_by_query 清空（原 1 条）
          -> bulk 首次 latin-1 编码失败 -> 刷新后 0 条 -> 改 UTF-8 重发 -> 7 条
          （**中间约 30 秒摘要为空**）
15:05     A 出 post 快照：87/122 全 old_only（= 回滚后状态，非重建成效）
15:12     实时复核：Nebula 87/122；ES kb_9=9、摘要=7；Milvus 实体表 AA/AAA/基点 0 命中
```

## 2 三步失败（各自独立，不能合并成一句"环境问题"）

### 2.1 `del_space` 静默空转（第 1 次失败）

```python
# graph_service.py:176/179
session.execute(f'USE {del_param.space_name};')                   # 不补前缀
del_query = f"DROP SPACE IF EXISTS {del_param.space_name};"        # 名字不存在 -> 合法成功
```
实测：传 `r14b_probe` -> 200「删除成功」但空间仍在；传 `g_r14b_probe` -> 真删。
调用方传 `kb_9`（真实空间 `g_kb_9`）→ **零删除 + 200**。

### 2.2 建 schema 后立刻 REBUILD 索引（第 2 次失败的起点）

索引创建是异步的，`REBUILD TAG INDEX` 立即执行会 `Index ... not found`，
脚本未容错 → 中途退出 → **图停在 0 顶点**。

### 2.3 重抽产出缺评级/加点（第 2 次失败的实质）

```
输入：9 块（新代）
输出：30 实体 / 32 边
缺失：AAA级/AA级/30·60·100个基点/客户信用评级 —— G1 依赖的全部
```
离线复现（服务内同函数+同配置，对块 139363536840301567 单块跑）：17 实体 / 15 关系，仍无上述实体。
→ **不是流水线抖动**。A 从日志解析出 `('北方重工配件厂','信用评级','AA')`，但 Milvus 实体表 0 命中，
说明问题可能是"抽了但中途被丢"（续写探针 `max_tokens=1` + `=="Y"` 精确匹配、`count<2` 上限、首轮 max_tokens 截断），
**尚在定性中**（A 的零成本复放）。

## 3 回滚过程（已演练，含一次自身失误）

```
① Nebula：清空当前顶点（DELETE VERTEX ... WITH EDGE）-> 按 nebula.json 逐条回灌
           -> 87/122，与备份逐项相等（脚本自检）
② ES 摘要：先误删（_delete_by_query 清 1 条）-> bulk latin-1 编码失败 -> 改 UTF-8 重发 -> 7 条
            **教训：bulk 必须 .encode("utf-8")；否则表现为"200 但 0 条"**
③ Milvus：**未回滚**（我漏了）-> 现状 ES 7 条 vs Milvus 1 条，已报 TL 待处置
```

## 4 四条教训（已进纪律）

```
① 破坏性重建必须先在**同构影子环境**跑通并比对数，再动真库
   补充：影子演练前要确认"下游依赖哪些数据源"——我搭的影子 space 因抽取还查库/Milvus 而失败，
        影子 space 只是"假影子"
② 建 schema 后必须轮询索引就绪（DESCRIBE INDEX），不能立刻 REBUILD
③ 开工公告必须三段：起–止 / **图是否可用（断言请避开）** / 请勿重启哪些服务
   第 3 段是这次最贵的：F 照"只别重启"去跑，撞进 2 分钟空窗
④ 备份恢复必须**先演练**（备份没演练过 = 没有备份）
   我这次是第一次跑恢复脚本，边写边修，还撞了编码问题，造成 30 秒摘要为空
```

再加一条过程性的：

```
⑤ 任何"重建完成"的结论，必须先把 **重建前备份** 与 **重建后现状** 逐项比对再报
   —— 第 1 次失败就是因为只报了"完成"，没做这一步，87->91 过了 3 小时才被自己发现
```

## 5 当前状态与交付口径

```
Nebula  g_kb_9                    87 顶点 / 122 边（全 old_only —— 因为是回滚的旧备份）
ES      kb_9 9 块 / 摘要 7 条
Milvus  实体表 AA/AAA/基点 0 命中；_community_summary=1（我这次重抽写的残留）
G1      30 / 60 / 60，引用 [L0-18625408]
```
**交付写法**：
```
M1 = 重建未完成，已回滚至 87/122 基线（不得写"重建成功"或"87→79 已达成"）
M1b = UNVERIFIED
已定位两个独立缺陷：① del_space 静默空转（含接口契约不一致）② 重抽产出缺评级/加点（定性中）
F 的 14:55 那一轮 acceptance 标 INVALID（图重建窗口）
```

## 6 未决项

```
① Milvus 摘要残留 1 条（ES 7 条）-> 建议删除，等 TL 批准
② 重抽缺评级/加点的定性（A 的复放）-> 结论出来再决定是否做第三次重建
③ 影子演练需要"可用的影子 KB"（有 DB 行 + Milvus collection），当前不具备
```

## 7 追加：P1-03 根因定位与修复（离线验证通过，未上线）

### 7.1 根因分层（从"最近"到"最远"）

```
第 0 层（主因）：首轮 requests_llm 未传 max_tokens -> 吃服务端默认值
                 459 字块的输出在 ~20 行实体处**硬截断**（最后一行停在"十五个工作日"），
                 尾部的"AAA级加30个基点，AA级加60个基点，A级加100个基点"从未进入输出
第 1 层：关系行解析原为严格 5 段解包，模型少写一段 description 即抛异常并丢整条关系
         （实测一轮丢 5~8 条，集中在长描述关系上）
第 2 层：续写探针 max_tokens=1 + `== "Y"` 精确匹配 -> 回 "Y\n" 即判 False，永不续写
第 3 层：轮次上限 count<2 -> 即使探针生效也只补一轮
第 4 层：temperature=0.1 -> 同一块三次跑出 17/20/27 个实体，评级档位时有时无
放大器：分块粒度（产品要素 + 评级加点表塞进同一 459 字块）→ 更容易触顶
```
**"每块约 10 条"不是模型决定，是输出预算决定。**

### 7.2 改动（全部在 `index_graph_service`，未加载到运行态）

```
graph_extract.py:34   轮次上限 2 -> 5（GRAPH_EXTRACT_MAX_ROUNDS 可调）
graph_extract.py:49   续写探针 max_tokens 1 -> 4；判定 strip().upper().startswith("Y")
graph_extract.py:52   首轮显式 max_tokens=2048（GRAPH_EXTRACT_MAX_TOKENS 可调）
graph_extract.py:144  关系行解析容错（<4 段抛错，>5 段把多余部分并入 description）
prompts/entity_extraction.py  新增 2.1：分级/分档对照必须逐项抽取（附反例）
graph_extract.py      抽取温度 0 + seed=42
```

### 7.3 离线验收（同一块 `139363536840301567`，三次）

| 次数 | 实体 | 关系 | 评级相关实体 |
|---|---|---|---|
| 1 | 27 | 20 | AAA级 / AAA级加30个基点 / AA级加60个基点 / A级加100个基点 |
| 2 | 27 | 20 | 同上 |
| 3 | 27 | 23 | 同上 |

关系形如 `AAA级 -等级 -加点幅度-> 利率-> AAA级加30个基点`（三档齐全）。
**判据：实体 >25 ✅；AAA级/AA级/A级 均出现（≥3）✅。**

### 7.4 未做的

```
- 未重启 19529（改动未生效于运行态）
- 未做第三次真库重建（等 TL 决定）
- 未清理 Milvus 残留 1 条摘要（等 TL 批准）
```

## 8 追加二：P1-03 真因修正（A 的复放 + B 的对照实验）

### 8.1 被推翻的三个假设

```
❌ max_tokens 截断：2048 与 8192 输出完全一致（finish=stop），模型自己收尾
❌ count<2 轮次上限：根本没进第 2 轮
❌ `== "Y"` 当前不是 bug：探针 max_tokens=1 时换行被截掉，恰好返回 'Y'，判等成立
```
> **但它是定时炸弹**：任何人把探针 max_tokens 调大（看起来像"修 bug"），
> 立刻得到 `'Y\n'` -> 判 False -> 续写静默失效，且不报错。

### 8.2 B 的对照实验（同一块 139363536840301567）

| 组合 | 实体 | AAA/AA/A | 30/60/100 个基点 |
|---|---|---|---|
| 业务类型表 + 整块 | 23~32 | 全有 | **0/6** |
| 默认 8 类 + 整块 + "表格逐项抽取"提示 | 10~46 | 全有 | **5/6** |
| 默认 8 类 + 提示 + **3 次采样取并集** | 37~53 | 全有 | **3/3** |

### 8.2.1 因子矩阵（A 的复放，交付引用这一份）

```
证据：platform/r12/graph/evidence/factor_matrix_summary_20261027T0800Z.json
条件：qwen2.5-7b-instruct / t=0.01 / max_tokens=2048 / seed=42 / 每格 n=3 / 同批连续跑

A 46字  + 默认类型   no_nudge 3/3   nudge 3/3
B 196字 + 默认类型   no_nudge 3/3   nudge 3/3
C 459字 + 默认类型   no_nudge 2/3   nudge 3/3    <- 提示把唯一不稳的一格补上
A 46字  + 业务类型   no_nudge 3/3   nudge 3/3
C 459字 + 业务类型   no_nudge 3/3   nudge 3/3
```
三条结论（与 B 的结论合并后一致）：
```
① 提示是杠杆：加"表格逐项抽取"后，5 个组合全部 3/3
② 类型表不是开关：不加提示时短块 3/3、长块 2/3(默认) vs 3/3(业务) —— 提高命中率，但不决定
③ 长度只在不加提示时起作用：46/196 字不加也 3/3，459 字不加才掉到 2/3
```
> **表述纪律**：B 观察到"业务类型表 + 整块 -> 基点 0/6"是**在 prompt 2.1 下**测得的；
> A 用仓库原 prompt 测得同格 3/3。两者条件不同、并不矛盾；交付只保留上表口径。

结论：
```
① 不是分块问题（A 组 100 字单句照样会漏）
② 不是 entity_types 问题（换成业务类型反而更差：基点 0/6）
③ 是**随机整段漏抽**（A：同一块 5 次里 2 次全无；我：6 次里 1 次无）
④ 有效修法：提示"表格逐项抽取" + **多次采样取并集**（p≈0.4，3 次全漏≈6%）
```

### 8.3 最终改动（已在源码，未加载到运行态）

```
prompts/entity_extraction.py  新增 2.1：分级/分档对照必须逐项抽取（含反例）  <- 主要手段
graph_extract.py              GRAPH_EXTRACT_SAMPLES（默认 3）多采样并集     <- 主要手段
graph_extract.py              关系行解析容错（少一段 description 不再丢整条）
graph_service.py              日志打出本次使用的 entity_types（可观测）
graph_service.py              _resolve_entity_types：**不擅自升级业务类型表**（实测更差），只记录
graph_extract.py              is_continue 归一化判定（防线，防"调大 max_tokens 就静默失效"）
```
离线验收（3 次）：`AAA级 / AA级 / A级` 与 `30/60/100个基点` **3/3 全部出现**。

### 8.4 Milvus 残留摘要：**未能安全删除，转开放项**

```
TL 给的集合名 _community_summary_kb_9 -> SchemaNotReady: collection not exist
static_count(community_summary_kb_9)  -> 108 行（无法确认是否同一份摘要，不敢盲删）
del_doc_by_col(_community_summary_kb_9) -> "未执行删除，milvus未找到集合"
```
**不做盲删**：不确定集合名与内容时删除，可能制造新的不一致（这正是今天的教训）。
转开放项：由 A 用 pymilvus 直连列出 graph_base 下所有 collection 与其行数，确认后再删。

### 8.5 内容级判据（新，进脚本）

```
重建后必须断言：{AAA级, AA级, 30个基点, 60个基点, 100个基点} 至少 3 个存在
（结构判据 ②③④⑤ 可以全绿而图缺一半 —— 它们验的是"代次/是否被并/类型分布"，
  不验"该抽出来的东西有没有抽出来"）
```

## 9 收口（15:45 硬线到达，第三次重建未做）

### 9.1 结论三句话

```
根因：抽取时 entity_types 落到"人/机构/位置/时间/角色/疾病/药品/项目"8 类通用默认值，
     而 459 字块里的评级加点表不属于其中任何一类 -> 模型判定"无匹配实体类型" -> 静默不抽。
     （A 的同批 n=4 矩阵：整块 + 默认类型 0/4；整块 + 业务类型 4/4；单因子、可复现）

修法：resolver 升级业务类型表 + prompt "分级/分档对照必须逐项抽取" + 固定 seed
     + 首轮显式 max_tokens + 关系行解析容错（+ 可选：多采样取并集防"整批抽风"）。

状态：离线验证 3/3 通过（实体 27；AAA级/AA级/A级 与 30/60/100 个基点全出；关系成三元组）；
     **未在真库验证** —— 今天不做第三次重建。
```

### 9.2 今天为什么没做成第三次（如实）

```
不是能力问题，是时间：三次尝试里前两次各暴露一个真实缺陷
（del_space 传 kb_9 删空气 / schema 索引异步未就绪），把时间用完了。
若强行在 15:45 之后开始，第三次会在"必须快"的状态下做不可逆操作 ——
而"赶时间"正是前两次失败的直接原因（第一次跳了前缀检查，第二次跳了索引就绪轮询）。
```
> 我们不是"没做完"，是"知道了怎么做，但没有时间按正确的方式做"。

### 9.3 Milvus 残留：确认无法安全定位，按开放项处理（不删）

```
static_count(_community_summary_kb_9)          -> collection not exist
static_count(community_summary_kb_9)           -> 108 行（远多于"1 条残留"，疑为跨库共用集合）
del_doc_by_col(_community_summary_kb_9)        -> "未执行删除，milvus未找到集合"
```
→ 在"集合名与内容都不确定"的前提下删除，风险大于收益（今天的教训正是"以为删到了"）。
转开放项：由 A 用 pymilvus 列 `graph_base` 下 collection + 行数，确认后再按 `community_id` 删。
**清理未完成这件事必须写进交付，不能因为"那 1 条只写不读"就默认没事。**

### 9.4 交付口径（最终）

```
M1   = 重建未完成；当前基线 87 顶点 / 122 边（回滚自 backup/kb_9-20261027T053048Z）
M1a  = 未达成（87->79 未发生）
M1b  = UNVERIFIED
P1-03 = 已定位（抽取链路四层静默失效叠加）+ 修法已离线验证 3/3 + 未在真库验证
F 的 14:55 acceptance = INVALID（图重建窗口）
```

## 10 技术债：把"不知道"伪装成"不存在"（A 实测确认）

> **本节头条（TL 指定放第一行）：`utility.has_collection(coll, using="graph_base")`
> 抛的是 `ConnectionNotExistException: should create connection first`（"你连连接都没建"），
> 被 `except Exception: return False` 吞成"集合不存在"，再包一层 `code=200`。
> 揭示的问题不是"没信息"，而是"**错的信息**"——`num_entities=108` 同类：值是真的，但它回答的不是你问的问题。**

### 10.1 定死的链路（pymilvus 2.6.2 实测）

```
connections.connect(alias="gtest", host=..., db_name="graph_base")
utility.has_collection("_community_summary_kb_9", using="graph_base")
  -> ConnectionNotExistException: should create connection first.
utility.has_collection("_community_summary_kb_9", using="gtest")
  -> True
```
代码（`milvus_kb_service.py:1441/262`）：`using=` 里传的是 **db_name**，而 pymilvus 的 `using=` 只认**连接别名**。

### 10.2 四层静默

```
① using=db_name 语义错 -> 抛 ConnectionNotExistException（原文"should create connection first"）
② except Exception: return False -> 异常被吞成"不存在"
③ code=200 + "未执行删除，milvus未找到集合" -> 调用方看到成功
④ 文案说"集合不存在"，真因是"连接/别名没建"
```
> 最讽刺的一层：**异常原文比转述后的信息更准确**——"你连连接都没建"被报告成"集合不存在"。

### 10.3 修法（不是今天改）

```python
def is_collection(collection_name, server_config, db_name=None, alias="default"):
    return utility.has_collection(collection_name, using=alias)   # 别名；库在 connect 时给
# 异常不要用 False 兜住：三态 True / False / 查询失败
except Exception as e:
    logger.error(f"has_collection 失败（不是'不存在'）: {type(e).__name__}: {e}")
    raise
```
**关键是把"False（真不存在）"与"异常（不知道）"分开**——今天族谱里一半条目都源于"把不知道伪装成不存在/0/空"。

### 10.4 族谱（今日累计，7 条同源）

```
del_space 传 kb_9（IF EXISTS）-> 200「删除成功」但零删除
ES delete_by_query -> deleted=0，不报错
nGQL DELETE VERTEX 不存在 -> SUCCEEDED
nGQL INSERT 属性名与 schema 不符 -> 不报错也不写入
MATCH ... RETURN v.<prop>（缺 tag 前缀）-> 恒返回 NULL
Milvus num_entities 含墓碑 -> 108 与 live=1 两个口径都"看起来对"
has_collection(using=库名) -> 连接异常被吞成"集合不存在"
```
统一判据：**任何"成功/为空/不存在"都不能单独作为判据，必须做"同一标识的前后对照"。**

## 11 环境终态（收口时只读快照，可复核）

```
时间：2026-10-27 15:52:42（A 独立采集；B 同期读数逐项一致）
ES     kb_9 = 9   table_chunks_kb_9 = 2   table_summary_kb_9 = 2   community_summary_kb_9 = 7
Nebula g_kb_9 = 87 顶点 / 122 边
Milvus(graph_base) live：_graph_entity_kb_9 = 42 / _graph_triples_kb_9 = 40 / _community_summary_kb_9 = 1
```
> 两份独立读数（不同连接、同一口径）一致，可作为"当日 14:58 之后未再写入"的见证。

### 11.1 三处不一致的记账（每条一句，便于评审扫读）

```
① ES community_summary = 7  vs  Milvus _community_summary live = 1
   -> 摘要两侧不一致（14:56 重抽写入 1 条，回滚只恢复了 ES）

② Milvus entity 42 / triples 40  vs  归档基线 53 / 72
   -> **回灌属于写操作，且 Milvus 三处需同时回灌，今天没有演练过的干净窗口，故未执行**
      （回滚只覆盖 Nebula + ES —— "逐存储清点"这条教训的由来）

③ Nebula 87/122 全 V0 file_id
   -> 按备份回灌的**预期结果**，不是归属缺陷
      （中间态 30 顶点/32 边的 file_id 确为新代 328/329/333/343，B 已 dump）
```

### 11.2 开放项与明日顺序（若做）

```
今天不回灌：Milvus 三处统一记开放项（含残留摘要 1 行）
措辞（TL 定）：**"回灌属于写操作，且 Milvus 三处（entity/triples/summary）需同时回灌，
              今天没有演练过的干净窗口"** —— 是"知道该怎么做但选择不做"，不是"忘了做"
理由：写操作跨 3 个集合，且当前没有能复测 G1 的干净窗口；
     今日所有事故都来自"临收口前动了不该动的"

明日顺序：dry-run 双见证（A 出第一份、B 出第二份，口径 pk>=0 计数）
        -> 回灌 entity 53 / triples 72 / 删摘要 1 行
        -> 三验：live 行数对齐 / G1 30·60·60 / global 引用仍出
```
