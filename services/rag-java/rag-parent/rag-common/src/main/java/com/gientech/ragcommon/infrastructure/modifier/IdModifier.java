package com.gientech.ragcommon.infrastructure.modifier;

import com.fasterxml.jackson.databind.BeanDescription;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.SerializationConfig;
import com.fasterxml.jackson.databind.ser.BeanPropertyWriter;
import com.fasterxml.jackson.databind.ser.BeanSerializerModifier;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;

import java.util.List;
import java.util.regex.Pattern;

/**
 * @author: shirleychen
 * @date 2025/9/24 19:18
 * @description
 */
public class IdModifier extends BeanSerializerModifier {

    // 两个正则：大小写敏感
    private static final Pattern ID_LOWER = Pattern.compile(".*id.*");
    private static final Pattern ID_UPPER = Pattern.compile(".*Id.*");

    @Override
    public List<BeanPropertyWriter> changeProperties(
            SerializationConfig config,
            BeanDescription beanDesc,
            List<BeanPropertyWriter> beanProperties) {

        for (BeanPropertyWriter writer : beanProperties) {
            String name = writer.getName();
            JavaType type = writer.getType();

            // 判断字段名匹配正则且类型是 Long
            if ((ID_LOWER.matcher(name).matches() || ID_UPPER.matcher(name).matches())
                    && type.getRawClass() == Long.class) {
                if (!(writer.getSerializer() instanceof ToStringSerializer)) {
                    writer.assignSerializer(ToStringSerializer.instance);
                }
            }
        }
        return beanProperties;
    }
}
