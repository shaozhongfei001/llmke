package com.gientech.ragauthservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.ResourceInterfaceAppService;
import com.gientech.ragcommon.auth.dto.ResourceInterfaceDTO;
import com.gientech.ragcommon.auth.request.SaveResourceInterfaceReq;
import com.gientech.ragcommon.auth.request.UpdateResourceInterfaceReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Tag(name = "权限接口关联")
@RestController
@RequestMapping("/resourceInterface")
public class ResourceInterfaceController {

    @Autowired
    private ResourceInterfaceAppService resourceInterfaceAppService;

    @Operation(summary = "分页查询")
    @GetMapping()
    public Page<ResourceInterfaceDTO> list(@RequestParam(value = "pageNo", required = false) Long pageNo, @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return resourceInterfaceAppService.list(pageNo, pageSize);
    }

    @Operation(summary = "通过id查询数据")
    @GetMapping("{id}")
    public ResourceInterfaceDTO queryResourceInterface(@PathVariable("id") Long id) {
        return resourceInterfaceAppService.findById(id);
    }

    @Operation(summary = "保存")
    @PostMapping()
    public Boolean saveResourceInterface(@RequestBody SaveResourceInterfaceReq resourceInterfaceReq) {
        return resourceInterfaceAppService.save(resourceInterfaceReq);
    }

    @Operation(summary = "通过id更新")
    @PutMapping()
    public Boolean updateResourceInterface(@RequestBody UpdateResourceInterfaceReq updateLogTestReq) {
        return resourceInterfaceAppService.updateById(updateLogTestReq);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("{id}")
    public Boolean deleteResourceInterfaceById(@PathVariable("id") Long id) {
        return resourceInterfaceAppService.deleteById(id);
    }
}
