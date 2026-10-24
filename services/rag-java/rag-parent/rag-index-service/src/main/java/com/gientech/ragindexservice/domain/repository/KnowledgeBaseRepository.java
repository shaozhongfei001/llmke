package com.gientech.ragindexservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;

import java.util.List;

public interface KnowledgeBaseRepository {

    KnowledgeBase findByKbName(String kbName, String userName);

    KnowledgeBase findByKbName(String kbName, String userName, String platform);

    KnowledgeBase findById(Long id);

    Long addKnowledgeBase(KnowledgeBase knowledgeBase);

    int updateById(KnowledgeBase knowledgeBase);

    Page<KnowledgeBase> list(List<Long> kbIds, String fuzzy, Long pageNo, Long pageSize, String userName, String platform, boolean isSuperAdmin, Integer privateKb);

    Page<KnowledgeBase> availableList(List<Long> kbIds, Long pageNo, Long pageSize);

    KnowledgeBase findByPrimitiveName(String primitiveName, String userName);

    KnowledgeBase findByPrimitiveName(String primitiveName, String userName, String platform);

    Integer getHighestPermission(Long kbId, Long deptId, Long userId, String userName);

    int transferProperty(String owner, String userName);

    List<KnowledgeBase> findByPrimitiveNames(List<String> primitiveNames);

    int replaceModel(String sourceModelName, String targetModelName);

    List<KnowledgeBase> selectUseSpecifiedModelKbList(String modelTypeName, String modelName);

    int selectReferenceByModelName(String modelName);
}
