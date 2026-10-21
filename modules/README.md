# modules/ — Java 领域与适配（空骨架）

放置 domain / application 层与端口实现。四层依赖单向：
`interfaces → application → domain`，`infrastructure → domain`（实现端口）。

**当前为空是刻意的**：`make p0-gate` 仍为红，L1 未武装。
现在往这里写实现等于在未关闭的 P0 上施工。
