package com.gientech.ragindexservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.application.service.BizLabelAppService;
import com.gientech.ragcommon.index.dto.BizLabelDTO;
import com.gientech.ragcommon.index.request.QueryBizLabelReq;
import com.gientech.ragcommon.index.request.SaveBizLabelReq;
import com.gientech.ragcommon.index.request.UpdateBizLabelReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.CollectionUtils;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "知识库分层接口")
@RestController
@RequestMapping("/bizLabel")
public class BizLabelController {

    @Autowired
    private BizLabelAppService bizLabelAppService;

    @Operation(summary = "分页查询")
    @GetMapping()
    public Page<BizLabelDTO> list(@RequestParam(value = "pageNo", required = false) Long pageNo, @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return bizLabelAppService.list(pageNo, pageSize);
    }

    @Operation(summary = "通过id查询数据")
    @GetMapping("{id}")
    public BizLabelDTO queryBizLabel(@PathVariable("id") Long id) {
        return bizLabelAppService.findById(id);
    }

    @Operation(summary = "保存")
    @PostMapping()
    public Boolean saveBizLabel(@RequestBody @Valid SaveBizLabelReq bizLabelReq) {
        return bizLabelAppService.save(bizLabelReq);
    }

    @Operation(summary = "通过id更新")
    @PutMapping()
    public Boolean updateBizLabel(@RequestBody UpdateBizLabelReq updateLogTestReq) {
        return bizLabelAppService.updateById(updateLogTestReq);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("{id}")
    public Boolean deleteBizLabelById(@PathVariable("id") Long id) {
        return bizLabelAppService.deleteById(id);
    }

    @Operation(summary = "根据kbNames获取标签列表")
    @PostMapping("/labels")
    public List<BizLabelDTO> getLabelsByKbNames(@RequestBody QueryBizLabelReq queryBizLabelReq) {
        if (CollectionUtils.isEmpty(queryBizLabelReq.getKbNames())) {
            return List.of();
        }
        return bizLabelAppService.findByKbNames(queryBizLabelReq.getKbNames());
    }

    @Operation(summary = "获取知识库历史标签列表")
    @GetMapping("/historyOfKbLabel")
    public List<BizLabelDTO> historyOfKbLabel(@RequestParam("kbId") Long kbId) {
        return bizLabelAppService.historyOfKbLabel(kbId);
    }
}
