# 验收矩阵 U01-U16

时间 2026-11-04，被测 /chats/knowledgeBase/9。构建 dist-kgw-final（3m6s，0 错误）。
- U02 PASS 真实137实体114边
- U03 PASS 业务名+类型色系
- U04 PASS 搜索定位+详情+相机
- U05 PARTIAL 有向谓词真实，边级证据后端未提供
- U06 PARTIAL 真实来源可跳转，无权场景未测
- U07 PASS 取消21类型后0/137+空态，重置恢复
- U08 PASS 35个真实算法社区
- U09 PARTIAL 跨文档用多来源title判断（简化）
- U10 PASS question_re 真实问答+引用，诚实回答缺失
- U11 PARTIAL 重建确认已实现，构建状态接口待接
- U12 PARTIAL loading/error/empty 已呈现
- U13 NOT_RUN 切库/切代延迟响应未做受控测试
- U14 PASS 平移/缩放/适配/全屏/ /聚焦/Esc关闭
- U15 PASS 1024画布906宽，390画布272宽，均无横向滚动
- U16 PASS 知识解析10行/FAQ正常；构建3m6s 0错误

## 真实后端缺口
- 实体稳定ID/别名缺失（vid=业务名）
- 边级证据无接口
- chunk级原文高亮缺position坐标
- 社区仅编号c-1无名称；source_meta为F合成ID
- /v2/build、/v2/fence 构建接口未接线

## 回退方法
git checkout -- src/components/KnowledgeBaseZh/Detail.tsx src/components/KnowledgeBaseZh/GraphCanvas.tsx src/const/knowledgebase.ts vite.config.ts
删除 v2/GraphWorkbench.tsx GraphCanvasV2.tsx graphData.ts workbench.less KnowledgeGraphView.tsx knowledge-graph.less 即回到改造前
