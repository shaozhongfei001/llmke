package com.gientech.tools.database.domain.entity;

import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Date;

 /**
 * 数据库配置;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Builder
@AllArgsConstructor
@NoArgsConstructor
@Data
public class TLDatabase {
    private static final long serialVersionUID = 1L;
    /** 编号 */
    private Long id ;
    /** 数据库名称 */
    private String name ;
    /** 数据库描述 */
    private String description ;
     /** 数据源类型;DataTable数据表;DirectDB数据库直连; */
     private String datasourceType;
    /** 数据库类型;MySQL,SQLServer,Doris */
    private String dbType ;
    /** 连接地址 */
    private String dbHost ;
    /** 连接端口 */
    private Integer dbPort ;
    /** 数据库名称 */
    private String dbDatabase ;
    /** 连接用户 */
    private String dbUser ;
    /** 连接密码 */
    private String dbPassword ;
     /** jdbc连接地址 */
     private String jdbcUrl ;
     /** jdbc驱动类名 */
     private String jdbcDriverClass ;
    /** 创建时间 */
    private Date gmtCreate ;
    /** 更新时间 */
    private Date gmtModified ;
    /** 创建人 */
    private String createBy ;
    /** 更新人 */
    private String updateBy ;

}