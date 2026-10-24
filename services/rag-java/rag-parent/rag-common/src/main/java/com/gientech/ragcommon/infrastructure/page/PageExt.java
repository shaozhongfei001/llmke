package com.gientech.ragcommon.infrastructure.page;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

public class PageExt<T> extends Page {
    private Integer pdfPages;

    private Integer failTotal;

    public Integer getPdfPages() {
        return pdfPages;
    }

    public Integer getFailTotal() {
        return failTotal;
    }

    public void setFailTotal(Integer failTotal) {
        this.failTotal = failTotal;
    }

    public void setPdfPages(Integer pdfPages) {
        this.pdfPages = pdfPages;
    }
}
