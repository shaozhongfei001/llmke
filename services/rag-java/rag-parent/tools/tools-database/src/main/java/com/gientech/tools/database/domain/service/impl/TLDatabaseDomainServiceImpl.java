package com.gientech.tools.database.domain.service.impl;

import cn.hutool.crypto.SecureUtil;
import cn.hutool.crypto.symmetric.AES;
import com.alibaba.excel.util.StringUtils;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.tools.database.application.remote.AuthUserClient;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.repository.TLDatabaseRepository;
import com.gientech.tools.database.domain.service.TLDatabaseDomainService;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TLDatabaseDomainServiceImpl implements TLDatabaseDomainService {
    private static final Logger log = LoggerFactory.getLogger(TLDatabaseDomainServiceImpl.class);

    @Autowired
    private TLDatabaseRepository dbDatabaseRepository;

    @Autowired
    private AuthUserClient authUserClient;

    @Value("${database.pw.enc-key:C7OT8Ty8ghEFRZF1}")
    private String encKey;

    @Override
    public Boolean save(TLDatabase database) {
        String dbPassword = database.getDbPassword();
        if (dbPassword != null && !"".equals(dbPassword)) {
            AES aes = SecureUtil.aes(encKey.getBytes());
            String dbPasswordEnc = aes.encryptHex(dbPassword);
            database.setDbPassword(dbPasswordEnc);
        }

        return dbDatabaseRepository.save(database);
    }

    @Override
    public Boolean updateById(TLDatabase database) {
        if (database.getDbPassword() != null && !database.getDbPassword().isEmpty()) {
            AES aes = SecureUtil.aes(encKey.getBytes());
            String dbPasswordEnc = aes.encryptHex(database.getDbPassword());
            database.setDbPassword(dbPasswordEnc);
        }
        return dbDatabaseRepository.updateById(database);
    }

    @Override
    public Page<TLDatabase> page(DataSourceTypeEnum dataSourceTypeEnum, Long pageNo, Long pageSize, String fuzzyWord, String userName, Boolean includingCreator) {
        return dbDatabaseRepository.page(dataSourceTypeEnum, pageNo, pageSize, fuzzyWord, userName, includingCreator);
    }

    @Override
    public Page<TLDatabase> pageByTargetIds(List<Long> targetIds, Long pageNo, Long pageSize, String fuzzyWord, Boolean includingCreator) {
        return dbDatabaseRepository.pageByTargetIds(targetIds, pageNo, pageSize, fuzzyWord, includingCreator);
    }

    @Override
    public TLDatabase findById(Long id) {
        TLDatabase db = dbDatabaseRepository.findById(id);
        return db;
    }

    @Override
    public TLDatabase findByIdOfDec(Long id) {
        TLDatabase tlDatabase = dbDatabaseRepository.findById(id);
        if (tlDatabase != null && tlDatabase.getDbPassword() != null && !"".equals(tlDatabase.getDbPassword())) {
            String dbPassword = tlDatabase.getDbPassword();
            AES aes = SecureUtil.aes(encKey.getBytes());
            String dbPasswordDec = aes.decryptStr(dbPassword);
            tlDatabase.setDbPassword(dbPasswordDec);
        }

        return tlDatabase;
    }

    @Override
    public Boolean deleteById(Long id) {
        return dbDatabaseRepository.removeById(id);
    }

    @Override
    public Integer getHighestPermission(Long databaseId) {
        UserInfoDTO userInfo = authUserClient.getUserInfoById(Long.valueOf(UserContext.getUser().getUserId()));
        Long deptId = StringUtils.isEmpty(userInfo.getDeptId()) ? null : Long.valueOf(userInfo.getDeptId());
        return dbDatabaseRepository.getHighestPermission(databaseId, deptId, userInfo.getId(), userInfo.getUserName());
    }
}
