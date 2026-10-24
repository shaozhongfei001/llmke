package com.gientech.start.easyexcel.dto;

import java.io.Serializable;

/** Excel 导入导出 DTO 基类（R12 兼容实现）。 */
public class BaseDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 行级错误信息（导入校验失败时回填） */
    private String errorMsg;

    public String getErrorMsg() {
        return errorMsg;
    }

    public void setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
    }
}
