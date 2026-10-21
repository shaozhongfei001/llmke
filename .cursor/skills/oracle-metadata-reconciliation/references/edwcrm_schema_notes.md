# EDWCRM Schema Domain Notes

> Domain knowledge discovered during data analysis sessions on an example EDWCRM-style schema (Oracle, host=<db-host>, service_name=<service-name>).
> 仅作为核对流程示范；连接真实环境时以本地 .env 为准，真实主机/服务名不得提交。

---

## 1. Loan Product Type Codes (YWPZ in S04_CRD_DBDKTZ)

| YWPZ Code | Loan Type | Balance (亿元, approx) |
|---|---|---|
| 010001 | 一般贷款 | 556.4 |
| 010006 | **小本贷款** | 166.7 |
| 010002 | (其他) | 41.5 |
| 010010 | (自助卡等) | 16.1 |
| 010003 | (大额) | 12.0 |
| 010011 | (消费信贷) | 1.4 |
| 010005 | (其他) | 1.0 |

- YWPZ is the primary discriminator for loan product type in S04_CRD_DBDKTZ (信贷担保贷款台账)
- 010006 = 小本贷款 is the most common filter for small business loan analysis

---

## 2. Key Tables for Loan Analysis

### A_CUST_ANALYSYS_IFO (客户分析主表)
- One row per customer, covers all loan types
- Contains: SLOAN_BAL (小本余额), LOAN_OVER_AMT (逾期总额), LOAN_OVER_NUM (逾期笔数), LOAN_OVER_MM (最长逾期月数)
- Also has CRC (信用卡) fields, deposit fields, asset fields
- Total customers with SLOAN_BAL > 0: ~132万

### A_CUST_SMALL_CAP_LOAN (小本贷款客户表)
- Dedicated small business loan customer table
- Key overdue field: **YQCS** (逾期次数, integer)
- Also has: SLOAN_BAL, CRC_OVER_BAL, CRC_OVER_RATE
- Total customers: ~131.8万

### S04_CRD_DBDKTZ (信贷担保贷款台账)
- **Loan-level (借据级) detail**, one row per loan/borrow
- YWPZ distinguishes product type (see above)
- Key overdue fields:
  - YQCS (逾期次数)
  - YQDKYE (逾期贷款余额)
  - DKJLXYQCS (贷款及利息逾期次数)
  - DKYQYY (贷款逾期原因) — **mostly NULL, not useful**
  - SFYQS (是否已起诉) — **mostly NULL/empty, not useful**
- Five-category classification fields:
  - WJFLGZ (关注余额), WJFLCJ (次级余额), WJFLKY (可疑余额), WJFLSS (损失余额)
- Other balance fields: ZCDKYE (正常), DZDKYE (呆滞), DZHANGDKYE (呆账)
- DKXZ (贷款性质): 1=normal, 2/3=other
- DKZL (贷款种类): 11=most common for 小本贷款
- Total records: ~386万

### DM_XBD_CUST_ANALYSYS (小本客户分析维度表)
- Analysis-ready dimension table for small business loan customers
- Rich attributes: AGE, SEX, CREDITGRADE, CUSTGRADE, IS_FIRST_LOAN, IS_LOSS, IS_CHG_MGR
- Overdue: YQCS (逾期次数), YQCS_SEG (逾期次数分段)
- Loan: SLOAN_BAL, LOAN_BAL, SLOAN_AVG_M/Q/Y, LAST_LRATE, CONTINUE_LN_CNT, TQHD_CNT
- Deposit: DEP_BAL, CUR_DEP_BAL, DEP_AVG_M/Q/Y
- Credit card: CRC_OVER_BAL, CRC_OVER_RATE, CRC_SX_AMT, CRC_YX_RATIO
- Asset: ZCYE, ZC_AVG_M/Q/Y
- Behavioral: BANK_NUM, THHD_NUM, SIGN_NUM, ELC_TRAN_AMT/NUM
- Query/credit: NMONTH_SNUM, NYEAR_SNUM
- Total records: ~84万 (active small business loan customers)

### Related tables
- DM_XBD_CUST_ANALYSYS_C — copy/variant
- DM_XBD_CUST_ANALYSYS_RN1 — RN1 variant
- DM_XBD_CUST_LOSS — loss analysis (has YQCS_SEG)
- DM_XBD_CUST_SCORE — scoring (has YQCS_SEG)
- DM_XBD_CUST_SCORE_RESULT — scoring result (has YQCS)
- F_CUST_LOAN_IFO — loan info fact table (**empty/no data**)
- F_CUST_CRC_IFO — credit card info
- F_XBD_CUSTINFO — XBD customer info (has YQCS)

---

## 3. Overdue Rate Interpretations

