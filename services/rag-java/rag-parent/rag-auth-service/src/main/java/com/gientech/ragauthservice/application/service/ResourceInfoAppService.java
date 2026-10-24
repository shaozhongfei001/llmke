package com.gientech.ragauthservice.application.service;

import com.gientech.ragauthservice.domain.entity.ResourceInfo;
import com.gientech.ragauthservice.interfaces.dto.ResourceInfoDTO;
import com.gientech.ragcommon.auth.dto.MenuDTO;
import com.gientech.ragcommon.auth.request.AddResourceReq;
import com.gientech.ragcommon.auth.request.UpdateResourceReq;

import java.awt.*;
import java.util.List;

public interface ResourceInfoAppService {

    Boolean addResource(AddResourceReq addResourceReq);

    Boolean deleteResource(Long resourceId);

    Boolean updateResource(UpdateResourceReq updateResourceReq);

    List<MenuDTO> getMenusByRole(Long roleId);

    List<MenuDTO> getMenusByUser();

    List<MenuDTO> getAllMenus();

    List<MenuDTO> getMenus();

    List<MenuDTO> listOperResources();
}
