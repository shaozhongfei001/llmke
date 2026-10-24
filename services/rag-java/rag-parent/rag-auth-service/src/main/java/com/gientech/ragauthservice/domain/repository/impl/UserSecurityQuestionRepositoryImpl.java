package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragauthservice.domain.entity.UserSecurityQuestion;
import com.gientech.ragauthservice.domain.mapper.UserSecurityQuestionMapper;
import com.gientech.ragauthservice.domain.model.UserSecurityQuestionDO;
import com.gientech.ragauthservice.domain.repository.UserSecurityQuestionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import java.util.Date;
import java.util.List;

@Repository
public class  UserSecurityQuestionRepositoryImpl implements  UserSecurityQuestionRepository {

    @Autowired
    private  UserSecurityQuestionMapper  userSecurityQuestionMapper;

    @Override
    public Long countByUserId(Long userId) {
        QueryWrapper<UserSecurityQuestionDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", userId);

        Long count = userSecurityQuestionMapper.selectCount(queryWrapper);
        return count;
    }

    @Override
    public List<UserSecurityQuestion> findByUserId(Long userId) {
        QueryWrapper<UserSecurityQuestionDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", userId);

        List<UserSecurityQuestionDO> userSecurityQuestionDOList = userSecurityQuestionMapper.selectList(queryWrapper);
        List<UserSecurityQuestion> userSecurityQuestionList = BeanUtil.copyToList(userSecurityQuestionDOList, UserSecurityQuestion.class);

        return userSecurityQuestionList;
    }

    @Override
    public Boolean save(UserSecurityQuestion userSecurityQuestion) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        userSecurityQuestion.setUpdateBy(userName);
        userSecurityQuestion.setCreateBy(userName);
        userSecurityQuestion.setGmtCreate(new Date());
        userSecurityQuestion.setGmtModified(userSecurityQuestion.getGmtCreate());
        return userSecurityQuestionMapper.insert(BeanUtil.copyProperties(userSecurityQuestion, UserSecurityQuestionDO.class)) > 0;
    }

    @Override
    public Boolean deleteByUserId(Long userId) {
        QueryWrapper<UserSecurityQuestionDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", userId);

        return userSecurityQuestionMapper.delete(queryWrapper) > 0;
    }
}
