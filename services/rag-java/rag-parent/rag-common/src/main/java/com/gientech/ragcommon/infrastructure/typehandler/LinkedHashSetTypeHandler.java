package com.gientech.ragcommon.infrastructure.typehandler;

import com.alibaba.excel.util.StringUtils;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedTypes;

import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Objects;

@MappedTypes(LinkedHashSet.class)
public class LinkedHashSetTypeHandler extends BaseTypeHandler<LinkedHashSet<String>> {

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, LinkedHashSet<String> parameter, JdbcType jdbcType) throws SQLException {
        if (Objects.nonNull(parameter)) {
            ps.setString(i, String.join(",", parameter));
        } else {
            ps.setNull(i, jdbcType.TYPE_CODE);
        }
    }

    @Override
    public LinkedHashSet<String> getNullableResult(ResultSet rs, String columnName) throws SQLException {
        String value = rs.getString(columnName);
        if (Objects.nonNull(value) && StringUtils.isNotBlank(value)) {
            return new LinkedHashSet<>(Arrays.asList(value.split(",")));
        }
        return new LinkedHashSet<>();
    }

    @Override
    public LinkedHashSet<String> getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        String value = rs.getString(columnIndex);
        if (Objects.nonNull(value)  && StringUtils.isNotBlank(value)) {
            return new LinkedHashSet<>(Arrays.asList(value.split(",")));
        }
        return new LinkedHashSet<>();
    }

    @Override
    public LinkedHashSet<String> getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        String value = cs.getString(columnIndex);
        if (Objects.nonNull(value)  && StringUtils.isNotBlank(value)) {
            return new LinkedHashSet<>(Arrays.asList(value.split(",")));
        }
        return new LinkedHashSet<>();
    }
}
