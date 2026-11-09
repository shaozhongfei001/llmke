package com.gientech.ragindexservice.application.service;

import com.gientech.ragcommon.index.enmus.MultiversionParseEnums;
import com.gientech.ragcommon.index.parameter.FileParseTaskInfo;
import com.gientech.ragindexservice.domain.entity.FileParseTask;
import org.springframework.scheduling.annotation.Async;

import java.util.List;

public interface FileAppService {

    /**
     * 文件解析
     *
     * @param task
     */
    void filesParse(FileParseTask task);

    /**
     * 文件解析(同步的方式)
     * @param param
     */
    void filesParseSync(FileParseTaskInfo param);

    /**
     * faq抽取
     *
     * @param param
     */
    @Async
    void faqExtract(FileParseTaskInfo param);

    /**
     * 图数据生成
     *
     * @param param
     */
    void generateGraph(FileParseTaskInfo param);

    /**
     * V2 摄取：解析完成后把**同一份解析快照**双路消费（搜索 chunk + 按库建图）。
     *
     * 与 legacy generateGraph 的区别：legacy 走 19529 从 ES 取正文（另一份解析），
     * V2 只用 doc2md 的四件套，保证搜索与图谱读的是同一次解析。
     * doc2md 产物缺失时跳过并告警，不拿 legacy 正文冒充。
     *
     * @param param 解析任务信息（需带 doc2mdDir）
     */
    @Async
    void v2Ingest(FileParseTaskInfo param);

    /**
     * 文件多版本解析
     *
     * @param kbId
     * @param fileIds
     * @param multiversionParseEnums
     */
    void fileMultiversionParse(Long kbId, List<Long> fileIds, MultiversionParseEnums multiversionParseEnums,List<Integer> parseTypes);

    void fileMultiversionParse(Long kbId, List<Long> fileIds, MultiversionParseEnums multiversionParseEnums, List<Integer> parseTypes, boolean needAuth);
}
