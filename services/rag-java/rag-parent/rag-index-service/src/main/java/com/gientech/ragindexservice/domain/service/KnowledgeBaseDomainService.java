package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.KnowledgeBaseDTO;
import com.gientech.ragcommon.index.request.KnowledgeBaseCreateReq;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;

import java.util.List;

/**
 * <p>
 * 知识库 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
public interface KnowledgeBaseDomainService {

    KnowledgeBase addKnowledgeBase(KnowledgeBase knowledgeBase);

    KnowledgeBase findByKbName(String kbName, String userName);

    KnowledgeBase findByKbName(String kbName, String userName, String platform);

    KnowledgeBase findByPrimitiveName(String primitiveName, String userName);

    KnowledgeBase findByPrimitiveName(String primitiveName, String userName, String platform);

    int deleteById(Long id);

    Page<KnowledgeBase> list(List<Long> kbIds, String fuzzy, Long pageNo, Long pageSize, String userName, String platform, boolean isSuperAdmin, Integer privateKb);

    Page<KnowledgeBase> availableList(List<Long> kbIds, Long pageNo, Long pageSize);

    int updateById(KnowledgeBase knowledgeBase);

    KnowledgeBase findByKbId(Long kbId);

    Integer getHighestPermission(Long kbId);

    String queryCreator(Long id);

    Boolean transferProperty(String owner, String receiver);

    List<KnowledgeBase> findByPrimitiveNames(List<String> primitiveNames);

    KnowledgeBaseDTO createKb(KnowledgeBaseCreateReq kbReq);

    Boolean replaceModel(String sourceModelName, String targetModelName);

    List<KnowledgeBase> selectUseSpecifiedModelKbList(String modelTypeName, String modelName);

    int selectReferenceByModelName(String modelName);
}
