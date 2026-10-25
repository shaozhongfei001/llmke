package com.gientech.ragauthservice.domain.service.impl;

import com.gientech.ragauthservice.infrastructure.security.PasswordHasher;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.UserSecurityQuestionAppService;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.entity.UserInfoExt;
import com.gientech.ragauthservice.domain.repository.UserInfoRepository;
import com.gientech.ragauthservice.domain.service.UserInfoDomainService;
import com.gientech.ragauthservice.infrastructure.PasswordGenerator;
import com.gientech.ragcommon.auth.enums.UserStatusEnum;
import com.gientech.ragcommon.auth.request.LoginReq;
import com.gientech.ragcommon.auth.request.SearchUserReq;
import com.gientech.ragcommon.auth.request.UpdateUserInfoReq;
import com.gientech.ragcommon.auth.request.UserQueryReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragcommon.infrastructure.utils.EncryptUtils;
import com.gientech.ragcommon.infrastructure.utils.IPUtils;
import com.gientech.ragcommon.infrastructure.utils.JWTUtils;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.gientech.start.storage.model.FileInfo;
import com.gientech.start.storage.properties.StorageProperties;
import com.gientech.start.storage.utils.FileStorageUtils;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.compress.utils.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;

import java.math.BigInteger;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.*;
import java.util.concurrent.TimeUnit;

import static com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums.USER_TOKEN_PREFIX;

/**
 * <p>
 * 用户表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-06-13
 */
@Slf4j
@Service
public class UserInfoDomainServiceImpl implements UserInfoDomainService {

    @Autowired
    private UserInfoRepository userInfoRepository;

    @Autowired
    private RedissonUtils redissonUtils;

    @Autowired
    private EncryptUtils encryptUtils;

    @Autowired
    private FileStorageUtils fileStorageUtils;

    @Autowired
    private StorageProperties storageProperties;

    @Autowired
    private UserSecurityQuestionAppService userSecurityQuestionAppService;

    /**
     * token的过期时间
     */
    public static final long DEFAULT_EXPIRE = 60 * 60 * 2;

    private static final String HEADER_PIC_FOLDER = "header_pic";

    /**
     * 缺省头像
     */
    private static final String DEFAULT_HEADER_PIC = "默认用户.png";

    /**
     * 缺省密码
     */
    @Value("${user.default-password:passWORD@123}")
    private String defaultPassword;

    @Override
    public UserInfo login(LoginReq loginReq) {
        // R13-SEC-A3：AES 解密得到明文，直接做 BCrypt 校验；历史 MD5 账号校验通过后原地升级为 BCrypt
        String rawPassword = rawPassword(loginReq.getPassword());
        Date loginTime = new Date(System.currentTimeMillis());
        //从数据库查询账户密码是否存在
        UserInfo user = userInfoRepository.getByUserName(loginReq.getUserName());
        if (Objects.isNull(user)) {
            throw new DomainException(ErrCodeEnum.USER_LOGIN_PARAM_ERROR);
        }

        // 先校验验证码是否正确，在校验账号信息
        if (!PasswordHasher.matches(rawPassword, user.getUserPassword())) {
            throw new DomainException(ErrCodeEnum.USER_LOGIN_PARAM_ERROR);
        }
        if (PasswordHasher.needsUpgrade(user.getUserPassword())) {
            // 透明迁移：不改用户口令，只把存储形式换成 BCrypt
            user.setUserPassword(PasswordHasher.encode(rawPassword));
            userInfoRepository.updateByPrimaryKey(user);
            log.info("password hash upgraded to bcrypt for user {}", user.getUserName());
        }
        //用户状态被设置为禁用 账户状态为禁用
        if (UserStatusEnum.DISENABLED.getCode().equals(user.getStatus())) {
            throw new DomainException(ErrCodeEnum.USER_DISABLED_ERROR);
        }
        // 离职用户不能登录系统
        if (UserStatusEnum.RESIGNED.getCode().equals(user.getStatus())) {
            throw new DomainException(ErrCodeEnum.USER_RESIGNED_ERROR);
        }

        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = servletRequestAttributes.getRequest();
        String ipAddr = IPUtils.getIpAddr(request);
        user.setIp(ipAddr);
        //更新当前登录人的上线时间
        user.setOnlineTime(new Date());
        userInfoRepository.updateByPrimaryKey(user);
        String cacheToken = redissonUtils.get(USER_TOKEN_PREFIX + user.getUserName());
        String token = StringUtils.isNotBlank(cacheToken) ? cacheToken : JWTUtils.generateToken(user.getId(), user.getUserName());
        redissonUtils.set(USER_TOKEN_PREFIX + user.getUserName(), token, DEFAULT_EXPIRE, TimeUnit.SECONDS);
        log.info("用户登录成功={}", loginTime);
        user.setToken(token);
        // 不输出用户密码
        user.setUserPassword(null);

        return user;
    }

