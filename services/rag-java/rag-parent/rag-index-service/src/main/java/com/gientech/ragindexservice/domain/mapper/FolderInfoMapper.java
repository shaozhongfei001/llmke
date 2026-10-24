package com.gientech.ragindexservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragindexservice.domain.model.FolderInfoDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Set;

@Mapper
public interface FolderInfoMapper extends BaseMapper<FolderInfoDO> {
    List<FolderInfoDO> findParentIdsById(@Param("folderId") Long id);

    List<FolderInfoDO> findSubFolderById(@Param("folderId") Long id);

    List<FolderInfoDO> findParentIdsByIds(@Param("folderIds") List<Long> ids);

    void transferFolder(@Param("id") Long id, @Param("parentId") Long parentId);

    void transferFolderBatch(@Param("ids") List<Long> ids, @Param("parentId") Long parentId);

    List<FolderInfoDO> recursiveFolderByKb(@Param("kbId") Long kbId,
                                           @Param("type") Integer type,
                                           @Param("currentIds") Set<Long> currentIds,
                                           @Param("currentFileIds") Set<Long> currentFileIds);
}