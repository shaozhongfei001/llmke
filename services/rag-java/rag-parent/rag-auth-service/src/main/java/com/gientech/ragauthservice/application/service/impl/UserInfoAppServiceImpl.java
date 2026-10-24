package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.core.date.DateUnit;
import cn.hutool.core.date.DateUtil;
import cn.hutool.core.util.StrUtil;
import com.alibaba.excel.support.ExcelTypeEnum;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.helper.UserExportHelper;
import com.gientech.ragauthservice.application.helper.UserImportHelper;
import com.gientech.ragauthservice.application.service.UserInfoAppService;
import com.gientech.ragauthservice.application.service.UserSecurityQuestionAppService;
import com.gientech.ragauthservice.domain.entity.*;
import com.gientech.ragauthservice.domain.service.*;
import com.gientech.ragauthservice.infrastructure.AuthProperties;
import com.gientech.ragauthservice.infrastructure.CodeUtils;
import com.gientech.ragauthservice.infrastructure.contextHolder.UserImportFailListContextHolder;
import com.gientech.ragcommon.auth.dto.*;
import com.gientech.ragcommon.auth.enums.ResourceTypeEnum;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.auth.enums.UserStatusEnum;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragcommon.infrastructure.utils.EncryptUtils;
import com.gientech.ragcommon.infrastructure.utils.IPUtils;
import com.gientech.ragcommon.infrastructure.utils.JWTUtils;
import com.gientech.start.easyexcel.utils.SpringContextUtil;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.google.code.kaptcha.Producer;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums.*;
import static com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums.USER_TOKEN_PREFIX;
import static net.sf.jsqlparser.util.validation.metadata.NamedObject.user;

@Slf4j
@Service
public class UserInfoAppServiceImpl implements UserInfoAppService {

    private static final long CAPTCHA_CODE_EXPIRED = 60 * 3;

    public static final long DEFAULT_EXPIRE = 60 * 60 * 2;

    @Autowired
    private Producer captchaProducer;

    @Autowired
    private RedissonUtils redissonUtils;

    @Autowired
    private UserInfoDomainService userInfoDomainService;

    @Autowired
    private UserRoleDomainService userRoleDomainService;

    @Autowired
    private ResourceInfoDomainService resourceInfoDomainService;

    @Autowired
    private RoleInfoDomainService roleInfoDomainService;

    @Autowired
    private EncryptUtils encryptUtils;

    @Autowired
    private InterfaceInfoDomainService interfaceDomainService;

    @Autowired
    private ResourceInterfaceDomainService resourceInterfaceDomainService;

    @Autowired
    private DepartmentInfoDomainService departmentInfoDomainService;

    @Autowired
    private UserImportHelper userImportHelper;

    @Autowired
    private UserExportHelper userExportHelper;

    @Autowired
    private AuthProperties authProperties;

    @Autowired
    private UserSecurityQuestionAppService userSecurityQuestionAppService;

    private static final Pattern PASS_PATTERN = Pattern.compile("^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$");

    @Override
    public UserInfoDTO agentLogin(AgentLoginReq agentLoginReq,Long roleId) {
        UserInfo userInfo = agentLoginToken(agentLoginReq.getUserName(),roleId);
        return setLoginUserInfoToRedis(userInfo);
    }