    @Override
    public UserInfo getUserInfoById(Long userId) {
        UserInfo userInfo = userInfoRepository.getUserInfoById(userId);
        if (Objects.isNull(userInfo)) {
            throw new DomainException(ErrCodeEnum.USER_NOT_EXISTS_ERROR);
        }
        return userInfo;
    }

    @Override
    public UserInfo getUserInfoByUserName(String userName) {
        UserInfo userInfo = userInfoRepository.getByUserName(userName);
        return userInfo;
    }

    @Override
    public List<UserInfo> getUserListByIds(List<Long> userIds) {
        return userInfoRepository.getUserListByIds(userIds);
    }

    @Override
    public Boolean updatePassword(long userId, String oldPassword, String newPassword) {
        UserInfo userInfo = userInfoRepository.getUserInfoById(userId);

        if (Objects.nonNull(userInfo)) {
            // R13-SEC-A3：明文比较（旧口令兼容 MD5），新口令一律 BCrypt 存储
            oldPassword = rawPassword(oldPassword);
            newPassword = rawPassword(newPassword);
            if (StringUtils.equals(oldPassword, newPassword)) {
                throw new DomainException(ErrCodeEnum.NEW_OLD_PASSWD_SAME_ERROR);
            }
            //先判断原来的密码是否正确
            if (!PasswordHasher.matches(oldPassword, userInfo.getUserPassword())) {
                throw new DomainException(ErrCodeEnum.OLD_PASSWD_WRONG_ERROR);
            }

            userInfoRepository.clearAdminResetPassword(userId);
            userInfo.setAdminResetPassword(null);
            userInfo.setUserPassword(PasswordHasher.encode(newPassword));
            userInfoRepository.updateByPrimaryKey(userInfo);
            return true;
        }
        return false;
    }

    @Override
    public Boolean resetPassword(long userId, String newPassword, Boolean isAdmin) {
        UserInfo userInfo = userInfoRepository.getUserInfoById(userId);

        if (!Objects.nonNull(userInfo)) {
            return false;
        }

        if(isAdmin){
            userInfo.setAdminResetPassword(newPassword);
        } else {
            userInfo.setAdminResetPassword(null);
        }
        // R13-SEC-A3：重置口令同样只做 AES 解密 + BCrypt 存储
        userInfo.setUserPassword(PasswordHasher.encode(rawPassword(newPassword)));
        userInfoRepository.updateByPrimaryKey(userInfo);
        return true;
    }

    @Override
    public String updateHeaderPicture(MultipartFile file) {
        try {
            User user = UserContext.getUser();
            UserInfo userInfo = userInfoRepository.getByUserName(user.getUserName());
            if (Objects.nonNull(userInfo)) {
                String folder = HEADER_PIC_FOLDER + "/" + userInfo.getUserName() + "/";
                // 上传文件
                FileInfo fileInfo = fileStorageUtils.putObject(folder, file, null);
                // 更新用户表url字段
                userInfo.setUrl(fileInfo.getFilePath());
                userInfoRepository.updateByPrimaryKey(userInfo);
                return fileInfo.getFilePath();
            }
            return null;
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new DomainException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }
    }

    @Override
    public UserInfo updatePersonalInfo(UpdateUserInfoReq req) {
        User user = UserContext.getUser();
        Long userId = Objects.nonNull(req.getId()) ? req.getId() : Long.valueOf(user.getUserId());
        UserInfo userInfo = userInfoRepository.getUserInfoById(userId);

        if (Objects.nonNull(userInfo)) {
            if (StringUtils.isNotBlank(req.getUserRealname())) {
                userInfo.setUserRealname(req.getUserRealname());
            }
            if (StringUtils.isNotBlank(req.getUserPhone())) {
                userInfo.setUserPhone(req.getUserPhone());
            }
            if (StringUtils.isNotBlank(req.getUserEmail())) {
                userInfo.setUserEmail(req.getUserEmail());
            }
            if (Objects.nonNull(req.getDeptId())) {
                userInfo.setDeptId(req.getDeptId());
            }
            if (StringUtils.isNotBlank(req.getDeptName())) {
                userInfo.setDeptName(req.getDeptName());
            }
            userInfoRepository.updateByPrimaryKey(userInfo);
        }
        return userInfo;
    }

