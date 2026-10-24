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
     * 文件多版本解析
     *
     * @param kbId
     * @param fileIds
     * @param multiversionParseEnums
     */
    void fileMultiversionParse(Long kbId, List<Long> fileIds, MultiversionParseEnums multiversionParseEnums,List<Integer> parseTypes);

    void fileMultiversionParse(Long kbId, List<Long> fileIds, MultiversionParseEnums multiversionParseEnums, List<Integer> parseTypes, boolean needAuth);
}
