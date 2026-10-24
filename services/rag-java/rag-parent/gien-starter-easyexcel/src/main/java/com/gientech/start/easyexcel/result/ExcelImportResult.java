package com.gientech.start.easyexcel.result;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/** 导入结果（R12 兼容实现）。 */
@Data
public class ExcelImportResult<T> {

    private List<T> successList = new ArrayList<>();

    private List<T> failList = new ArrayList<>();

    private int total;

    public int getSuccessCount() {
        return successList == null ? 0 : successList.size();
    }

    public int getFailCount() {
        return failList == null ? 0 : failList.size();
    }

    public boolean isSuccess() {
        return getFailCount() == 0;
    }
}