    @Override
    public Boolean updateUseInfoBatch(UpdateUserInfoReq req) {
        return userInfoRepository.updateBatch(req.getUserIds(), req.getDeptId(), req.getDeptName(), req.getStatus()) > 0;
    }

    /**
     * R13-SEC-A3：只做 AES 解密，不做哈希（哈希交由 PasswordHasher）。
     */
    private String rawPassword(String cipherText) {
        try {
            return encryptUtils.decryptAES(cipherText);
        } catch (Exception e) {
            log.error("decrypt password failed", e);
            throw new DomainException(ErrCodeEnum.USER_LOGIN_PARAM_ERROR);
        }
    }


    @Override
    public UserInfo addUser(UserInfo userInfo) {
        try {
            // 管理员新增用户密码为8位随机密码
//            String randomPwd = generateRandomPassword();
            String randomPwd = PasswordGenerator.generatePassword(8);
            String password = PasswordHasher.encodeChecked(randomPwd);
            userInfo.setUserPassword(password);
            // 管理员新增用户头像为缺省头像
            String bucketName = storageProperties.getDefaultStorageProperties().getBucketName();
            String objectName = HEADER_PIC_FOLDER + "/" + DEFAULT_HEADER_PIC;
            String url = storageProperties.getDefaultStorageProperties().getEndPoint() + "/" + bucketName + "/" + objectName;
            userInfo.setUrl(url);
            userInfo.setAppKey(UUID.randomUUID().toString().replaceAll("-",""));
            Long id = userInfoRepository.addUserInfo(userInfo);
            userInfo.setUserPassword(randomPwd);
            userInfo.setId(id);
            return userInfo;
        } catch (NoSuchAlgorithmException e) {
            log.error(e.getMessage(), e);
            throw new DomainException(
                    ErrCodeEnum.ADD_NEW_USER_ERROR.getErrCode(),
                    ErrCodeEnum.ADD_NEW_USER_ERROR.getErrMsg());
        }
    }

    private void setUserPassAndAvatar(UserInfo userInfo) throws NoSuchAlgorithmException {
        String randomPwd = userInfo.getUserPassword();
        String password = PasswordHasher.encodeChecked(randomPwd);
        userInfo.setUserPassword(password);
        // 管理员新增用户头像为缺省头像
        String bucketName = storageProperties.getDefaultStorageProperties().getBucketName();
        String objectName = HEADER_PIC_FOLDER + "/" + DEFAULT_HEADER_PIC;
        String url = storageProperties.getDefaultStorageProperties().getEndPoint() + "/" + bucketName + "/" + objectName;
        userInfo.setUrl(url);
    }

