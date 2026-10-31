# `use-mineru` 开关真跑：开/关/MinerU 坏 三种状态（2026-10-31）

离线安装通了不等于"敢开开关"。这一轮把开关在**真实 nacos 配置 + 真实 MinIO 取文件 + 真实
parse 服务代码**下跑了一遍，并验证了失败回退。

## 演练怎么做（`scripts/v2_switch_drill.py`）

1. 读测试 data-id（`alg_doc_config_py_v2test`）的完整配置，只改 `use-mineru` 一行，
   发布成 `alg_doc_config_py_v2switch_on` / `_off` / `_broken`（**不动线上 data-id**）；
2. 把 `cn-scan.pdf` 传进 MinIO（`v2probe/cn-scan.pdf`）——loader 走 `MinioFile` 取文件，
   直接传本地绝对路径会被当成 `bucket=/` 而报 `invalid bucket name /`；
3. 每个变体起一个子进程跑真实 `load_files`，收集抽到的正文与关键日志。

## 结果

| 变体 | 正文 | 关键中文 | 事件 |
|---|---|---|---|
| `use-mineru: true` | **111 字符** | ✅ 命中「授信审批意见通知书」 | `使用minerU parser` |
| `use-mineru: false` | 0 字符 | ❌ | 走自建 `PDFParser`，对扫描件无正文 |
| `true` + MinerU 配置不可用 | 0 字符 | ❌ | `使用minerU parser` → `外部解析器解析失败，尝试使用自建解析` → `使用parser` |

第三条是关键：`bypass: true` 时**不会崩**，但自建解析器对扫描件同样出不了正文
（还依赖本地 OCR 模型，本环境没有，最终 `解析失败` 被外层吞掉、返回空结果）。
所以开关的真实含义是：**开 = 扫描件有正文；关/坏 = 静默空结果**——这也是为什么
"看着没报错"不能作为验收依据。

## 过程中踩到的四个坑（都是"量尺/环境"问题，不是解析器问题）

1. **`ParsedText` 的正文在 `page_content`，不是 `.text`。**
   我第一版用 `getattr(doc, "text", "")` 统计，于是"解析成功"显示 0 字符，
   差点把平台判成解析失败。与 Q 里查 ES 字段是同一类错误：先确认字段名再下结论。

2. **`MinerUParser` 里 `file_name + request_id.get()` 直接拼字符串。**
   没有请求上下文时 `request_id.get()` 返回 `None` → `TypeError: can only concatenate str`。
   真实服务由中间件设置，脚本必须自己 `request_id.set(...)`。这是隐式耦合，
   任何在请求上下文外调用它的代码都会踩。

3. **平台 `loguru` 默认 `enqueue=True`，队列 sink 在 magic_pdf 的多进程里被 pickle**
   → `cannot pickle '_io.TextIOWrapper' object`。必须先 `import log` 让平台配好，
   再整体换成内存 sink，顺序反了会把队列 sink 装回来。

4. **`load_files` 只认 MinIO 路径**，喂本地路径报 `invalid bucket name /`，
   很容易被误读成"解析器挂了"。

## 还没做

- 只测了**扫描 PDF**；`doc/docx → PDF` 转换路径仍受 LibreOffice 缺 writer 限制；
- 没测**并发**下开关切换（配置热更新时进行中的任务会不会换解析器）；
- 没测开关关闭时自建解析器**装齐本地 OCR 模型**后的效果（本环境没有那些模型）；
- `use-mineru` 在**线上 data-id 仍为 false**：这次只在测试 data-id 上验证，
  真正切换需要发布 + 观察一轮，未做。
