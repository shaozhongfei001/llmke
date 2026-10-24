package com.gientech.ragindexservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.SynLogDTO;
import com.gientech.ragindexservice.application.service.SynLogAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Tag(name = "文件解析或faq抽取异常日志")
@RestController
@RequestMapping("/synLog")
public class SynLogController {

    @Autowired
    private SynLogAppService synLogAppService;

    @Operation(summary = "分页查询异常日志")
    @GetMapping("/list")
    public Page<SynLogDTO> list(
            @RequestParam(value = "pageNo", required = false,defaultValue = "1") Long pageNo,
            @RequestParam(value = "pageSize", required = false,defaultValue = "10") Long pageSize,
            @RequestParam(value = "fileId") Long fileId
    ) {
        return synLogAppService.list(pageNo, pageSize,fileId);
    }


}
