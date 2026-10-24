package com.gientech.ragauthservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.InterfaceInfoDTO;
import com.gientech.ragcommon.auth.request.SaveInterfaceInfoReq;
import com.gientech.ragcommon.auth.request.UpdateInterfaceInfoReq;

import java.util.List;

public interface InterfaceInfoAppService {

    InterfaceInfoDTO findById(Long id);

    Boolean save(SaveInterfaceInfoReq interfaceInfoReq);

    Boolean updateById(UpdateInterfaceInfoReq interfaceInfoReq);

    Page<InterfaceInfoDTO> list(Long pageNo, Long pageSize);

    Page<InterfaceInfoDTO> listExtInterfaces(Long pageNo, Long pageSize, String fuzzy);

    Boolean deleteById(Long id);

    Boolean saveBatch(List<SaveInterfaceInfoReq> infoReqs);
}