**Two very different metrics, must not be confused:**

| Metric | Definition | Value (小本贷款) |
|---|---|---|
| Customer overdue rate | % of customers who EVER had overdue records (YQCS > 0) | **18.44%** |
| Balance overdue rate | Current overdue balance / total loan balance (from S04) | **0.37%** |
| NPL rate (五级分类不良率) | (次级+可疑+损失) / total balance | **0.09%** |

- Customer overdue rate is a **historical** metric — once a customer has YQCS > 0, they stay flagged
- Balance overdue rate is a **point-in-time** snapshot of actual overdue amounts
- Always clarify which metric the user means

---

## 4. Overdue Analysis Key Findings

### Customer profile differences (overdue vs normal)
- Overdue customers have **53% lower deposits** (1.51万 vs 2.82万)
- Overdue customers have **53% lower assets** (1.52万 vs 2.84万)
- First-loan customer share is **higher** in overdue group (18.87% vs 12.24%)
- Customer churn rate is **higher** in overdue group (58.16% vs 40.37%)
- Overdue customers are slightly younger (40.7 vs 41.6 years)
- No significant difference in financing bank count or credit card overdraft

### Five-category distribution (S04, YWPZ=010006)
- 正常: 99.69%, 关注: 0.22%, 次级: 0.07%, 可疑: 0.01%, 损失: 0.01%
- Total NPL (次级+可疑+损失): ~1.52亿元

### Overdue frequency distribution
- 逾期1次: 9.89% of customers, 10.17% of balance
- 逾期2-3次: 5.54%, 5.32% of balance
- 逾期4-6次: 2.04%, 1.78% of balance
- 逾期7-12次: 0.92%, 0.62% of balance
- 逾期12次以上: 0.05%, 0.04% of balance
- More overdue → lower per-customer balance (high-frequency overdue customers tend to have smaller loans)

---

## 5. SQL Pitfalls for EDWCRM Queries

### all_col_comments lacks column_id
```sql
-- WRONG: column_id not in all_col_comments
SELECT column_name, comments FROM all_col_comments ORDER BY column_id;

-- CORRECT: join with all_tab_columns for ordering
SELECT c.column_name, cc.comments, c.column_id
FROM all_tab_columns c
LEFT JOIN all_col_comments cc ON c.owner = cc.owner AND c.table_name = cc.table_name AND c.column_name = cc.column_name
WHERE c.owner = 'EDWCRM' AND c.table_name = 'S04_CRD_DBDKTZ'
ORDER BY c.column_id;
```

### DEL_IND filter
Many tables have DEL_IND (delete indicator). Always filter:
```sql
WHERE DEL_IND IS NULL OR DEL_IND != '1'
```

### IFS_ prefix tables have corrupted comments
7 tables with IFS_ prefix have permanently corrupted comments due to ZHS16GBK charset migration. These are auto-filtered by the reconciliation script.

### Empty fact tables
F_CUST_LOAN_IFO is empty — don't waste queries on it. Use S04_CRD_DBDKTZ instead.

### Sparse fields
In S04_CRD_DBDKTZ: DKYQYY (逾期原因), SFYQS (是否已起诉) are almost entirely NULL. Don't rely on them for analysis.

---

## 6. Quick Reference: Common Loan Balance Queries

```sql
-- Total loan balances by product type (from A_CUST_ANALYSYS_IFO)
SELECT
    ROUND(SUM(GLOAN_BAL)/10000,2) AS 一般贷款_万元,
    ROUND(SUM(SLOAN_BAL)/10000,2) AS 小本贷款_万元,
    ROUND(SUM(ZZDK_BAL)/10000,2) AS 自助卡_万元,
    ROUND(SUM(BL_LOAN_BAL)/10000,2) AS 不良_万元,
    ROUND(SUM(XFXD_BAL)/10000,2) AS 消费信贷_万元,
    ROUND(SUM(XNK_BAL)/10000,2) AS 兴农卡_万元,
    ROUND(SUM(XYD_BAL)/10000,2) AS 薪易贷_万元
FROM EDWCRM.A_CUST_ANALYSYS_IFO;

-- Small business loan overdue from S04 ledger
SELECT
    COUNT(*) AS 笔数,
    SUM(DKYE) AS 贷款余额,
    SUM(YQDKYE) AS 逾期余额,
    SUM(WJFLGZ) AS 关注,
    SUM(WJFLCJ) AS 次级,
    SUM(WJFLKY) AS 可疑,
    SUM(WJFLSS) AS 损失
FROM EDWCRM.S04_CRD_DBDKTZ
WHERE YWPZ = '010006'
  AND (DEL_IND IS NULL OR DEL_IND != '1');
```
