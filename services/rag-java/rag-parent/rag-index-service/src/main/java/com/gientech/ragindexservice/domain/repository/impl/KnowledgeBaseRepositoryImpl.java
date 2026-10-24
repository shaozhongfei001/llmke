package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.KbStatusEnums;
import com.gientech.ragcommon.index.enmus.KbTypeEnums;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
import com.gientech.ragindexservice.domain.mapper.KnowledgeBaseMapper;
import com.gientech.ragindexservice.domain.model.KnowledgeBaseDO;
import com.gientech.ragindexservice.domain.repository.KnowledgeBaseRepository;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
@Slf4j
public class KnowledgeBaseRepositoryImpl implements KnowledgeBaseRepository {

    @Autowired
    private KnowledgeBaseMapper knowledgeBaseMapper;

    @Override
    public KnowledgeBase findByKbName(String kbName, String userName) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_name", kbName);
        if (StringUtils.isNotBlank(userName))
            queryWrapper.eq("create_by", userName);
        queryWrapper.eq("status", KbStatusEnums.NORMAL.getValue())
                .last("limit 1 ");
        KnowledgeBaseDO knowledgeBaseDO = knowledgeBaseMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseDO) ? null : BeanUtil.copyProperties(knowledgeBaseDO, KnowledgeBase.class);
    }

    @Override
    public KnowledgeBase findByKbName(String kbName, String userName, String platform) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_name", kbName);
        queryWrapper.eq("platform", platform);
        if (StringUtils.isNotBlank(userName))
            queryWrapper.eq("create_by", userName);
        queryWrapper.eq("status", KbStatusEnums.NORMAL.getValue())
                .last("limit 1 ");
        KnowledgeBaseDO knowledgeBaseDO = knowledgeBaseMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseDO) ? null : BeanUtil.copyProperties(knowledgeBaseDO, KnowledgeBase.class);
    }

    @Override
    public KnowledgeBase findByPrimitiveName(String primitiveName, String userName) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("primitive_name", primitiveName);
        if (StringUtils.isNotBlank(userName))
            queryWrapper.eq("create_by", userName);
        queryWrapper.eq("status", KbStatusEnums.NORMAL.getValue())
                .last("limit 1 ");
        KnowledgeBaseDO knowledgeBaseDO = knowledgeBaseMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseDO) ? null : BeanUtil.copyProperties(knowledgeBaseDO, KnowledgeBase.class);
    }

    @Override
    public List<KnowledgeBase> findByPrimitiveNames(List<String> primitiveNames) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("primitive_name", primitiveNames);
        queryWrapper.eq("status", KbStatusEnums.NORMAL.getValue());
        List<KnowledgeBaseDO> knowledgeBaseDOs = knowledgeBaseMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseDOs) ? null : BeanUtil.copyToList(knowledgeBaseDOs, KnowledgeBase.class);
    }

    @Override
    public KnowledgeBase findByPrimitiveName(String primitiveName, String userName, String platform) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("primitive_name", primitiveName);
        queryWrapper.eq("platform", platform);
        if (StringUtils.isNotBlank(userName))
            queryWrapper.eq("create_by", userName);
        queryWrapper.eq("status", KbStatusEnums.NORMAL.getValue())
                .last("limit 1 ");
        KnowledgeBaseDO knowledgeBaseDO = knowledgeBaseMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseDO) ? null : BeanUtil.copyProperties(knowledgeBaseDO, KnowledgeBase.class);
    }

    @Override
    public KnowledgeBase findById(Long id) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id", id)
                .eq("status", KbStatusEnums.NORMAL.getValue())
                .last("limit 1");
        KnowledgeBaseDO knowledgeBaseDO = knowledgeBaseMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseDO) ? null : BeanUtil.copyProperties(knowledgeBaseDO, KnowledgeBase.class);
    }

    @Override
    public Long addKnowledgeBase(KnowledgeBase knowledgeBase) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        knowledgeBase.setStatus(KbStatusEnums.NORMAL.getValue());
        knowledgeBase.setCreateBy(userName);
        knowledgeBase.setModifyBy(userName);
        knowledgeBase.setGmtCreate(new Date());
        knowledgeBase.setGmtModified(knowledgeBase.getGmtCreate());
        KnowledgeBaseDO knowledgeBaseDO = BeanUtil.copyProperties(knowledgeBase, KnowledgeBaseDO.class);
        knowledgeBaseMapper.insert(knowledgeBaseDO);
        knowledgeBase.setId(knowledgeBaseDO.getId());
        return knowledgeBaseDO.getId();
    }

    @Override
    public int updateById(KnowledgeBase knowledgeBase) {
        knowledgeBase.setModifyBy(UserContext.getUser().getUserName());
        knowledgeBase.setGmtModified(new Date());
        KnowledgeBaseDO knowledgeBaseDO = BeanUtil.copyProperties(knowledgeBase, KnowledgeBaseDO.class);
        LambdaUpdateWrapper<KnowledgeBaseDO> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(KnowledgeBaseDO::getId, knowledgeBaseDO.getId());
//        knowledgeBaseDO.setPrimitiveName(null);
        return knowledgeBaseMapper.update(knowledgeBaseDO, wrapper);
//        return knowledgeBaseMapper.updateById(knowledgeBaseDO);
    }

    @Override
    public Page<KnowledgeBase> list(List<Long> kbIds, String fuzzy, Long pageNo, Long pageSize, String userName, String platform, boolean isSuperAdmin, Integer privateKb) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.ne("status", KbStatusEnums.DELETE.getValue());
        queryWrapper.eq("kb_type", KbTypeEnums.KB.getCode());
        queryWrapper.eq("platform", platform);
        if(Objects.nonNull(privateKb) && (privateKb == 0 || privateKb == 1)){
            queryWrapper.eq("private_kb", privateKb);
        }
        if (!CollectionUtils.isEmpty(kbIds)) {
            queryWrapper.in("id", kbIds);
            queryWrapper.ne(StringUtils.isBlank(userName), "create_by", UserContext.getUser().getUserName());
        } else {
            if (isSuperAdmin) {
                queryWrapper.ne(StringUtils.isNotBlank(userName), "create_by", userName);
            } else {
                queryWrapper.eq(StringUtils.isNotBlank(userName), "create_by", userName);
            }

        }

        if (StringUtils.isNotBlank(fuzzy)) {
            queryWrapper
                    .and(name -> name
                            .like("kb_name", fuzzy)
                            .or(id -> id.like("id", fuzzy))
                            .or(kbLabel -> kbLabel.like("kb_label", fuzzy))

                    );
        }
        queryWrapper.orderByDesc("gmt_create");
        Page<KnowledgeBaseDO> page = new Page<>(pageNo, pageSize);
        Page<KnowledgeBaseDO> pageResult = knowledgeBaseMapper.selectPage(page, queryWrapper);
        Page<KnowledgeBase> knowledgeBasePage = new Page<>();
        BeanUtil.copyProperties(pageResult, knowledgeBasePage);
        return knowledgeBasePage;
    }

    @Override
    public Page<KnowledgeBase> availableList(List<Long> kbIds, Long pageNo, Long pageSize) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.ne("status", KbStatusEnums.DELETE.getValue());
        queryWrapper.eq("kb_type", KbTypeEnums.KB.getCode());
        if (!CollectionUtils.isEmpty(kbIds)) {
            queryWrapper.in("id", kbIds);
        }
        queryWrapper.orderByDesc("gmt_create");
        Page<KnowledgeBaseDO> page = new Page<>(pageNo, pageSize);
        Page<KnowledgeBaseDO> pageResult = knowledgeBaseMapper.selectPage(page, queryWrapper);

        Page<KnowledgeBase> knowledgeBasePage = new Page<>();
        BeanUtil.copyProperties(pageResult, knowledgeBasePage);
        List<KnowledgeBase> knowledgeBaseList = BeanUtil.copyToList(pageResult.getRecords(), KnowledgeBase.class);
        knowledgeBasePage.setRecords(knowledgeBaseList);
        return knowledgeBasePage;
    }

    @Override
    public Integer getHighestPermission(Long kbId, Long deptId, Long userId, String userName) {
        Integer permission = knowledgeBaseMapper.getHighestPermission(kbId, deptId, userId, userName);
        return Objects.isNull(permission) ? 0 : permission;
    }

    @Override
    public int transferProperty(String owner, String receiver) {
        QueryWrapper<KnowledgeBaseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("create_by", owner);
        queryWrapper.ne("status", KbStatusEnums.DELETE.getValue());
        List<KnowledgeBaseDO> knowledgeBaseDOS = knowledgeBaseMapper.selectList(queryWrapper);
        if (!CollectionUtils.isEmpty(knowledgeBaseDOS)) {
            List<Long> ids = knowledgeBaseDOS.stream().map(KnowledgeBaseDO::getId).toList();
            return knowledgeBaseMapper.updateCreator(ids, receiver);
        }
        return 0;
    }

    public int replaceModel(String sourceModelName, String targetModelName) {
        return knowledgeBaseMapper.replaceModel( sourceModelName, targetModelName);
    }

    @Override
    public List<KnowledgeBase> selectUseSpecifiedModelKbList(String modelTypeName, String modelName) {
        List<KnowledgeBaseDO> knowledgeBaseDOS = knowledgeBaseMapper.selectUseSpecifiedModelKbList(modelTypeName, modelName);
        return BeanUtil.copyToList(knowledgeBaseDOS, KnowledgeBase.class);
    }

    @Override
    public int selectReferenceByModelName(String modelName) {
        return  knowledgeBaseMapper.selectReferenceByModelName(modelName);
    }

}
