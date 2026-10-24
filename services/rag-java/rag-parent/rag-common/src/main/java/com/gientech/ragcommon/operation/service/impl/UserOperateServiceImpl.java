package com.gientech.ragcommon.operation.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.operation.mapper.UserOperateDOMapper;
import com.gientech.ragcommon.operation.model.UserOperateDO;
import com.gientech.ragcommon.operation.service.UserOperateService;
import org.springframework.stereotype.Service;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/12/24 11:22
 **/
@Service
public class UserOperateServiceImpl extends ServiceImpl<UserOperateDOMapper, UserOperateDO> implements UserOperateService {
}
