package com.gientech.ragindexservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.gientech.ragindexservice.domain.entity.ModelInfo;
import com.gientech.ragindexservice.domain.model.ModelInfoDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;


/**
 * @Desc 模型管理 Mapper 接口
 * @Author ZhenPanHong
 * @Date 2025/3/5 13:33
 */
@Mapper
public interface ModelInfoMapper extends BaseMapper<ModelInfoDO> {

    /**
     * 自建和共享模型列表数据(分页)
     *
     * @param page
     * @param queryParam
     * @return
     */
    IPage<ModelInfoDO> allPage(IPage<ModelInfoDO> page, @Param("queryParam") ModelInfo queryParam);


    int updateCreator(@Param("ids") List<Long> ids, @Param("userName") String userName);
}