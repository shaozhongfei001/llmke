package com.gientech.ragauthservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import com.gientech.ragauthservice.application.service.UserOperateAppService;
import com.gientech.ragcommon.auth.dto.UserOperateDTO;
import com.gientech.ragcommon.auth.request.SaveUserOperateReq;
import com.gientech.ragcommon.auth.request.UpdateUserOperateReq;
import com.gientech.ragcommon.auth.request.UserOperateQueryReq;
import com.gientech.ragcommon.infrastructure.page.PageExt;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletResponse;

@RestController
@RequestMapping("/userOperate")
public class UserOperateController {

    @Autowired
    private UserOperateAppService userOperateAppService;

    @Operation(summary = "分页查询")
    @GetMapping()
    public PageExt<UserOperateDTO> list(UserOperateQueryReq queryReq) {
        return userOperateAppService.list(queryReq);
    }

    @Operation(summary = "通过id查询数据")
    @GetMapping("{id}")
    public UserOperateDTO queryUserOperate(@PathVariable("id") Long id) {
        return userOperateAppService.findById(id);
    }

    @Operation(summary = "保存")
    @PostMapping()
    public Boolean saveUserOperate(@RequestBody SaveUserOperateReq userOperateReq) {
        return userOperateAppService.save(userOperateReq);
    }

    @Operation(summary = "通过id更新")
    @PutMapping()
    public Boolean updateUserOperate(@RequestBody UpdateUserOperateReq updateLogTestReq) {
        return userOperateAppService.updateById(updateLogTestReq);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("{id}")
    public Boolean deleteUserOperateById(@PathVariable("id") Long id) {
        return userOperateAppService.deleteById(id);
    }


    @Operation(summary = "导出")
    @GetMapping("/export")
    public void exportUserOperate(@RequestParam(value = "fuzzy", required = false) String fuzzy,
                                  @RequestParam(value = "start", required = false) String start,
                                  @RequestParam(value = "end", required = false) String end,
                                  HttpServletResponse response) {
        userOperateAppService.exportUserOperate(fuzzy, start, end, response);
    }
}
