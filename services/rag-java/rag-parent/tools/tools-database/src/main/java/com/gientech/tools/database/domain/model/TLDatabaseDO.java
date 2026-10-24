package com.gientech.tools.database.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.TableId;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.io.Serializable;
import java.util.Date;

 /**
 * 数据库配置;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("tools_database")
public class TLDatabaseDO implements Serializable,Cloneable{
    /** 编号 */
    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键", isKey = true, isAutoIncrement = true)
    private Long id ;
    
    /** 数据库名称 */
    @Column(name = "name", comment = "数据库名称", length = 100)
    private String name ;
    
    /** 数据库描述 */
    @Column(name = "description", comment = "数据库描述", length = 500)
    private String description ;
    
    /** 数据源类型;DataTable数据表;DirectDB数据库直连; */
    @Column(name = "datasource_type", comment = "数据源类型", length = 32)
    private String datasourceType;
    
    /** 数据库类型;MySQL,SQLServer,Doris */
    @Column(name = "db_type", comment = "数据库类型", length = 32)
    private String dbType ;
    
    /** 连接地址 */
    @Column(name = "db_host", comment = "连接地址", length = 255)
    private String dbHost ;
    
    /** 连接端口 */
    @Column(name = "db_port", comment = "连接端口")
    private Integer dbPort ;
    
    /** 数据库名称 */
    @Column(name = "db_database", comment = "数据库名称", length = 100)
    private String dbDatabase ;
    
    /** 连接用户 */
    @Column(name = "db_user", comment = "连接用户", length = 100)
    private String dbUser ;
    
    /** 连接密码 */
    @Column(name = "db_password", comment = "连接密码", length = 255)
    private String dbPassword ;

     /** jdbc连接地址 */
     @Column(name = "jdbc_url", comment = "jdbc连接地址", length = 500)
     private String jdbcUrl ;

     /** jdbc驱动类名 */
     @Column(name = "jdbc_driver_class", comment = "jdbc驱动类名", length = 255)
     private String jdbcDriverClass ;
    
    /** 创建时间 */
    @Column(name = "gmt_create", comment = "创建时间")
    private Date gmtCreate ;
    
    /** 更新时间 */
    @Column(name = "gmt_modified", comment = "更新时间")
    private Date gmtModified ;
    
    /** 创建人 */
    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy ;
    
    /** 更新人 */
    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy ;
    

}