    private UserInfo agentLoginToken(String userName,Long roleId) {
        Date loginTime = new Date(System.currentTimeMillis());
        //从数据库查询账户密码是否存在
        UserInfo userInfoDb = userInfoDomainService.getByUserName(userName);
        if (Objects.isNull(userInfoDb)) {
            UserInfo userInfo = new UserInfo();
            userInfo.setUserName(userName);
            userInfo.setEmpNo(userName);

            userInfo = userInfoDomainService.addUser(userInfo);
            userInfoDb = userInfo;
            userRoleDomainService.addUserRoles(userInfo.getId(), Arrays.asList(roleId));
            userInfoDb.setUserPassword(userName);
        }else{
            userInfoDb.setUserPassword(null);
        }


        //userGroupDomainService.existsUserSave(userInfoDb.getId(),authProperties.getOssGroupId());

        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = servletRequestAttributes.getRequest();
        String ipAddr = IPUtils.getIpAddr(request);
        userInfoDb.setIp(ipAddr);
        //更新当前登录人的上线时间
        userInfoDb.setOnlineTime(new Date());
        userInfoDomainService.update(userInfoDb);

        String cacheToken = redissonUtils.get(USER_TOKEN_PREFIX + userInfoDb.getUserName());
        String token = org.apache.commons.lang3.StringUtils.isNotBlank(cacheToken) ? cacheToken : JWTUtils.generateToken(userInfoDb.getId(), userInfoDb.getUserName());
        redissonUtils.set(USER_TOKEN_PREFIX + userInfoDb.getUserName(), token, DEFAULT_EXPIRE, TimeUnit.SECONDS);

        log.info("用户登录成功={}", loginTime);
        userInfoDb.setToken(token);
        // 不输出用户密码
        //userInfoDb.setUserPassword(null);
        return userInfoDb;
    }

    @Override
    public UserInfoDTO login(LoginReq loginReq) {
        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = servletRequestAttributes.getRequest();
        // 校验验证码
        String verifyCodeExpected = redissonUtils.get(CodeUtils.getCaptchaKey(request));
        if (!loginReq.getVerifyCode().equalsIgnoreCase(verifyCodeExpected)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }
        UserInfo userInfo = userInfoDomainService.login(loginReq);

        UserInfoDTO userInfoDTO = setLoginUserInfoToRedis(userInfo);

        Boolean setSecurityQuestion = userSecurityQuestionAppService.isSetSecurityQuestion(userInfo.getId());
        userInfoDTO.setHasSetSecurityQuestion(setSecurityQuestion);
        userInfoDTO.setHasAdminResetPassword(userInfo.getAdminResetPassword() != null);

        return userInfoDTO;
    }

    private Map<String, String> getInterface(List<ResourceInfo> resourceInfos) {
        //权限id
        List<Long> resourceIds = resourceInfos.stream()
                .filter(resourceInfo -> resourceInfo.getResourceType().equals(ResourceTypeEnum.OPER.getCode()))
                .map(resourceInfo -> resourceInfo.getId())
                .collect(Collectors.toList());
        //接口id
        List<ResourceInterface> resourceInterfaceDTOS = resourceInterfaceDomainService.findByResourceIds(resourceIds);
        List<Long> interfaceIds = resourceInterfaceDTOS
                .stream()
                .map(ResourceInterface::getInterfaceId)
                .collect(Collectors.toList());

        //转化成hash结构 map{key:服务名,value:接口列表}
        Map<String, List<InterfaceInfo>> interfaceMap = Maps.newHashMap();
        List<InterfaceInfo> interfaces = interfaceDomainService.findByIds(interfaceIds);
        interfaces.forEach(interfaceInfo -> {
            String appNameAbbreviate = interfaceInfo.getAppNameAbbreviate();
            List<InterfaceInfo> interfaceInfos = interfaceMap.get(appNameAbbreviate);
            if (CollectionUtils.isEmpty(interfaceInfos)) {
                interfaceInfos = Lists.newArrayList();
                interfaceMap.put(appNameAbbreviate, interfaceInfos);
            }
            interfaceInfos.add(interfaceInfo);
        });
        Map<String, String> map = Maps.newHashMap();
        interfaceMap.forEach((k, v) -> map.put(k, JSONObject.toJSONString(v)));
        return map;
    }

    @Override
    public UserInfoDTO simpleLogin(SimpleLoginReq simpleLoginReq) {
        LoginReq loginReq = simpleLoginReq.adaptToLoginReq();
        UserInfo userInfo = userInfoDomainService.login(loginReq);

        return setLoginUserInfoToRedis(userInfo);
    }

