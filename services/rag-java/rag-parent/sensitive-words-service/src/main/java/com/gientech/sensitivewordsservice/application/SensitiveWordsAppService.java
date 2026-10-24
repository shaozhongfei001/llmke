package com.gientech.sensitivewordsservice.application;

import com.gientech.ragcommon.sensitive.request.HitSensitiveWordRequest;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;

import java.util.LinkedHashSet;

public interface SensitiveWordsAppService {


    /**
     * 根据词库id改动内部的敏感词
     *
     * @param libraryId 词库id
     * @param words     敏感词列表
     * @return 成功/失败
     */
    Boolean updateSensitiveWords(Long libraryId, LinkedHashSet<String> words);


    /**
     * 根据词库id批量导入敏感词
     *
     * @param libraryId 词库id
     * @param file      敏感词列表文件 .csv  .txt
     * @return 成功/失败
     */
    Boolean importSensitiveWords(Long libraryId, MultipartFile file);

    /**
     * 敏感词模板下载
     *
     * @param fileType
     * @return
     * @throws Exception
     */
    ResponseEntity<InputStreamResource> downloadTemplate(String fileType) throws Exception;


    Boolean checkHitSensitiveWord(HitSensitiveWordRequest wordRequest);
}
