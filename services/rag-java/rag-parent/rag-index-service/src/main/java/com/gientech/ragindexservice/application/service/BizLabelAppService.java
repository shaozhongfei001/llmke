package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.index.dto.BizLabelDTO;
import com.gientech.ragcommon.index.request.SaveBizLabelReq;
import com.gientech.ragcommon.index.request.UpdateBizLabelReq;

import java.util.List;
import java.util.Set;

public interface BizLabelAppService {

    BizLabelDTO findById(Long id);

    Boolean save(SaveBizLabelReq bizLabelReq);

    Boolean updateById(UpdateBizLabelReq bizLabelReq);

    Page<BizLabelDTO> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    Set<BizLabelDTO> findAll(BizTypeEnums bizTypeEnum, Long targetId, String indexName);

    List<BizLabelDTO> findByTargetIds(List<Long> targetIds);

    List<BizLabelDTO> historyOfKbLabel(Long kbId);

    List<BizLabelDTO> findByKbNames(List<String> targetIds);

    List<String> findSuperiorLabel(BizTypeEnums bizTypeEnums, Long targetId);

    /**
     * 查询文件以及其文件夹的标签
     * @param kbId
     * @param fileId
     * @return
     */
    Set<String> findByFileId(Long kbId, Long fileId);

}
