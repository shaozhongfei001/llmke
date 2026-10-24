package com.gientech.tools.database.infrastructure.util;

import com.gientech.tools.database.infrastructure.enums.DatabaseTypeEnum;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import javax.sql.DataSource;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * JDBC 工具类;
 *
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-14
 */
public class JdbcUtil {

    /**
     * 常见数据库的 JDBC URL 模板
     */
    public static Map<String, String> jdbcUrlTemplate = new HashMap<>() {{
        put("MySQL", "jdbc:mysql://{host}:{port}/{database}?useSSL=false&serverTimezone=UTC&characterEncoding=UTF-8");
        put("PostgreSQL", "jdbc:postgresql://{host}:{port}/{database}?currentSchema={schema}&sslmode=disable");
        put("SQLServer", "jdbc:sqlserver://{host}:{port};databaseName={database};encrypt=true;trustServerCertificate=true");
        put("Doris", "jdbc:mysql://{host}:{port}/{database}?useSSL=false&serverTimezone=UTC&characterEncoding=UTF-8");

    }};

    /**
     * 根据数据库类型，获取jdbcUrl
     * @param databaseTypeEnum
     * @return
     */
    public static String getJdbcUrlTemplate(DatabaseTypeEnum databaseTypeEnum) {
        String code = databaseTypeEnum.getCode();
        String jdbcUrl = jdbcUrlTemplate.get(code);
        return jdbcUrl;
    }

    /**
     * jdbc url地址填充变量
     * 例如：
     * jdbc:mysql://{host}:{port}/{database}
     * 转化为
     * jdbc:mysql://127.0.0.1:3306/test
     *
     * 传入参数
     * Map<String, Object> params = new HashMap<>();
     * params.put("host", "localhost");
     * params.put("port", 3306);
     * params.put("database", "mydb");
     * @param template
     * @param params
     * @return
     */
    public static String jdbcUrlConver(String template, Map<String, Object> params) {
        Pattern pattern = Pattern.compile("\\{(.*?)\\}");
        Matcher matcher = pattern.matcher(template);

        StringBuffer buffer = new StringBuffer();
        while (matcher.find()) {
            String key = matcher.group(1);
            Object value = params.get(key);
            if (value != null) {
                matcher.appendReplacement(buffer, value.toString());
            }
        }
        matcher.appendTail(buffer);
        return buffer.toString();
    }

    /**
     * jdbc url地址填充变量
     * @param databaseTypeEnum
     * @param params
     * @return
     */
    public static String jdbcUrlConver(DatabaseTypeEnum databaseTypeEnum, Map<String, Object> params) {
        String jdbcUrlTempl = getJdbcUrlTemplate(databaseTypeEnum);
        return jdbcUrlConver(jdbcUrlTempl, params);
    }


    /**
     * 构建数据库连接数据源
     */
    public static DataSource buildDataSource(String jdbcUrl, String dbUser, String dbPassword){
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(jdbcUrl);
        config.setUsername(dbUser);
        config.setPassword(dbPassword);
        config.setMaximumPoolSize(10);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);

        DataSource dataSource = new HikariDataSource(config);
        return dataSource;
    }
}
