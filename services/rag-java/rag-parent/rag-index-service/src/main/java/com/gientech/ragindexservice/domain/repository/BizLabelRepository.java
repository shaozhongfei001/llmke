package com.gientech.ragindexservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.ragindexservice.domain.entity.BizLabel;
import com.gientech.ragindexservice.domain.model.BizLabelDO;

import java.util.List;

public interface BizLabelRepository extends IService<BizLabelDO> {

    BizLabel findById(Long id);

    Boolean save(BizLabel bizLabel);

    Boolean updateById(BizLabel bizLabel);

    Page<BizLabel> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    int deleteBatch(BizLabel bizLabel);

    List<BizLabel> findByTargetIds(List<Long> targetIds);

    List<BizLabel> findHistoryOfKbLabel(Long kbId);

    List<BizLabel> findByKbNames(List<String> kbNames);

    List<BizLabel> findLabelByFileIdsAndFolderIds(List<Long> fileIds, List<Long> folderIds);

    List<BizLabel> findLabelByTargetIds(List<Long> targetIds);
}
