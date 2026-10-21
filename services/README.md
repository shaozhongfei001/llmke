# services/ — Python 算法侧（空骨架）

规划中的子域：`retrieval`（多路召回/融合/精排/分通路埋点）、`index`（解析/分块/嵌入/图抽取）、
`parse`（OCR/表格/版式）、`llm`（生成与上下文装配）。

约束：无状态、不直连业务库、分通路标识只用 `metadata.search_type`。
**当前为空是刻意的**，见 `modules/README.md`。
