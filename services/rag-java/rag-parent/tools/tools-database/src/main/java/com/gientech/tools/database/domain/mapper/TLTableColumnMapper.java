package com.gientech.tools.database.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.tools.database.domain.model.TLTableColumnDO;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 数据表-字段信息;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-8-8
 */
@Mapper
public interface TLTableColumnMapper extends BaseMapper<TLTableColumnDO>  {
    @Insert("<script>" +
            "insert into tools_table_column (database_id, table_id, business_name, physical_name, description, data_type, " +
            "gmt_create, gmt_modified, create_by, update_by) values " +
            "<foreach collection='list' item='item' separator=','>" +
            "(#{item.databaseId}, #{item.tableId}, #{item.businessName}, #{item.physicalName}, " +
            "#{item.description}, #{item.dataType}, #{item.gmtCreate}, #{item.gmtModified}, " +
            "#{item.createBy}, #{item.updateBy})" +
            "</foreach>" +
            "</script>")
    int batchInsert(@Param("list") List<TLTableColumnDO> tlTableColumnDOList);
}
