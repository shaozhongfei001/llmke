package com.gientech.ragauthservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.InterfaceInfoAppService;
import com.gientech.ragcommon.auth.dto.InterfaceInfoDTO;
import com.gientech.ragcommon.auth.request.SaveInterfaceInfoReq;
import com.gientech.ragcommon.auth.request.UpdateInterfaceInfoReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "接口信息")
@RestController
@RequestMapping("/interface")
public class InterfaceInfoController {

    @Autowired
    private InterfaceInfoAppService interfaceInfoAppService;

    @Operation(summary = "分页查询")
    @GetMapping()
    public Page<InterfaceInfoDTO> list(@RequestParam(value = "pageNo", required = false) Long pageNo, @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return interfaceInfoAppService.list(pageNo, pageSize);
    }

    @Operation(summary = "分页查询")
    @GetMapping("/listExtInterfaces")
    public Page<InterfaceInfoDTO> listExtInterfaces(@RequestParam(value = "pageNo", required = false) Long pageNo, @RequestParam(value = "pageSize", required = false) Long pageSize, @RequestParam(value = "fuzzy", required = false) String fuzzy) {
        return interfaceInfoAppService.listExtInterfaces(pageNo, pageSize, fuzzy);
    }

    @Operation(summary = "通过id查询数据")
    @GetMapping("{id}")
    public InterfaceInfoDTO queryInterfaceInfo(@PathVariable("id") Long id) {
        return interfaceInfoAppService.findById(id);
    }

    @Operation(summary = "保存")
    @PostMapping()
    public Boolean saveInterfaceInfo(@RequestBody SaveInterfaceInfoReq interfaceInfoReq) {
        return interfaceInfoAppService.save(interfaceInfoReq);
    }

    @Operation(summary = "批量保存")
    @PostMapping("/saveBatch")
    public Boolean saveBatch(@RequestBody List<SaveInterfaceInfoReq> infoReqs) {
        return interfaceInfoAppService.saveBatch(infoReqs);
    }

    @Operation(summary = "通过id更新")
    @PutMapping()
    public Boolean updateInterfaceInfo(@RequestBody UpdateInterfaceInfoReq updateLogTestReq) {
        return interfaceInfoAppService.updateById(updateLogTestReq);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("{id}")
    public Boolean deleteInterfaceInfoById(@PathVariable("id") Long id) {
        return interfaceInfoAppService.deleteById(id);
    }
}
