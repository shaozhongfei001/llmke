package com.gientech.ragindexservice.infrastructure.serializer;

import com.alibaba.fastjson.serializer.JSONSerializer;
import com.alibaba.fastjson.serializer.ObjectSerializer;
import com.gientech.ragcommon.index.enmus.FaqTypeEnums;

import java.io.IOException;
import java.lang.reflect.Type;

/**
 * @author chenjuan
 * @date 2025/5/14 11:31
 */
public class FaqTypeEnumsSerializer implements ObjectSerializer {
    @Override
    public void write(JSONSerializer jsonSerializer, Object o, Object o1, Type type, int i) throws IOException {
        Integer faqType = (Integer) o;
        jsonSerializer.write(FaqTypeEnums.of(faqType));
    }
}
