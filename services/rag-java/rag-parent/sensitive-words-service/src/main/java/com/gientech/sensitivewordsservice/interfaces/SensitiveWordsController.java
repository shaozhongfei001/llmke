package com.gientech.sensitivewordsservice.interfaces;

import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.sensitive.request.HitSensitiveWordRequest;
import com.gientech.sensitivewordsservice.application.SensitiveWordsAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.LinkedHashSet;

/**
 * 敏感词手动操作： （增、删） 都是修改敏感词库 words 字段
 * 敏感词批量导入： 导入.csv/.txt文件。内部换行为一个敏感词，写入到敏感词库的 words 字段
 *
 * @author wxc
 * @since 2024-08-13
 */
@Tag(name = "敏感词接口--敏感词具有顺序性、唯一性")
@RestController
@RequestMapping("/word")
public class SensitiveWordsController {

    @Autowired
    private SensitiveWordsAppService sensitiveWordsAppService;


    @Operation(summary = "根据词库id增、删敏感词,请保证敏感词原顺序")
    @PutMapping("/{libraryId}")
    @OperationLog(operateType = "编辑敏感词库")
    public Boolean updateSensitiveWords(@Parameter(name = "libraryId", description = "敏感词词库id", required = true)
                                        @PathVariable("libraryId") Long libraryId,
                                        @RequestBody LinkedHashSet<String> words) {
        return sensitiveWordsAppService.updateSensitiveWords(libraryId, words);
    }


    @Operation(summary = "根据词库id导入敏感词文件 .csv/.txt 一行一个词",
            description = "上传一个文件，批量导入敏感词。请确保使用 multipart/form-data 格式发送请求"
    )
    @PutMapping(value = "/{libraryId}/import", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @OperationLog(operateType = "导入敏感词库")
    public Boolean importSensitiveWords(@Parameter(name = "libraryId", description = "敏感词词库id", required = true)
                                        @PathVariable("libraryId") Long libraryId,
                                        @Parameter(name = "file", description = "敏感词文件.csv/.txt", required = true)
                                        @RequestPart("file") MultipartFile file) {
        return sensitiveWordsAppService.importSensitiveWords(libraryId, file);
    }

    @Operation(summary = "模板下载")
    @GetMapping("/downloadTemplate")
    @OperationLog(operateType = "下载敏感词模版文件")
    public ResponseEntity<InputStreamResource> downloadTemplate(@RequestParam("fileType") String fileType) throws Exception {
        return sensitiveWordsAppService.downloadTemplate(fileType);
    }

    @Operation(summary = "是否命中敏感词")
    @PostMapping("/checkHitSensitiveWord")
    public Boolean checkHitSensitiveWord(@RequestBody HitSensitiveWordRequest wordRequest) {
        return sensitiveWordsAppService.checkHitSensitiveWord(wordRequest);
    }


}
