package com.gientech.tools.database.domain.mapper;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.tools.database.domain.entity.TLTable;
import com.gientech.tools.database.domain.model.TLTableDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 数据表信息;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Mapper
public interface TLTableMapper extends BaseMapper<TLTableDO>  {
    @Select("SELECT tf.*,(select status from tools_table_file ttf where ttf.table_id = tf.id order by ttf.gmt_create desc limit 1) as parse_status " +
            "FROM tools_table tf ${ew.customSqlSegment}")
    Page<TLTable> queryPage(Page<TLTableDO> page, @Param(Constants.WRAPPER) Wrapper<TLTableDO> queryWrapper);
}