    @Override
    public UserInfoDTO getUserInfo() {
        User user = UserContext.getUser();
        UserInfo userInfo = userInfoDomainService.getUserInfoById(Long.parseLong(user.getUserId()));
        UserInfoDTO userInfoDTO = BeanUtil.copyProperties(userInfo, UserInfoDTO.class);
        userInfoDTO.setRoles(getByUserRoles(user.getUserId()));
        userInfoDTO.setUserPassword(null);
        return userInfoDTO;
    }

    @Override
    public UserInfoDTO getUserInfoById(Long userId) {
        UserInfo userInfo = userInfoDomainService.getUserInfoById(userId);
        return BeanUtil.copyProperties(userInfo, UserInfoDTO.class);
    }

    @Override
    public UserInfoDTO getUserInfoByUserName(String userName) {
        UserInfo userInfo = userInfoDomainService.getUserInfoByUserName(userName);
        if(userInfo==null) return null;
        UserInfoDTO userInfoDTO = BeanUtil.copyProperties(userInfo, UserInfoDTO.class);
        Long userId = userInfo.getId();
        userInfoDTO.setRoles(getByUserRoles(String.valueOf(userId)));
        userInfoDTO.setUserPassword(null);
        return userInfoDTO;
    }

    private List<RoleInfoDTO> getByUserRoles(String userId) {
        List<UserRole> userRoles = userRoleDomainService.queryByUserId(Long.parseLong(userId));
        if (CollectionUtils.isEmpty(userRoles)) {
            return null;
        }
        List<Long> roleIds = userRoles.stream().map(UserRole::getRoleId).collect(Collectors.toList());
        List<RoleInfo> roleInfos = roleInfoDomainService.queryByIds(roleIds);
        return CollectionUtils.isEmpty(roleInfos) ? null : BeanUtil.copyToList(roleInfos, RoleInfoDTO.class);
    }

    @Override
    public Boolean updatePassword(UpdatePasswordReq updatePasswordReq) {
        String pass = encryptUtils.decryptAES(updatePasswordReq.getNewPassword());
        if (pass.length() < 8) {
            throw new ApplicationException(ErrCodeEnum.PASSWORD_ILLEGAL);
        } else if (!PASS_PATTERN.matcher(pass).find()) {
            throw new ApplicationException(ErrCodeEnum.PASSWORD_ILLEGAL);
        }
        return userInfoDomainService.updatePassword(Long.parseLong(UserContext.getUser().getUserId()),
                updatePasswordReq.getOldPassword(), updatePasswordReq.getNewPassword());
    }

    @Override
    public String updateHeaderPicture(MultipartFile file) {
        return userInfoDomainService.updateHeaderPicture(file);
    }

    @Override
    public UserInfoDTO updatePersonalInfo(UpdateUserInfoReq updateUserInfoReq) {
        UserInfo userInfo = userInfoDomainService.updatePersonalInfo(updateUserInfoReq);
        userInfo.setUserPassword(null);
        return BeanUtil.copyProperties(userInfo, UserInfoDTO.class);
    }

    @Override
    public Boolean updateUseInfoBatch(UpdateUserInfoReq req) {
        if (CollectionUtils.isEmpty(req.getUserIds()) || !StringUtils.hasText(req.getDeptId()) || !StringUtils.hasText(req.getDeptName())) {
            throw new ApplicationException(ErrCodeEnum.PARAM_LIST_EMPTY);
        }
        return userInfoDomainService.updateUseInfoBatch(req);
    }

    @Override
    public Boolean updateUserStatusBatch(UpdateUserInfoReq req) {
        if (CollectionUtils.isEmpty(req.getUserIds()) || Objects.isNull(req.getStatus())) {
            throw new ApplicationException(ErrCodeEnum.PARAM_LIST_EMPTY);
        }
        return userInfoDomainService.updateUseInfoBatch(req);
    }

    @Override
    public Boolean logout() {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        redissonUtils.deleteKey(RedisKeyEnums.USER_TOKEN_PREFIX + userName);
        redissonUtils.deleteKey(AUTH_USER_RESOURCE + userName);
        redissonUtils.deleteKey(AUTH_USER_MENU + userName);
        return true;
    }

