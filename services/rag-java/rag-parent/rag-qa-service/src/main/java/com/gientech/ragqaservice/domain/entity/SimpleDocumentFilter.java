package com.gientech.ragqaservice.domain.entity;

import com.alibaba.fastjson2.filter.PropertyFilter;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/27 14:03
 */
public class SimpleDocumentFilter implements PropertyFilter {
    @Override
    public boolean apply(Object o, String s, Object o1) {
        if ("page_content".equals(s) || "order_num".equals(s)) {
            return true;
        }
        return false;
    }

    public static SimpleDocumentFilter getDefault(){
        return new SimpleDocumentFilter();
    }
}
