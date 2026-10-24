package com.gientech.ragauthservice.interfaces;

import com.alibaba.excel.support.ExcelTypeEnum;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.DepartmentInfoAppService;
import com.gientech.ragcommon.auth.dto.DepartmentInfoDTO;
import com.gientech.ragcommon.auth.dto.DeptImportExportDTO;
import com.gientech.ragcommon.auth.dto.FrameElement;
import com.gientech.ragcommon.auth.dto.UserImportDTO;
import com.gientech.ragcommon.auth.request.CreateDepartmentInfoReq;
import com.gientech.ragcommon.auth.request.ListDepartmentInfoReq;
import com.gientech.ragcommon.auth.request.UpdateDepartmentInfoReq;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Locale;

@Tag(name = "部门")
@RestController
@RequestMapping("/departmentInfo")
public class DepartmentInfoController {

    @Autowired
    private DepartmentInfoAppService departmentInfoAppService;


    @Operation(summary = "新增部门")
    @PostMapping("/create")
    @OperationLog(operateType = "创建部门")
    public Boolean createDepartment(@RequestBody CreateDepartmentInfoReq departmentInfoReq) {
        return departmentInfoAppService.create(departmentInfoReq);
    }

    @Operation(summary = "编辑部门")
    @PostMapping("/edit")
    @OperationLog(operateType = "编辑部门")
    public Boolean editDepartment(@RequestBody UpdateDepartmentInfoReq updateDepartmentInfoReq) {
        return departmentInfoAppService.edit(updateDepartmentInfoReq);
    }

    @Operation(summary = "部门列表（分页查询）")
    @GetMapping("/list")
    @OperationLog(operateType = "查询部门列表")
    public Page<DepartmentInfoDTO> list(ListDepartmentInfoReq listDepartmentInfoReq) {
        return departmentInfoAppService.list(listDepartmentInfoReq);
    }


    @Operation(summary = "通过id查询数据")
    @GetMapping("{id}")
    public DepartmentInfoDTO queryDepartmentInfo(@PathVariable("id") Long id) {
        return departmentInfoAppService.findById(id);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("{id}")
    public Boolean deleteDepartmentInfoById(@PathVariable("id") Long id) {
        return departmentInfoAppService.deleteById(id);
    }

    @Operation(summary = "递归批量删除部门")
    @DeleteMapping("/recursiveDeleteByIds")
    public Boolean recursiveDeleteByIds(@RequestParam("ids") List<Long> ids) {
        return departmentInfoAppService.recursiveDeleteByIds(ids);
    }

    @Operation(summary = "组织架构模糊查询")
    @GetMapping("/frameSearch")
    @OperationLog(operateType = "查询部门列表")
    public List<FrameElement> frameSearch(ListDepartmentInfoReq listDepartmentInfoReq) {
        return departmentInfoAppService.frameSearch(listDepartmentInfoReq);
    }

    @Operation(summary = "获取组织架构树状列表")
    @GetMapping("/treeFrame")
    public List<FrameElement> treeFrame() {
        return departmentInfoAppService.treeFrame();
    }


    @Operation(summary = "获取树状的部门")
    @GetMapping("/treeDept")
    public List<FrameElement> treeDept(@RequestParam(value = "depth", required = false) Integer depth) {
        return departmentInfoAppService.treeDeptById(null, depth);
    }

    @Operation(summary = "根据部门id获取树状的部门（无用户）")
    @GetMapping("/treeDept/{deptId}")
    public List<FrameElement> treeDept(@PathVariable("deptId") Long deptId, @RequestParam(value = "depth", required = false) Integer depth) {
        return departmentInfoAppService.treeDeptById(deptId, depth);
    }


    @Operation(summary = "根据部门id获取树状的部门和用户")
    @GetMapping("/treeFrame/{deptId}")
    public List<FrameElement> treeFrame(@PathVariable("deptId") Long deptId) {
        return departmentInfoAppService.treeFrameByDeptId(deptId);
    }


    @Operation(summary = "部门导入模版下载")
    @GetMapping("/downloadTemplate")
    public void downloadTemplate(@RequestParam("fileType") String fileType, HttpServletResponse response) {
        departmentInfoAppService.downloadTemplate(ExcelTypeEnum.valueOf(fileType.toUpperCase(Locale.ROOT)), response);
    }

    @Operation(summary = "部门数据导入")
    @PostMapping("/import")
    public List<DeptImportExportDTO> userImport(@RequestParam("file") MultipartFile file) {
        return departmentInfoAppService.importData(file).getFailList();
    }

    @Operation(summary = "部门信息导出")
    @GetMapping("/export")
    public void export(@RequestParam(value = "pids", required = false) List<Long> pids, HttpServletResponse response) {
        departmentInfoAppService.export(pids, response);
    }

    @Operation(summary = "导出验证失败的部门数据")
    @GetMapping("/exportError")
    public void exportError(HttpServletResponse response) {
        departmentInfoAppService.exportError(response);
    }

}
