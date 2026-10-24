package com.gientech.tools.database.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.tools.database.domain.model.TLTableFileDO;
import org.apache.ibatis.annotations.Mapper;

/**
 * 数据表-上传文件表;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Mapper
public interface TLTableFileMapper extends BaseMapper<TLTableFileDO>  {
}
