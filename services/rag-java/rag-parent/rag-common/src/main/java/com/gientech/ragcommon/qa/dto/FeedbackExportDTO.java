package com.gientech.ragcommon.qa.dto;

import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.write.style.ColumnWidth;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.gientech.start.easyexcel.dto.BaseDTO;
import lombok.Data;

import java.util.Date;

@Data
public class FeedbackExportDTO extends BaseDTO {

    @ExcelProperty("用户名称")
    @ColumnWidth(20)
    private String userName;

    @ExcelProperty("问题类型")
    @ColumnWidth(20)
    private String issueType;

    @ExcelProperty("补充说明")
    @ColumnWidth(25)
    private String supplementExplain;

    @ExcelProperty("理想回答")
    @ColumnWidth(25)
    private String idealAnswer;

    @ExcelProperty("部门")
    @ColumnWidth(20)
    private String deptName;

    @ExcelProperty("联系方式")
    @ColumnWidth(20)
    private String userPhone;

    @ExcelProperty("助手名称")
    @ColumnWidth(20)
    private String configName;

    @ExcelProperty("问题和回答")
    @ColumnWidth(100)
    private String questionsAndAnswers;

    @ExcelProperty("上下文")
    @ColumnWidth(100)
    private String context;

    @ExcelProperty("反馈时间")
    @ColumnWidth(20)
    private Date gmtCreate;

}
