package com.gientech.ragindexservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragindexservice.domain.model.BizLabelDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface BizLabelMapper extends BaseMapper<BizLabelDO> {
    int insertBatch(@Param("list") List<BizLabelDO> list);

    List<BizLabelDO> findHistoryOfKbLabel(@Param("kbId") Long kbId);

    List<BizLabelDO> findByKbNames(@Param("kbNames") List<String> kbNames);

    List<BizLabelDO> findLabelByFileIdsAndFolderIds(@Param("fileIds") List<Long> fileIds, @Param("folderIds") List<Long> folderIds);

    List<BizLabelDO> findLabelByTargetIds(@Param("targetIds") List<Long> targetIds);
}