package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.Collaborator;
import com.gientech.ragcommon.index.dto.KnowledgeBaseDTO;
import com.gientech.ragcommon.index.request.KbConfUpdateReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseCreateReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseQueryReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseUpdateReq;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;

import java.util.List;
import java.util.Set;

/**
 *
 * 知识库 服务类
 * @author wudf
 * @since 2024-06-04
 */

public interface KnowledgeBaseAppService {

    /**
     * 添加知识库
     *
     * @param kbReq
     * @return
     */
    KnowledgeBaseDTO createKb(KnowledgeBaseCreateReq kbReq);

    /**
     * 通过id删除
     *
     * @param id
     * @return
     */
    Boolean deleteById(Long id);

    /**
     * 分页查询数据
     *
     * @param knowledgeBaseQueryReq
     * @return
     */
    Page<KnowledgeBaseDTO> list(KnowledgeBaseQueryReq knowledgeBaseQueryReq);

    /**
     * 修改
     *
     * @param knowledgeBaseUpdateReq
     * @return
     */
    Boolean update(KnowledgeBaseUpdateReq knowledgeBaseUpdateReq);

    /**
     * 通过id查询知识库信息
     *
     * @param id
     * @return
     */
    KnowledgeBaseDTO getKbById(Long id);

    /**
     * 共享知识库列表
     *
     * @param knowledgeBaseQueryReq
     * @return
     */
    Page<KnowledgeBaseDTO> shareList(KnowledgeBaseQueryReq knowledgeBaseQueryReq);

    /**
     * 所有知识库数据(用户自己的知识库 + 共享数据的知识库)
     *
     * @param fuzzy
     * @return
     */
    Set<KnowledgeBaseDTO> searchList(String fuzzy, String userName, String platform);

    Set<KnowledgeBaseDTO> searchList(String fuzzy, String userName, String platform, String scope);

    /**
     * 更新知识库解析配置
     *
     * @param updateConf
     * @return
     */
    Boolean updateConf(KbConfUpdateReq updateConf);

    /**
     * 更新知识库解析配置
     *
     * @param kbId 知识库id
     * @return
     */
    Boolean canUpdateConf(Long kbId);

    /**
     * 根据旧知识库重建新知识库并解析所有原知识库文档
     *
     * @param id
     * @return
     */
    KnowledgeBaseDTO rebuildNew(Long id);

    /**
     * 重新解析所有知识库文档
     *
     * @param id
     * @return
     */
    Boolean reParse(Long id);

    /**
     * 下载知识库所有文档
     *
     * @param id
     * @return
     */
    Boolean downloadKbFiles(Long id);

    /**
     * 文件解析模型列表
     *
     * @return
     */
//    List<KbEmbeddingModelDTO> getEmbeddingModels();


    Integer getKbHighestPermission(Long kbId);


    List<Collaborator> getCollaborators(Long kbId);

    /**
     * 通过知识库名查询
     *
     * @param primitiveName
     * @return
     */
    KnowledgeBaseDTO getKbByPrimitiveName(String primitiveName);

    /**
     * 查询知识库创建者
     *
     * @param id
     * @return
     */
    String queryCreator(Long id);


    Boolean transferProperty(String owner, String receiver);

//    List<KbParseTypeDTO> getParseTypes();

    Boolean replaceModel(String taskUUID, String modelType, String sourceModelName, String targetModelName);

    List<KnowledgeBase> selectUseSpecifiedModelKbList(String modelTypeName, String modelName);

    int selectReferenceByModelName(String modelName);
}