    @Override
    public List<UserInfo> addUsers(List<UserInfo> userInfoList) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        userInfoList.forEach(userInfo -> {
            try {
                userInfo.setCreateBy(userName);
                userInfo.setUpdateBy(userName);
                userInfo.setGmtCreate(new Date());
                userInfo.setGmtModified(userInfo.getGmtCreate());
                setUserPassAndAvatar(userInfo);
            } catch (NoSuchAlgorithmException e) {
                log.error(e.getMessage(), e);
                throw new DomainException(
                        ErrCodeEnum.ADD_NEW_USER_ERROR.getErrCode(),
                        ErrCodeEnum.ADD_NEW_USER_ERROR.getErrMsg());
            }
        });
        return userInfoRepository.inserBatch(userInfoList);
    }

    /**
     * 生成8位随机密码
     *
     * @return
     */
    public String generateRandomPassword() {
        Random random = new SecureRandom();
        StringBuilder pwd = new StringBuilder();
        //密码包括大小写和数字
        pwd.append((char) (random.nextInt(25) + 65));
        pwd.append((char) (random.nextInt(25) + 97));
        pwd.append(random.nextInt(9));
        for (int i = 0; i < 5; i++) {
            int j = random.nextInt(100);
            if (j % 2 == 0) {
                pwd.append((char) (random.nextInt(25) + 65));
            } else if (j % 3 == 0) {
                pwd.append((char) (random.nextInt(25) + 97));
            } else {
                pwd.append(random.nextInt(9));
            }
        }
        return pwd.toString();
    }

    @Override
    public UserInfo getByUserName(String userName) {
        return userInfoRepository.getByUserName(userName);
    }

    @Override
    public Long regist(UserInfo userInfo) {
        try {
            String password = PasswordHasher.encodeChecked(encryptUtils.decryptAES(userInfo.getUserPassword()));
            userInfo.setUserPassword(password);
            userInfo.setStatus(UserStatusEnum.ENABLED.getCode());
            String bucketName = storageProperties.getDefaultStorageProperties().getBucketName();
            String objectName = HEADER_PIC_FOLDER + "/" + DEFAULT_HEADER_PIC;
            String url = storageProperties.getDefaultStorageProperties().getEndPoint() + "/" + bucketName + "/" + objectName;
            userInfo.setUrl(url);
            return userInfoRepository.addUserInfo(userInfo);
        } catch (NoSuchAlgorithmException e) {
            log.error(e.getMessage(), e);
            throw new DomainException(ErrCodeEnum.REGIST_USER_ERROR);
        }
    }

    @Override
    public Boolean setUserStatus(List<Long> userIds, Integer status) {
        return userInfoRepository.setUserStatus(userIds, status);
    }

    @Override
    public Page<UserInfo> list(SearchUserReq searchUserListRequest) {
        return userInfoRepository.list(searchUserListRequest);
    }

    @Override
    public Boolean resetPassword(List<Long> userIds) {
        try {
            for (Long userId : userIds) {
                UserInfo userInfo = userInfoRepository.getUserInfoById(userId);
                if (Objects.nonNull(userInfo)) {
                    // 管理员重置用户密码为缺省密码
                    String password = PasswordHasher.encodeChecked(defaultPassword);
                    userInfo.setUserPassword(password);
                    userInfoRepository.updateByPrimaryKey(userInfo);
                }
            }
            return true;
        } catch (NoSuchAlgorithmException e) {
            log.error(e.getMessage(), e);
            throw new DomainException(ErrCodeEnum.RESET_PASSWORD_ERROR);
        }
    }

    @Override
    public List<UserInfo> getUserInfoByIds(List<Long> userIds) {
        if (CollectionUtils.isEmpty(userIds))
            Lists.newArrayList();
        return userInfoRepository.getUserInfoByIds(userIds);
    }

    @Override
    public UserInfo getUserInfoByAppKey(String appKey) {
        return userInfoRepository.getUserInfoByAppKey(appKey);
    }

    @Override
    public Boolean update(UserInfo userInfo) {
        try {
            String randomPwd = userInfo.getUserPassword();
            if (StringUtils.isNotBlank(randomPwd)) {
                String password = PasswordHasher.encodeChecked(randomPwd);
                userInfo.setUserPassword(password);
            }
            userInfoRepository.updateByPrimaryKey(userInfo);
            return true;
        } catch (NoSuchAlgorithmException e) {
            log.error(e.getMessage(), e);
            throw new DomainException(ErrCodeEnum.USER_UPDATE_FAIL);
        }
    }

    @Override
    public void deleteByIds(List<Long> userIds) {
        userInfoRepository.deleteByIds(userIds);
    }

    @Override
    public List<UserInfoExt> searchUserList(List<String> deptIds) {
        return userInfoRepository.searchUserList(deptIds);
    }

    @Override
    public List<UserInfo> list(UserInfo userInfoParam) {
        return userInfoRepository.list(userInfoParam);
    }

    @Override
    public List<UserInfo> list(String fuzzy) {
        return userInfoRepository.list(fuzzy);
    }

    @Override
    public List<UserInfo> listNoDeptUsers(UserInfo userInfoParam) {
        return userInfoRepository.listNoDeptUsers(userInfoParam);
    }

    @Override
    public List<UserInfo> listByDeptIds(List<Long> deptIds) {
        return userInfoRepository.listByDeptIds(deptIds);
    }

    @Override
    public Page<UserInfo> list(List<Long> userIds, Long pageNo, Long pageSize) {
        return userInfoRepository.list(userIds, pageNo, pageSize);
    }

    @Override
    public Page<UserInfo> list(UserQueryReq userQueryReq) {
        return userInfoRepository.list(userQueryReq);
    }

    @Override
    public List<UserInfo> getByPhoneOrEmail(String userPhone, String userEmail) {
        return userInfoRepository.getByPhoneOrEmail(userPhone, userEmail);
    }

    @Override
    public Boolean updateBatchUserFeature(List<Long> userIds, String feature) {
        return userInfoRepository.updateBatchUserFeature(userIds, feature);
    }

    @Override
    public Boolean clearAdminResetPassword(Long userId) {
        return userInfoRepository.clearAdminResetPassword(userId);
    }
}
