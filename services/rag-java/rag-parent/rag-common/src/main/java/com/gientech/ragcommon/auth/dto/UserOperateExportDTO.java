package com.gientech.ragcommon.auth.dto;

import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.write.style.ColumnWidth;
import com.gientech.start.easyexcel.dto.BaseDTO;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.Date;

@EqualsAndHashCode(callSuper = true)
@Data
public class UserOperateExportDTO extends BaseDTO  {

    @ExcelProperty("方法名称")
    @ColumnWidth(25)
    private String name;

    @ExcelProperty("方法url")
    @ColumnWidth(100)
    private String url;

    @ExcelProperty("接口请求开始时间")
    @ColumnWidth(25)
    private Date startTime;

    @ExcelProperty("接口请求结束时间")
    @ColumnWidth(25)
    private Date endTime;

    @ExcelProperty("用户id")
    @ColumnWidth(10)
    private Long userId;

    @ExcelProperty("用户名称")
    @ColumnWidth(25)
    private String userName;

    @ExcelProperty("参数")
    @ColumnWidth(255)
    private String params;

    @ExcelProperty("ip")
    @ColumnWidth(20)
    private String ip;

    @ExcelProperty("接口是否请求成功")
    @ColumnWidth(10)
    private Integer success;

    @ExcelProperty("创建时间")
    @ColumnWidth(25)
    private Date gmtCreated;

    @ExcelProperty("更新时间")
    @ColumnWidth(25)
    private Date gmtModified;
}
