package com.gientech.ragindexservice.domain.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.excel.util.StringUtils;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.BizLabel;
import com.gientech.ragindexservice.domain.model.BizLabelDO;
import com.gientech.ragindexservice.domain.repository.BizLabelRepository;
import com.gientech.ragindexservice.domain.repository.KnowledgeBaseListRepository;
import com.gientech.ragindexservice.domain.service.BizLabelDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class BizLabelDomainServiceImpl implements BizLabelDomainService {

    @Autowired
    private BizLabelRepository bizLabelRepository;

    @Autowired
    private KnowledgeBaseListRepository knowledgeBaseListRepository;

    @Override
    public BizLabel findById(Long id) {
        return bizLabelRepository.findById(id);
    }

    @Override
    public Boolean save(BizLabel bizLabel) {
        return bizLabelRepository.save(bizLabel);
    }

    @Override
    public Boolean saveBatch(List<BizLabel> bizLabels) {
        if (CollectionUtils.isEmpty(bizLabels)) {
            return Boolean.TRUE;
        }
        BizLabel existedLabel = BizLabel.builder().bizType(bizLabels.get(0).getBizType()).targetId(bizLabels.get(0).getTargetId()).build();
        deleteBatch(existedLabel);
        List<BizLabelDO> bizLabelDOS = BeanUtil.copyToList(bizLabels, BizLabelDO.class);
        return bizLabelRepository.saveBatch(bizLabelDOS);
    }

    @Override
    public Boolean updateById(BizLabel bizLabel) {
        return bizLabelRepository.updateById(bizLabel);
    }

    @Override
    public Page<BizLabel> list(Long pageNo, Long pageSize) {
        return bizLabelRepository.list(pageNo, pageSize);
    }

    @Override
    public Boolean deleteById(Long id) {
        return bizLabelRepository.deleteById(id);
    }

    @Override
    public int deleteBatch(BizLabel bizLabel) {
        return bizLabelRepository.deleteBatch(bizLabel);
    }

    @Override
    public List<BizLabel> findByTargetIds(List<Long> targetIds) {
        return bizLabelRepository.findByTargetIds(targetIds);
    }

    @Override
    public List<String> findLabelsByTargetIds(List<Long> targetIds) {
        List<BizLabel> byTargetIds = bizLabelRepository.findByTargetIds(targetIds);
        return byTargetIds.stream().map(BizLabel::getLabel).toList();
    }

    @Override
    public List<BizLabel> findHistoryOfKbLabel(Long kbId) {
        return bizLabelRepository.findHistoryOfKbLabel(kbId);
    }

    @Override
    public List<BizLabel> findByKbNames(List<String> kbNames) {
        return bizLabelRepository.findByKbNames(kbNames);
    }

    @Override
    public Map<String, String> findLabelByFileIdsAndFolderIds(List<Long> fileIds, List<Long> folderIds) {

        return bizLabelRepository.findLabelByFileIdsAndFolderIds(fileIds, folderIds).stream()
                .filter(i -> StringUtils.isNotBlank(i.getLabel()))
                .collect(Collectors.toMap(BizLabel::getIdStr, BizLabel::getLabel, (v1, v2) -> v1));
    }

    @Override
    public Map<String, String> findLabelMapByTargetIds(List<Long> targetIds) {
        return bizLabelRepository.findLabelByTargetIds(targetIds).stream()
                .filter(i -> StringUtils.isNotBlank(i.getLabel()))
                .collect(Collectors.toMap(BizLabel::getIdStr, BizLabel::getLabel, (v1, v2) -> v1));
    }
}
