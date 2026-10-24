package com.gientech.ragauthservice.utils;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.generator.FastAutoGenerator;
import com.baomidou.mybatisplus.generator.config.OutputFile;
import com.baomidou.mybatisplus.generator.config.rules.DbColumnType;
import com.baomidou.mybatisplus.generator.config.rules.NamingStrategy;
import com.baomidou.mybatisplus.generator.engine.VelocityTemplateEngine;

import java.sql.Types;
import java.util.Collections;

public class CodeGenerator {

    public static void main(String[] args) {
        String outDir = System.getProperty("user.dir") + "/rag-parent/rag-index-service";
        String parent = "com.gientech.ragindexservice";
        FastAutoGenerator
                // 数据源配置
                .create("jdbc:mysql://10.64.7.145:3306/gienrag?serverTimezone=Asia/Shanghai&useSSL=true&useUnicode=true&characterEncoding=utf8&allowPublicKeyRetrieval=true",
                        "root",
                        "Gientech!2024")
                // 全局配置
                .globalConfig(builder -> {
                    builder.author("wudf")                // 设置作者
                            .outputDir(outDir + "/src/main/java") // 指定输出目录
                            .commentDate("yyyy-MM-dd")   // 注释日期
                            .disableOpenDir();           // 禁止打开输出目录，默认:true
                })
                .dataSourceConfig(builder -> builder.typeConvertHandler((globalConfig, typeRegistry, metaInfo) -> {
                    int typeCode = metaInfo.getJdbcType().TYPE_CODE;
                    if (typeCode == Types.TIMESTAMP) {
                        return DbColumnType.DATE;
                    }
                    return typeRegistry.getColumnType(metaInfo);

                }))
                // 包配置
                .packageConfig(builder -> {
                    builder.parent(parent) // 设置父包名
                            //.moduleName("mp")          // 设置父包模块名
                            .entity("domain.model")
                            .mapper("domain.mapper")
                            .service("domain.service")
                            .serviceImpl("domain.service.impl")
                            .controller("interfaces")
                            .pathInfo(Collections.singletonMap(OutputFile.xml, outDir + "/src/main/resources/mapper")); // 设置mapperXml生成路径
                })
                // 策略配置
                .strategyConfig((scanner, builder) -> {
                    builder.addInclude(scanner.apply("请输入表名，使用英文的逗号分隔：")) // 设置需要生成的表名
                            .addTablePrefix("t_", "c_") // 设置过滤表前缀

                            // entity 策略配置
                            .entityBuilder().enableFileOverride()
                            .formatFileName("%sDO")
                            .idType(IdType.AUTO)
                            .enableLombok()
                            //.logicDeleteColumnName("deleted")                 //逻辑删除字段名
                            .naming(NamingStrategy.underline_to_camel)          //数据库表映射到实体的命名策略：下划线转驼峰命
                            .columnNaming(NamingStrategy.underline_to_camel)    //数据库表字段映射到实体的命名策略：下划线转驼峰命
//                            .addTableFills(
//                                    new Column("gmt_create", FieldFill.INSERT),
//                                    new Column("gmt_modified", FieldFill.INSERT_UPDATE)
//                            )   //添加表字段填充，"gmt_create"字段自动填充为插入时间，"gmt_modified"字段自动填充为插入修改时间
                            .enableTableFieldAnnotation()                       // 开启生成实体时生成字段注解
                            // mapper 策略配置
                            .mapperBuilder().enableFileOverride()
                            .superClass(BaseMapper.class)       //设置父类
                            .formatMapperFileName("%sMapper")   //格式化 mapper 文件名称
                            .enableMapperAnnotation()           //开启 @Mapper 注解
                            .formatXmlFileName("%sMapper")      //格式化 Xml 文件名称 如 UserXml
                            .enableBaseColumnList()             //生成通用查询结果列
                            .enableBaseResultMap()              //生成查询映射结果ResultMap

                            // service 策略配置
                            .serviceBuilder().enableFileOverride()
                            .formatServiceFileName("%sDomainService")         // 如:UserService
                            .formatServiceImplFileName("%sDomainServiceImpl") // 如:UserServiceImpl

                            // controller 策略配置
                            .controllerBuilder().enableFileOverride()
                            .formatFileName("%sController")     // 如 UserController
                            .enableRestStyle();                 //开启生成 @RestController 控制器

                })
                // 模板配置
                .templateEngine(new VelocityTemplateEngine()) // 使用Freemarker引擎模板，默认的是Velocity引擎模板
                // 执行
                .execute();
    }
}
