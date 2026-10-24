package com.gientech.ragauthservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.FrameElement;
import com.gientech.ragcommon.auth.dto.GroupDTO;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.request.*;

import java.util.List;

public interface GroupAppService {

    Boolean addGroup(AddGroupReq addGroupReq);

    Boolean updateGroup(UpdateGroupReq updateGroupReq);

    Boolean deleteGroup(Long id);

    Page<GroupDTO> list(SearchGroupReq searchGroupReq);

    Page<FrameElement> listFrameElements(GroupUserReq searchGroupReq);

    GroupDTO getGroupById(Long id);

    Page<UserInfoDTO> listGroupUsers(GroupUserReq groupUserReq);

    Boolean editGroupUsers(List<EditUserGroupReq> reqs);

    List<FrameElement> treeGroup();

    Boolean editGroupDepartments(List<EditDeptGroupReq> reqs);

    Boolean deleteGroupMembers(GroupQueryReq req);

    Boolean addGroupUsers(EditUserGroupReq req);
}