    @Override
    public void getKaptchaImage(HttpServletRequest request, HttpServletResponse response, boolean isLogin) throws IOException {
        response.setDateHeader("Expires", 0);
        response.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
        response.addHeader("Cache-Control", "post-check=0, pre-check=0");
        response.setHeader("Pragma", "no-cache");
        response.setContentType("image/jpeg");
        //生成验证码
        String capText = captchaProducer.createText();
        //存储
        if (isLogin) {
            redissonUtils.set(CodeUtils.getCaptchaKey(request), capText, CAPTCHA_CODE_EXPIRED, TimeUnit.SECONDS);
        } else {
            redissonUtils.set(CodeUtils.getRegisterCaptchaKey(request), capText, CAPTCHA_CODE_EXPIRED, TimeUnit.SECONDS);
        }
        //向客户端写出
        BufferedImage bi = captchaProducer.createImage(capText);
        ServletOutputStream out = response.getOutputStream();
        ImageIO.write(bi, "jpg", out);
        try {
            out.flush();
        } finally {
            out.close();
        }
    }


    @Override
    public UserInfoDTO addUser(AddUserReq addUserReq) {
        String userName = addUserReq.getUserName();
        // 校验用户账号是否已存在
        UserInfo userInfo = userInfoDomainService.getByUserName(userName);
        if (Objects.nonNull(userInfo)) {
            throw new ApplicationException(ErrCodeEnum.USER_NAME_EXISTING_ERROR);
        }
        //校验手机号和邮箱(手机号和邮箱不能重复)
        List<UserInfo> users = userInfoDomainService.getByPhoneOrEmail(addUserReq.getUserPhone(), addUserReq.getUserEmail());
        if (users.stream().anyMatch(user -> addUserReq.getUserPhone().equals(user.getUserPhone())))
            throw new ApplicationException(ErrCodeEnum.USER_PHONE_REPEAT);
        if (users.stream().anyMatch(user -> addUserReq.getUserEmail().equals(user.getUserEmail())))
            throw new ApplicationException(ErrCodeEnum.USER_EMAIL_REPEAT);
        try {
            userInfo = userInfoDomainService.addUser(BeanUtil.copyProperties(addUserReq, UserInfo.class));
            userRoleDomainService.addUserRoles(userInfo.getId(), addUserReq.getRoleIds());
            UserInfoDTO userInfoDTO = BeanUtil.copyProperties(userInfo, UserInfoDTO.class);
            userInfoDTO.setRoles(getByUserRoles(String.valueOf(userInfoDTO.getId())));
            return userInfoDTO;
        } catch (DomainException ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ex.getErrCode(), ex.getMessage());
        }
    }

    @Transactional
    @Override
    public Boolean regist(UserRegistReq userRegistReq) {
        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = servletRequestAttributes.getRequest();
        // 校验验证码
        String verifyCodeExpected = redissonUtils.get(CodeUtils.getCaptchaKey(request));
        if (!userRegistReq.getVerifyCode().equalsIgnoreCase(verifyCodeExpected)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }

        String pass = encryptUtils.decryptAES(userRegistReq.getPassword());
        if (pass.length() < 8) {
            throw new ApplicationException(ErrCodeEnum.PASSWORD_ILLEGAL);
        } else if (!PASS_PATTERN.matcher(pass).find()) {
            throw new ApplicationException(ErrCodeEnum.PASSWORD_ILLEGAL);
        } else if (!userRegistReq.getPassword().equals(userRegistReq.getPasswordAffirm())) {
            throw new ApplicationException(ErrCodeEnum.PASSWORD_NOT_SAME);
        }
        // 校验用户账号是否已存在
        UserInfo userInfo = userInfoDomainService.getByUserName(userRegistReq.getUserName());
        if (Objects.nonNull(userInfo)) {
            throw new ApplicationException(ErrCodeEnum.USER_NAME_EXISTING_ERROR);
        }
        UserInfo addUser = BeanUtil.copyProperties(userRegistReq, UserInfo.class);
        addUser.setUserPhone(userRegistReq.getUserIphone());
        addUser.setUserPassword(userRegistReq.getPassword());
        Long userId = userInfoDomainService.regist(addUser);
        if (!Objects.isNull(userId))
            userRoleDomainService.addUserRoles(userId, Arrays.asList(authProperties.getDefaultRoleId()));

        // 保存密保问题
        List<UserSecurityQuestionDTO> userSecurityQuestionList = userRegistReq.getUserSecurityQuestionList();
        userSecurityQuestionAppService.save(userSecurityQuestionList, userId);
        return true;
    }

    @Override
    public Boolean setUserStatus(List<Long> userIds, Integer status) {
        return userInfoDomainService.setUserStatus(userIds, status);
    }

    @Override
    public Page<UserInfoDTO> searchUserList(SearchUserReq searchUserListRequest) {
        Page<UserInfo> userInfoPage = userInfoDomainService.list(searchUserListRequest);
        Page<UserInfoDTO> result = new Page<>();
        BeanUtil.copyProperties(userInfoPage, result);

        List<UserInfoDTO> list = new ArrayList<>();
        for(UserInfo userInfo:userInfoPage.getRecords()){
            UserInfoDTO userInfoDTO = BeanUtil.copyProperties(userInfo, UserInfoDTO.class);
            userInfoDTO.setHasAdminResetPassword(userInfo.getAdminResetPassword() != null);

            List<RoleInfoDTO> userRoles = getByUserRoles(String.valueOf(userInfoDTO.getId()));
            userInfoDTO.setRoles(userRoles);
            userInfoDTO.setUserPassword(null);
            if (!CollectionUtils.isEmpty(userRoles)) {
                for (RoleInfoDTO userRole : userRoles) {
                    if (userRole.getId().equals(authProperties.getSuperRoleId())) {
                        userInfoDTO.setUserType(RoleTypeEnums.SUPER_ADMIN.getCode());
                        break;
                    } else if (userRole.getId().equals(authProperties.getAdminRoleId())) {
                        userInfoDTO.setUserType(RoleTypeEnums.ADMIN.getCode());
                        break;
                    }
                }
            }
            list.add(userInfoDTO);
        }
        result.setRecords(list);

        return result;
    }

    @Override
    public Boolean resetPassword(List<Long> userIds) {
        return userInfoDomainService.resetPassword(userIds);
    }

    @Override
    public UserInfoDTO getUserInfoByAppKey(String appKey) {
        UserInfo userInfo = userInfoDomainService.getUserInfoByAppKey(appKey);
        if (userInfo == null) {
            return null;
        } else {
            redissonUtils.set(appKey + ":USER_ID", userInfo.getId().toString(), DEFAULT_EXPIRE, TimeUnit.SECONDS);
            redissonUtils.set(appKey + ":USER_NAME", userInfo.getUserName(), DEFAULT_EXPIRE, TimeUnit.SECONDS);
            return setLoginUserInfoToRedis(userInfo);
        }
    }

    private UserInfoDTO setLoginUserInfoToRedis(UserInfo userInfo) {
        List<UserRole> userRoles = userRoleDomainService.queryByUserId(userInfo.getId());
        if (CollectionUtils.isEmpty(userRoles)) {
            throw new ApplicationException(ErrCodeEnum.NO_ROLE_EEROR);
        }
        UserInfoDTO userInfoDTO = BeanUtil.copyProperties(userInfo, UserInfoDTO.class);
        List<Long> roleIds = userRoles.stream().map(r -> r.getRoleId()).collect(Collectors.toList());

        List<ResourceInfo> resourceInfos = resourceInfoDomainService.queryByRoleIds(roleIds);
        if(!CollectionUtils.isEmpty(resourceInfos)){
            redissonUtils.hashPut(AUTH_USER_RESOURCE + userInfoDTO.getUserName(), getInterface(resourceInfos), DEFAULT_EXPIRE, ChronoUnit.SECONDS);
            List<MenuDTO> menuDTOS = resourceInfoDomainService.getMenusByRoleIds(roleIds);
            redissonUtils.set(AUTH_USER_MENU + userInfoDTO.getUserName(), JSON.toJSONString(menuDTOS), DEFAULT_EXPIRE, TimeUnit.SECONDS);
        }
        userInfoDTO.setUserPassword(null);

        return userInfoDTO;
    }

    @Override
    public Boolean addBatch(List<AddUserBatchReq> userBatchReqs) {
        Validator validator = SpringContextUtil.getBean(Validator.class);
        userBatchReqs.forEach(item -> {
            Set<ConstraintViolation<AddUserBatchReq>> validate = validator.validate(item);
            if (!validate.isEmpty()) {
                StringBuffer errorMsg = new StringBuffer("");
                Iterator<ConstraintViolation<AddUserBatchReq>> iterator = validate.iterator();
                while (iterator.hasNext()) {
                    ConstraintViolation<AddUserBatchReq> next = iterator.next();
                    errorMsg.append(next.getMessageTemplate()).append(";");
                }
                throw new ApplicationException(ErrCodeEnum.USER_PARAMETER_VERIFY_FAIL.getErrCode(), errorMsg.toString());
            }
        });
        addUserBatch(BeanUtil.copyToList(userBatchReqs, UserImportDTO.class));
        return true;
    }

    @Override
    public Boolean update(UpdateUserReq updateUserReq) {
        String userEmail = updateUserReq.getUserEmail();
        String userPhone = updateUserReq.getUserPhone();
        Long userId = updateUserReq.getId();

        //校验手机号和邮箱(手机号和邮箱不能重复)
        List<UserInfo> users = userInfoDomainService.getByPhoneOrEmail(userPhone, userEmail);
        if (users.stream().anyMatch(user ->  userPhone.equals(user.getUserPhone()) && !userId.equals(user.getId())))
            throw new ApplicationException(ErrCodeEnum.USER_PHONE_REPEAT);
        if (users.stream().anyMatch(user -> userEmail.equals(user.getUserEmail())  && !userId.equals(user.getId())))
            throw new ApplicationException(ErrCodeEnum.USER_EMAIL_REPEAT);
        userInfoDomainService.update(BeanUtil.copyProperties(updateUserReq, UserInfo.class));
        //更新角色
        List<Long> roleIds = updateUserReq.getRoleIds();
        if (!CollectionUtils.isEmpty(roleIds))
            updateUserRole(updateUserReq.getId(), roleIds);
        return true;
    }

    private void updateUserRole(Long userId, List<Long> roleIds) {
        List<UserRole> dbUserRoleList = userRoleDomainService.queryByUserId(userId);
        dbUserRoleList = CollectionUtils.isEmpty(dbUserRoleList) ? new ArrayList<>() : dbUserRoleList;
        List<Long> dbRoleIds = dbUserRoleList.stream().map(dbUserRole -> dbUserRole.getRoleId()).collect(Collectors.toList());
        List<Long> addRoleIds = (List<Long>) CollectionUtil.subtract(roleIds, dbRoleIds);
        List<Long> delRoleIds = (List<Long>) CollectionUtil.subtract(dbRoleIds, roleIds);
        userRoleDomainService.addUserRoles(userId, addRoleIds);
        userRoleDomainService.delUserRoles(userId, delRoleIds);
    }

    private void addUserBatch(List<UserImportDTO> list) {
        if (CollectionUtils.isEmpty(list))
            return;
        List<UserInfo> userInfos = BeanUtil.copyToList(list, UserInfo.class);
        Iterator<UserInfo> iterator = userInfos.iterator();
        while (iterator.hasNext()) {
            UserInfo userInfo = iterator.next();
            String userName = userInfo.getUserName();
            String userPhone = userInfo.getUserPhone();
            String userEmail = userInfo.getUserEmail();
            // 校验用户账号是否已存在
            UserInfo dbUser = userInfoDomainService.getByUserName(userName);
            if (Objects.nonNull(dbUser)) {
                log.warn("用户【{}】已存在,不处理", dbUser.getUserName());
                iterator.remove();
            }
            //校验手机号和邮箱(手机号和邮箱不能重复)
            List<UserInfo> users = userInfoDomainService.getByPhoneOrEmail(userPhone, userEmail);
            if (CollUtil.isNotEmpty(users))
                iterator.remove();
        }
        if (CollectionUtils.isEmpty(userInfos))
            return;
        //新增用户
        List<UserInfo> userInfoList = userInfoDomainService.addUsers(userInfos);
        List<Long> userIds = userInfoList.stream().map(UserInfo::getId).collect(Collectors.toList());
        //新增角色
        List<UserRole> userRoles = Lists.newArrayList();
        userIds.forEach(userId -> {
            UserRole userRole = new UserRole();
            userRole.setUserId(userId);
            userRole.setRoleId(authProperties.getDefaultRoleId());
            userRoles.add(userRole);
        });
        userRoleDomainService.addUserRoles(userRoles);
    }

    @Override
    public List<UserImportDTO> importData(MultipartFile file) {
         userImportHelper.importData(file, UserImportDTO.class);
        List<UserImportDTO> userImportFailList = UserImportFailListContextHolder.getUserImportFailList();
        UserImportFailListContextHolder.clear();
        return userImportFailList;
    }

    @Override
    public void downloadTemplate(ExcelTypeEnum type, HttpServletResponse response) {
        log.info("文件类型,{}", type.getValue());
        userImportHelper.exportData("用户信息模板", null, UserImportDTO.class, type, response);
    }

    @Override
    public Boolean deleteByIds(List<Long> userIds) {
        if (CollectionUtils.isEmpty(userIds))
            return false;
        //删除用户
        userInfoDomainService.deleteByIds(userIds);
        //删除角色
        userRoleDomainService.deleteByuserIds(userIds);
        return true;
    }

    @Override
    public Integer getUserType() {
        User user = UserContext.getUser();
        String userId = user.getUserId();
        return userRoleDomainService.getRoleType(Long.parseLong(userId));
    }

    @Override
    public Page<ResignedUserDTO> searchResignedUserList(UserQueryReq userQueryReq) {
        userQueryReq.setStatus(UserStatusEnum.RESIGNED.getCode());
        userQueryReq.setOrderByResignDate(Boolean.TRUE);
        Page<UserInfo> userInfoPage = userInfoDomainService.list(userQueryReq);

        Page<ResignedUserDTO> resignedUserDTOPage = new Page<>();
        BeanUtil.copyProperties(userInfoPage, resignedUserDTOPage);
        List<ResignedUserDTO> resignedUserDTOS = BeanUtil.copyToList(userInfoPage.getRecords(), ResignedUserDTO.class);
        resignedUserDTOPage.setRecords(resignedUserDTOS);

        if (CollUtil.isEmpty(resignedUserDTOS)) {
            return resignedUserDTOPage;
        }

        // 获取部门信息
        List<Long> deptIds = resignedUserDTOS.stream().map(ResignedUserDTO::getDeptId).filter(Objects::nonNull).map(Long::valueOf).toList();
        Map<String, String> deptMap = departmentInfoDomainService.listByIds(deptIds).stream()
                .collect(Collectors.toMap(dept -> String.valueOf(dept.getId()), DepartmentInfo::getName));

        for (ResignedUserDTO resignedUserDTO : resignedUserDTOS) {
            // 获取所属部门信息
            if (StrUtil.isNotBlank(resignedUserDTO.getDeptId())) {
                resignedUserDTO.setDeptName(deptMap.get(resignedUserDTO.getDeptId()));
            }
            // 离职天数
            if (Objects.nonNull(resignedUserDTO.getResignDate())) {
                resignedUserDTO.setResignedDays(DateUtil.between(DateUtil.beginOfDay(resignedUserDTO.getResignDate()), DateUtil.beginOfDay(DateUtil.date()), DateUnit.DAY));
            }
        }
        return resignedUserDTOPage;
    }

    @Override
    public void export(List<String> deptIds, HttpServletResponse response) {
        List<UserInfoExt> userInfoExts = userInfoDomainService.searchUserList(deptIds);
        if (CollectionUtils.isEmpty(userInfoExts)) {
            log.warn("没有数据");
            return;
        }
        userExportHelper.exportData(
                "用户信息" + DateUtil.format(new Date(), "yyyyMMddHHmmss"),
                BeanUtil.copyToList(userInfoExts, UserExportDTO.class),
                UserExportDTO.class,
                ExcelTypeEnum.valueOf("xlsx".toUpperCase(Locale.ROOT)),
                response);
    }

    @Override
    public void exportError(HttpServletResponse response) {
        String userStr = redissonUtils.get(RedisKeyEnums.USER_IMPORT_DATA_ERROR_PREFIX + UserContext.getUser().getUserName());
        List<UserImportDTO> userImportDTOS = JSONArray.parseArray(userStr, UserImportDTO.class);
        if(CollectionUtils.isEmpty(userImportDTOS))
            return;

        userImportHelper.exportData(
                "导入失败的用户数据" + DateUtil.format(new Date(),"yyyyMMddHHmmss"),
                userImportDTOS,
                UserImportDTO.class,
                ExcelTypeEnum.valueOf("xlsx".toUpperCase(Locale.ROOT)),
                response);
    }

    @Override
    public Page<UserInfoDTO> searchUserByRole(Long roleId, Long pageNo, Long pageSize) {
        Page<UserInfoDTO> result = new Page<>();
        List<UserRole> userRoles = userRoleDomainService.queryByRoleId(roleId);
        if (CollectionUtils.isEmpty(userRoles))
            return result;
        List<Long> userIds = userRoles.stream().map(UserRole::getUserId).collect(Collectors.toList());
        Page<UserInfo> userInfoPage = userInfoDomainService.list(userIds, pageNo, pageSize);
        BeanUtil.copyProperties(userInfoPage, result);
        result.setRecords(BeanUtil.copyToList(userInfoPage.getRecords(), UserInfoDTO.class));
        return result;
    }

    @Override
    public Boolean clearResignedUsers() {
        UserQueryReq userQueryReq = UserQueryReq.builder()
                .status(UserStatusEnum.RESIGNED.getCode())
                .pageNo(1L)
                .pageSize(99999L)
                .build();
        Page<UserInfo> userInfoPage = userInfoDomainService.list(userQueryReq);

        List<Long> resignedUserIds = Optional.ofNullable(userInfoPage)
                .map(Page::getRecords)
                .map(userInfoList -> userInfoList.stream().map(UserInfo::getId).toList())
                .orElse(Lists.newArrayList());

        return deleteByIds(resignedUserIds);
    }

    @Override
    public Integer getUserType(String userName) {
        Long userId = getUserId(userName);
        return Objects.isNull(userId) ? null : userRoleDomainService.getRoleType(userId);
    }

    @Override
    public Boolean resetPassword(Long userId, String password, Boolean isAdmin) {
        String pass = encryptUtils.decryptAES(password);
        if (pass.length() < 8) {
            throw new ApplicationException(ErrCodeEnum.PASSWORD_ILLEGAL);
        } else if (!PASS_PATTERN.matcher(pass).find()) {
            throw new ApplicationException(ErrCodeEnum.PASSWORD_ILLEGAL);
        }
        return userInfoDomainService.resetPassword(userId, password, isAdmin);
    }

    @Override
    public String queryAdminResetPassword(Long userId) {
        UserInfo userInfo = userInfoDomainService.getUserInfoById(userId);
        String adminResetPassword = userInfo.getAdminResetPassword();
        return adminResetPassword;
    }

    /**
     *
     * @param userName 用户名
     * @return 用户ID
     */
    private Long getUserId(String userName) {
        return Optional.ofNullable(userName)
                .map(userInfoDomainService::getByUserName)
                .map(UserInfo::getId)
                .orElse(null);
    }


    @Override
    public Boolean updateBatchUserFeature(List<Long> userIds, String feature) {
        return userInfoDomainService.updateBatchUserFeature(userIds, feature);
    }
}
