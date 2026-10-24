package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.BizLabel;

import java.util.List;
import java.util.Map;

public interface BizLabelDomainService {

    BizLabel findById(Long id);

    Boolean save(BizLabel bizLabel);

    Boolean saveBatch(List<BizLabel> bizLabels);

    Boolean updateById(BizLabel bizLabel);

    Page<BizLabel> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    int deleteBatch(BizLabel bizLabel);

    List<BizLabel> findByTargetIds(List<Long> targetIds);

    List<String> findLabelsByTargetIds(List<Long> targetIds);

    List<BizLabel> findHistoryOfKbLabel(Long kbId);

    List<BizLabel> findByKbNames(List<String> kbNames);

    Map<String, String> findLabelByFileIdsAndFolderIds(List<Long> fileIds, List<Long> folderId);

    Map<String, String> findLabelMapByTargetIds(List<Long> targetIds);
}
