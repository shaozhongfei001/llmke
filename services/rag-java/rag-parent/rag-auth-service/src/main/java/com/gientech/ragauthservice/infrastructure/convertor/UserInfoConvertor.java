package com.gientech.ragauthservice.infrastructure.convertor;

import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragcommon.auth.dto.FrameElement;
import com.gientech.ragcommon.auth.dto.SimpleUserDTO;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.ArrayList;
import java.util.List;

@Mapper
public interface UserInfoConvertor {
    UserInfoConvertor INSTANCE = Mappers.getMapper(UserInfoConvertor.class);

    default List<SimpleUserDTO> userInfoS2SimpleUsers(List<UserInfo> userInfoS) {
        if (userInfoS == null) {
            return null;
        }

        List<SimpleUserDTO> list = new ArrayList<SimpleUserDTO>(userInfoS.size());
        for (UserInfo userInfo : userInfoS) {
            list.add(userInfoToSimpleUserDTO(userInfo));
        }

        return list;
    }

    default List<FrameElement> userInfoS2FrameElements(List<UserInfo> userInfoS) {
        if (userInfoS == null) {
            return null;
        }

        List<FrameElement> list = new ArrayList<FrameElement>(userInfoS.size());
        for (UserInfo userInfo : userInfoS) {
            list.add(userInfo2FrameElement(userInfo));
        }

        return list;
    }

    default FrameElement userInfo2FrameElement(UserInfo userInfo) {
        if (userInfo == null) {
            return null;
        }

        FrameElement.FrameElementBuilder frameElement = FrameElement.builder();

        frameElement.id(userInfo.getId());
        frameElement.userName(userInfo.getUserName());
        frameElement.userRealname(userInfo.getUserRealname());
        frameElement.userEmail(userInfo.getUserEmail());
        frameElement.empNo(userInfo.getEmpNo());
        frameElement.deptName(userInfo.getDeptName());

        return frameElement.build();
    }

    private SimpleUserDTO userInfoToSimpleUserDTO(UserInfo userInfo) {
        if (userInfo == null) {
            return null;
        }

        SimpleUserDTO simpleUserDTO = new SimpleUserDTO();

        simpleUserDTO.setUserName(userInfo.getUserName());
        simpleUserDTO.setUserRealname(userInfo.getUserRealname());
        simpleUserDTO.setUserEmail(userInfo.getUserEmail());
        simpleUserDTO.setId(userInfo.getId());

        return simpleUserDTO;
    }
}
