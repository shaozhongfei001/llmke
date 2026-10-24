package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.date.DateUtil;
import com.alibaba.excel.support.ExcelTypeEnum;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragauthservice.application.helper.UserOperateExportHelper;
import com.gientech.ragauthservice.application.service.UserOperateAppService;
import com.gientech.ragauthservice.domain.entity.UserOperate;
import com.gientech.ragauthservice.domain.service.UserOperateDomainService;
import com.gientech.ragcommon.auth.dto.UserOperateDTO;
import com.gientech.ragcommon.auth.dto.UserOperateExportDTO;
import com.gientech.ragcommon.auth.request.SaveUserOperateReq;
import com.gientech.ragcommon.auth.request.UpdateUserOperateReq;
import com.gientech.ragcommon.auth.request.UserOperateQueryReq;
import com.gientech.ragcommon.infrastructure.page.PageExt;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import jakarta.servlet.http.HttpServletResponse;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

@Service
public class UserOperateAppServiceImpl implements UserOperateAppService {

    @Autowired
    private UserOperateDomainService userOperateDomainService;

    @Autowired
    private UserOperateExportHelper userOperateExportHelper;

    @Override
    public UserOperateDTO findById(Long id) {
        if(Objects.isNull(id))
            return null;
        UserOperate byId = userOperateDomainService.findById(id);
        return BeanUtil.copyProperties(byId,UserOperateDTO.class);
    }

    @Override
    public Boolean save(SaveUserOperateReq userOperateReq) {
        if(Objects.isNull(userOperateReq))
            return false;
       return userOperateDomainService.save(BeanUtil.copyProperties(userOperateReq,UserOperate.class));
    }

    @Override
    public Boolean updateById(UpdateUserOperateReq userOperateReq) {
        if(Objects.isNull(userOperateReq))
            return false;
        return userOperateDomainService.updateById(BeanUtil.copyProperties(userOperateReq,UserOperate.class));
    }

    @Override
    public PageExt<UserOperateDTO> list(UserOperateQueryReq queryReq) {
        Page<UserOperate> page = userOperateDomainService.list(queryReq);
        PageExt<UserOperateDTO> result = new PageExt<>();
        BeanUtil.copyProperties(page,result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(),UserOperateDTO.class));
        //查询失败的数据
        result.setFailTotal(userOperateDomainService.queryfailTotal(queryReq));
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        if(Objects.isNull(id))
            return false;
        return userOperateDomainService.deleteById(id);
    }

    @Override
    public void exportUserOperate(String fuzzy, String start, String end, HttpServletResponse response) {
        List<UserOperate> userOperateList = userOperateDomainService.queryByCondition(
                fuzzy, start, end);
        List<UserOperateExportDTO> userOperateDTOList = BeanUtil.copyToList(userOperateList, UserOperateExportDTO.class);

        userOperateExportHelper.exportData(
                "用户操作记录" + DateUtil.format(new Date(),"yyyyMMddHHmmss"),
                userOperateDTOList,
                UserOperateExportDTO.class,
                ExcelTypeEnum.valueOf("xlsx".toUpperCase(Locale.ROOT)),
                response);
    }
}
