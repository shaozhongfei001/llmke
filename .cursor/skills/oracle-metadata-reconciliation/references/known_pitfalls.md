# Oracle 元数据核对 — 已知陷阱

## 1. openpyxl API 错误
- ❌ `wb.get(sheet_name)` — 不存在
- ✅ `wb[sheet_name]` 或先用 `sheet_name in wb.sheetnames` 判断

## 2. Excel 输出空行填充缺陷
- 原程序生成了 6964 行但只有 1114 行有数据，34 列中只有 2 列有值
- 根因: 使用了逐列写入而非逐行写入，导致行号错位
- 修复: 使用 `for row_idx, row_data in enumerate(data, 2)` 逐行写入

## 3. Oracle 注释永久损坏 (ZHS16GBK 字符集)
- 数据库字符集 ZHS16GBK
- 历史迁移数据 (IFS_ 前缀表) 注释字节已是 `0x3f 0x3f 0x3f...`
- 不是读取编码问题，是存入时 UTF-8 → GBK 转换失败
- 检测: `set(str(comment).strip()) == {"?"} and len >= 2`
- 验证: `SELECT DUMP(comments, 1016) FROM all_col_comments WHERE ...`

## 4. 字典文件格式差异
| 文件 | 格式 | 解析难度 |
|------|------|----------|
| 数据仓库数据ACRM相关数据字典.xlsx | 每表一sheet，结构清晰 | 容易 |
| DICT_ACRM数据挖掘前期分析数据模型_V1.xlsx | 分类sheet，结构松散 | 困难（返回0张表） |
| DICT_ACRM系统基础表字段级分析.xlsx | 单大sheet，表名嵌入D列 | 中等 |

## 5. D 列源系统表名格式
- 格式: `"OMDATA.S01_FFHZ/OMDATA.S07_FFHZ"` 或 `"EDW.TABLE_NAME"`
- 需取第一个 part (`split("/")[0]`)，再取 `.` 后面的表名

## 6. Oracle 连接信息（占位模板，真实值只进本地 .env）
- 主机名: `<db-hostname>`（推荐主机名解析，避免硬编码 IP）
- 端口/服务: `1521/<service-name>`
- 虚拟机端口转发环境: /etc/hosts 中 `127.0.0.1 <db-hostname>` 可能是正确配置，删除前先确认
- 过期 IP 会导致 ORA-12170 timeout——连接信息变更后必须同步更新本地 .env
- thick 模式需要 `oracledb.init_oracle_client(lib_dir="<oracle-client-dir>")`；无 client 时用 thin 模式（ORACLE_CLIENT_DIR 留空）

## 6.1 /etc/hosts 导致 <db-hostname> 解析失败
- 现象: `<db-hostname>` 解析到 `127.0.0.1`，连接超时 ORA-12170
- 原因: `/etc/hosts` 中有 `127.0.0.1 <db-hostname>` 的错误条目，覆盖了真实 DNS
- 修复: `sudo sed -i '/^127\.0\.0\.1\s\+<db-hostname>/s/^/# /' /etc/hosts`
- 验证: `getent hosts <db-hostname>` 应返回真实内网 IP 而非 127.0.0.1
- 注意: 修改 /etc/hosts 需要 sudo；自动化 patch 工具通常拒绝写系统文件，必须用 terminal

## 7. Python 变量作用域: 全局集合的 `|=` 操作
- `CORRUPTED_TABLES |= auto_corrupted` 在 main() 函数内会报 UnboundLocalError
- Python 将 `|=` 视为赋值操作，使变量成为局部变量，但此时还未绑定
- 修复: 使用局部变量 `corrupted_tables = CORRUPTED_TABLES | auto_corrupted`，避免修改全局变量

## 9. all_col_comments 无 column_id
- `all_col_comments` 视图没有 `column_id` 列，ORDER BY column_id 会报 ORA-00904
- 必须与 `all_tab_columns` JOIN 来获取 column_id 排序
```sql
SELECT c.column_name, cc.comments, c.column_id
FROM all_tab_columns c
LEFT JOIN all_col_comments cc
  ON c.owner = cc.owner AND c.table_name = cc.table_name AND c.column_name = cc.column_name
WHERE c.owner = 'EDWCRM' AND c.table_name = 'TARGET_TABLE'
ORDER BY c.column_id;
```

## 10. S04_CRD_DBDKTZ 逾期相关字段多为空
- `DKYQYY` (贷款逾期原因) 几乎全为 NULL
- `SFYQS` (是否已起诉) 几乎全为 NULL/空
- 分析逾期时不要依赖这些字段，应改用 `YQCS`、`YQDKYE`、五级分类字段

## 11. F_CUST_LOAN_IFO 表为空
- 该贷款信息事实表没有数据，不要浪费时间查询
- 贷款明细请用 `S04_CRD_DBDKTZ`（台账级）或 `A_CUST_ANALYSYS_IFO`（客户级）

## 12. 逾期率的两种口径
- **客户逾期率**: YQCS > 0 的客户数 / 总客户数（历史口径，约 18.44%）
- **余额逾期率**: YQDKYE / DKYE（时点口径，约 0.37%）
- **五级分类不良率**: (次级+可疑+损失) / 总余额（最严格口径，约 0.09%）
- 用户问"逾期率"时必须澄清口径

## 13. 数据量统计
- Oracle: 212 表, 5817 字段, 51 主键, 0 外键, 46 索引
- 字典1: 58 表, 1633 字段
- 字典3: 34 表, 1113 字段
- 合并: 82 表, 2459 字段
