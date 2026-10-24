package com.gientech.ragindexservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.KbLabelHisDTO;
import com.gientech.ragcommon.index.request.SaveKbLabelHisReq;
import com.gientech.ragcommon.index.request.UpdateKbLabelHisReq;
import com.gientech.ragindexservice.application.service.KbLabelHisAppService;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/kbLabelHis")
public class KbLabelHisController {

    @Autowired
    private KbLabelHisAppService kbLabelHisAppService;

    @Operation(summary = "分页查询")
    @GetMapping()
    public Page<KbLabelHisDTO> list(@RequestParam(value = "pageNo", required = false) Long pageNo, @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return kbLabelHisAppService.list(pageNo, pageSize);
    }

    @Operation(summary = "通过id查询数据")
    @GetMapping("{id}")
    public KbLabelHisDTO queryKbLabelHis(@PathVariable("id") Long id) {
        return kbLabelHisAppService.findById(id);
    }

    @Operation(summary = "保存")
    @PostMapping()
    public Boolean saveKbLabelHis(@RequestBody SaveKbLabelHisReq kbLabelHisReq) {
        return kbLabelHisAppService.save(kbLabelHisReq);
    }

    @Operation(summary = "通过id更新")
    @PutMapping()
    public Boolean updateKbLabelHis(@RequestBody UpdateKbLabelHisReq updateLogTestReq) {
        return kbLabelHisAppService.updateById(updateLogTestReq);
    }
}
