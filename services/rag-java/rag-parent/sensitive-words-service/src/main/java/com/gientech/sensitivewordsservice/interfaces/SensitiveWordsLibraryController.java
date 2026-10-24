package com.gientech.sensitivewordsservice.interfaces;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.sensitive.dto.SensitiveWordsDTO;
import com.gientech.sensitivewordsservice.application.SensitiveWordsLibraryAppService;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.interfaces.request.SensitiveWordLibraryCreateRequest;
import com.gientech.sensitivewordsservice.interfaces.request.SensitiveWordLibraryUpdateRequest;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Min;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;

/**
 * 敏感词词库操作：  新增、删除、修改、查询详情、分页查询列表
 *
 * @author wxc
 * @since 2024-08-13
 */
@Tag(name = "敏感词词库-接口")
@RestController
@RequestMapping("/library")
public class SensitiveWordsLibraryController {


    @Autowired
    private SensitiveWordsLibraryAppService sensitiveWordsLibraryAppService;

    @Operation(summary = "新增敏感词词库")
    @PostMapping()
    @OperationLog(operateType = "创建敏感词库")
    public Long createSensitiveWordsLibrary(@Validated @RequestBody SensitiveWordLibraryCreateRequest request) {
        SensitiveWords sensitiveWords = BeanUtil.copyProperties(request, SensitiveWords.class);
        return sensitiveWordsLibraryAppService.createWordsLibrary(sensitiveWords);
    }

    @Operation(summary = "删除敏感词词库")
    @DeleteMapping("/{id}")
    @OperationLog(operateType = "删除敏感词库")
    public Boolean deleteSensitiveWordsLibrary(@Parameter(name = "id", description = "敏感词词库id", required = true)
                                                               @PathVariable("id") Long id) {
        return sensitiveWordsLibraryAppService.deleteWordsLibrary(id);
    }

    @Operation(summary = "修改敏感词词库")
    @PutMapping("/{id}")
    @OperationLog(operateType = "修改敏感词库")
    public SensitiveWordsDTO updateSensitiveWordsLibrary(@Parameter(name = "id", description = "敏感词词库id", required = true)
                                                                         @PathVariable("id") Long id,
                                                                         @Validated @RequestBody SensitiveWordLibraryUpdateRequest request) {
        SensitiveWords sensitiveWords = BeanUtil.copyProperties(request, SensitiveWords.class);
        sensitiveWords.setId(id);
        sensitiveWords = sensitiveWordsLibraryAppService.updateWordsLibraryById(sensitiveWords);
        return BeanUtil.copyProperties(sensitiveWords, SensitiveWordsDTO.class);
    }

    @Operation(summary = "敏感词词库详情查询")
    @GetMapping("/{id}")
    @OperationLog(operateType = "查询敏感词库")
    public SensitiveWordsDTO querySensitiveWordsLibrary(@Parameter(name = "id", description = "敏感词词库id", required = true)
                                                                        @PathVariable("id") Long id,
                                                        @RequestParam(value = "start",defaultValue = "0",required = false) Integer start,
                                                        @RequestParam(value = "end",defaultValue = "300",required = false) Integer end
     ) {
        SensitiveWords sensitiveWords = sensitiveWordsLibraryAppService.queryWordsLibraryById(id,start,end);
        return  BeanUtil.copyProperties(sensitiveWords, SensitiveWordsDTO.class);
    }


    @Operation(summary = "分页查询敏感词词库列表")
    @GetMapping()
    public Page<SensitiveWordsDTO> pageQuery(
                                                             @Parameter(name = "name", description = "敏感词词库名称,用于模糊匹配")
                                                             @RequestParam(value = "name", required = false) String name,
                                                             @Parameter(name = "ids", description = "id列表字符串，多个用英文，分割")
                                                             @RequestParam(value = "ids", required = false) String ids,
                                                             @Parameter(name = "pageNo", description = "第几页")
                                                             @Min(value = 1, message = "页码不能小于1")
                                                             @RequestParam(value = "pageNo", required = false, defaultValue = "1") Integer pageNo,
                                                             @Parameter(name = "pageSize", description = "每页大小")
                                                             @Min(value = 1, message = "每页大小不能小于1")
                                                             @RequestParam(value = "pageSize", required = false, defaultValue = "10") Integer pageSize) {

        List<Long> numberList = new ArrayList<>();
        if (StringUtils.isNotBlank(ids)) {
            String[] numberStrings = ids.split(",");
            // 遍历字符串数组并转换为Long类型
            for (String numberString : numberStrings) {
                numberList.add(Long.parseLong(numberString.trim()));
            }
        }
        Page<SensitiveWords> pageSensitiveWords = sensitiveWordsLibraryAppService.pageQuery(name,numberList, pageNo, pageSize);
        Page<SensitiveWordsDTO> pageResult = new Page<>();
        BeanUtil.copyProperties(pageSensitiveWords, pageResult);
        //设置敏感词词汇结果
        List<SensitiveWords> records = pageSensitiveWords.getRecords();
        for (SensitiveWords sensitiveWords : records) {
            sensitiveWords.setTotalCount();
            sensitiveWords.wordCountLimit(20);
        }
        pageResult.setRecords(BeanUtil.copyToList(records, SensitiveWordsDTO.class));
        return pageResult;
    }


    @Operation(summary = "根据id获取敏感词库列表")
    @GetMapping("/getListByIds")
    public List<SensitiveWordsDTO> getListByIds(@RequestParam("ids") Long[] ids) {
        return sensitiveWordsLibraryAppService.getListByIds(ids);
    }

}
