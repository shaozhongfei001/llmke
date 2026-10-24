package com.gientech.ragcommon.auth.dto;

import com.alibaba.excel.annotation.ExcelIgnore;
import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.write.style.ColumnWidth;
import com.gientech.start.easyexcel.dto.BaseDTO;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class DeptImportExportDTO extends BaseDTO {

    @ExcelProperty("部门名称")
    @NotBlank(message = "部门名称不能为空")
    @ColumnWidth(20)
    private String name;

    @ExcelProperty("部门人数")
    @ColumnWidth(20)
    private int userCount;

    @ExcelProperty("上级部门名称")
    @NotBlank(message = "上级部门名称不能为空")
    @ColumnWidth(20)
    private String parentDeptName;

    @ExcelIgnore
    private Long parentId;

}
