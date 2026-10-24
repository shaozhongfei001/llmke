package com.gientech.tools.database.domain.entity;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Date;

 /**
 * 数据表信息;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Builder
@AllArgsConstructor
@NoArgsConstructor
@Data
public class TLTable {
    private static final long serialVersionUID = 1L;
     /** 编号 */
     private Long id ;
     /** 数据库编号 */
     private Long databaseId ;
     /** 业务表名 */
     private String businessName ;
     /** 物理表名 */
     private String physicalName ;
     /** 表描述 */
     private String description ;
     /** 列数量 */
     private Integer columnCount ;
     /** 行数量 */
     private Long rowCount ;
     /** 解析状态 */
     private String parseStatus;
     /** 创建时间 */
     private Date gmtCreate ;
     /** 更新时间 */
     private Date gmtModified ;
     /** 创建人 */
     private String createBy ;
     /** 更新人 */
     private String updateBy ;

     private Boolean isGenDesc;

     private String genDescErrMsg;

     private String genDescStatus;

}