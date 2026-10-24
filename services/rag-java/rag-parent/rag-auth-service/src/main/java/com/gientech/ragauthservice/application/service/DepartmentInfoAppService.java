package com.gientech.ragauthservice.application.service;

import com.alibaba.excel.support.ExcelTypeEnum;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.DepartmentInfoDTO;
import com.gientech.ragcommon.auth.dto.DeptImportExportDTO;
import com.gientech.ragcommon.auth.dto.FrameElement;
import com.gientech.ragcommon.auth.request.CreateDepartmentInfoReq;
import com.gientech.ragcommon.auth.request.ListDepartmentInfoReq;
import com.gientech.ragcommon.auth.request.UpdateDepartmentInfoReq;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.start.easyexcel.dto.BaseDTO;
import com.gientech.start.easyexcel.result.ExcelImportResult;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.multipart.MultipartFile;

import java.awt.*;
import java.util.List;

public interface DepartmentInfoAppService {

    DepartmentInfoDTO findById(Long id) throws ApplicationException;

    Boolean create(CreateDepartmentInfoReq departmentInfoReq) throws ApplicationException;

    Boolean edit(UpdateDepartmentInfoReq departmentInfoReq) throws ApplicationException;

    Page<DepartmentInfoDTO> list(ListDepartmentInfoReq listDepartmentInfoReq) throws ApplicationException;

    Boolean deleteById(Long id) throws ApplicationException;

    Boolean recursiveDeleteByIds(List<Long> ids) throws ApplicationException;

    List<FrameElement> frameSearch(ListDepartmentInfoReq listDepartmentInfoReq);

    List<FrameElement> treeFrame();

    List<FrameElement> treeFrameByDeptId(Long deptId);

    List<FrameElement> treeFrameByDeptIds(List<Long> deptIds);

    List<FrameElement> treeDeptById(Long deptId, Integer depth);

    void downloadTemplate(ExcelTypeEnum valueOf, HttpServletResponse response);

    ExcelImportResult<DeptImportExportDTO> importData(MultipartFile file);

    void export(List<Long> pids, HttpServletResponse response);

    void exportError(HttpServletResponse response);
}
