package com.gientech.ragauthservice.application.helper;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.StrUtil;
import com.alibaba.fastjson2.JSON;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.RoleInfo;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.entity.UserRole;
import com.gientech.ragauthservice.domain.service.DepartmentInfoDomainService;
import com.gientech.ragauthservice.domain.service.RoleInfoDomainService;
import com.gientech.ragauthservice.domain.service.UserInfoDomainService;
import com.gientech.ragauthservice.domain.service.UserRoleDomainService;
import com.gientech.ragauthservice.infrastructure.contextHolder.UserImportFailListContextHolder;
import com.gientech.ragcommon.auth.dto.UserImportDTO;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums;
import com.gientech.start.easyexcel.template.BaseExcelService;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Component
public class UserImportHelper extends BaseExcelService<UserImportDTO> {

    @Autowired
    private UserInfoDomainService userInfoDomainService;

    @Autowired
    private UserRoleDomainService userRoleDomainService;

    @Autowired
    private DepartmentInfoDomainService departmentInfoDomainService;

    @Autowired
    private RoleInfoDomainService roleInfoDomainService;

    @Autowired
    private RedissonUtils redissonUtils;

    private final static Long USER_IMPORT_DATA_ERROR_EXPIRE = 3L;

    @Override
    protected void handlerSuccessList(List<UserImportDTO> list, Object... objects) {
        log.info("导入Excel中的数据为:{}",JSON.toJSONString(list));
        list = handleDept(list);
        list = handleRole(list);

        if (CollectionUtils.isEmpty(list))
            return;
        List<UserInfo> insertUsers = Lists.newArrayList();
        Map<String, UserImportDTO> userInfoMap = Maps.newHashMap();
        Iterator<UserImportDTO> iterator = list.iterator();
        while (iterator.hasNext()) {
            UserImportDTO userInfo = iterator.next();
            String userName = userInfo.getUserName();
            String userPhone = userInfo.getUserPhone();
            String userEmail = userInfo.getUserEmail();

            // 校验用户账号、手机号和邮箱是否已存在
            UserInfo dbUser = userInfoDomainService.getByUserName(userName);
            List<UserInfo> usersByPhoneOrEmail = userInfoDomainService.getByPhoneOrEmail(userPhone, userEmail);

            boolean isUserNameExists = Objects.nonNull(dbUser);
            boolean isPhoneExists = usersByPhoneOrEmail.stream().anyMatch(user -> userPhone.equals(user.getUserPhone()));
            boolean isEmailExists = usersByPhoneOrEmail.stream().anyMatch(user -> userEmail.equals(user.getUserEmail()));

            if (isUserNameExists)
                userInfo.setErrorMsg("该用户名已存在");
            else if (isPhoneExists)
                userInfo.setErrorMsg("该手机号已存在");
            else if (isEmailExists)
                userInfo.setErrorMsg("该邮箱已存在");

            if (isUserNameExists || isPhoneExists || isEmailExists) {
                UserImportFailListContextHolder.setUserImportFailList(userInfo);
                iterator.remove();
            } else {
                insertUsers.add(BeanUtil.copyProperties(userInfo, UserInfo.class));
                userInfoMap.put(userInfo.getUserName(), userInfo);
            }
        }

        if (CollectionUtils.isEmpty(insertUsers))
            return;
        //新增用户
        List<UserInfo> userInfoList = userInfoDomainService.addUsers(insertUsers);
        //新增角色
        List<UserRole> userRoles = Lists.newArrayList();
        userInfoList.forEach(userInfo -> {
            UserImportDTO user = userInfoMap.get(userInfo.getUserName());
            UserRole userRole = new UserRole();
            userRole.setUserId(userInfo.getId());
            userRole.setRoleId(user.getRoleId());
            userRoles.add(userRole);
        });
        userRoleDomainService.addUserRoles(userRoles);
    }

    @Override
    protected void handlerFailList(List<UserImportDTO> list, Object... objects) {
        UserImportFailListContextHolder.setUserImportFailList(list);
        List<UserImportDTO> userImportFailList = UserImportFailListContextHolder.getUserImportFailList();
        if (CollUtil.isNotEmpty(userImportFailList))
            saveUserToRedis(userImportFailList);
    }

    private void saveUserToRedis(List<UserImportDTO> havaExistUsers) {
        if(CollectionUtils.isEmpty(havaExistUsers))
            return;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        redissonUtils.set(RedisKeyEnums.USER_IMPORT_DATA_ERROR_PREFIX + userName, JSON.toJSONString(havaExistUsers), USER_IMPORT_DATA_ERROR_EXPIRE, TimeUnit.HOURS);
    }

    private List<UserImportDTO> handleDept(List<UserImportDTO> list) {
        if (CollUtil.isEmpty(list))
            return Lists.newArrayList();

        for (UserImportDTO userImportDTO : list) {
            String deptPath = userImportDTO.getDeptPath();
            if (StringUtils.isEmpty(deptPath)) {
                log.warn("用户【{}】的部门路径为空，跳过处理", userImportDTO.getUserName());
                continue;
            }
            // 解析部门路径并查找部门ID
            Long deptId = findDeptIdByPath(userImportDTO);
            if (deptId == null) {
                log.warn("用户【{}】的部门路径【{}】未找到对应的部门ID", userImportDTO.getUserName(), deptPath);
                continue;
            }
            // 设置部门ID和部门名称
            userImportDTO.setDeptId(deptId);
            userImportDTO.setDeptName(CollUtil.getLast(StrUtil.splitTrim(deptPath,"/")));
        }
        return list.stream().filter(userImportDTO -> Objects.nonNull(userImportDTO.getDeptId())).collect(Collectors.toList());
    }

    /**
     * 根据部门路径查找部门ID
     * @param userImportDTO 部门路径格式为
     *                      "中电金信/test11/test22"  或
     *                      "/中电金信/test11/test22" 或
     *                      "中电金信/test11/test22/" 或
     *                      "/中电金信/test11/test22/"
     * @return 部门ID，如果未找到则返回 null
     */
    private Long findDeptIdByPath(UserImportDTO userImportDTO) {
        String deptPath = userImportDTO.getDeptPath();
        Long parentId = null;

        for (String deptName : StrUtil.splitTrim(deptPath, "/")) {
            DepartmentInfo departmentInfo = departmentInfoDomainService.findByPidAndName(parentId, deptName);
            if (departmentInfo == null) {
                log.warn("部门【{}】未找到", deptName);
                userImportDTO.setErrorMsg("该部门不存在:" + deptName);
                UserImportFailListContextHolder.setUserImportFailList(userImportDTO);
                return null;
            }
            parentId = departmentInfo.getId();
        }
        return parentId;
    }

    private List<UserImportDTO> handleRole(List<UserImportDTO> list) {
        if (CollUtil.isEmpty(list))
            return Lists.newArrayList();

        for (UserImportDTO userImportDTO : list) {
            Long roleId = Optional.ofNullable(userImportDTO.getRoleName())
                    .map(roleInfoDomainService::queryByName)
                    .map(RoleInfo::getId)
                    .orElse(null);
            userImportDTO.setRoleId(roleId);
            if (Objects.isNull(roleId)) {
                userImportDTO.setErrorMsg("该角色不存在");
                UserImportFailListContextHolder.setUserImportFailList(userImportDTO);
            }
        }
        return list.stream().filter(userImportDTO -> Objects.nonNull(userImportDTO.getRoleId())).collect(Collectors.toList());
    }
}
