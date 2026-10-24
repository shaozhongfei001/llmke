package com.gientech.ragauthservice.application.helper;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.service.DepartmentInfoDomainService;
import com.gientech.ragcommon.auth.dto.DeptImportExportDTO;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums;
import com.gientech.start.easyexcel.template.BaseExcelService;
import com.gientech.start.redisson.utils.RedissonUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

@Component
public class DeptImportExportHelper extends BaseExcelService<DeptImportExportDTO> {

    @Autowired
    private DepartmentInfoDomainService departmentInfoDomainService;

    @Autowired
    private RedissonUtils redissonUtils;

    private final static Long DEPT_IMPORT_DATA_ERROR_EXPIRE = 3L;



    @Override
    protected void handlerSuccessList(List<DeptImportExportDTO> list, Object... objects) {
        if (CollectionUtils.isEmpty(list))
            return;

        List<DepartmentInfo> deptList = (List<DepartmentInfo>) objects[0];
        List<DeptImportExportDTO> failList = (List<DeptImportExportDTO>) objects[1];

        list.forEach(item -> {
            if (Objects.isNull(departmentInfoDomainService.findByParentNameAndName(item.getParentDeptName(), item.getName()))) {
                DepartmentInfo parentDept = departmentInfoDomainService.findByName(item.getParentDeptName());
                if (Objects.isNull(parentDept)) {
                    item.setErrorMsg(ErrCodeEnum.PARENT_DEPT_NOT_EXIST.getErrMsg());
                    failList.add(item);
                } else {
                    item.setParentId(parentDept.getId());
                    deptList.add(BeanUtil.copyProperties(item, DepartmentInfo.class));
                }
            }
        });
        departmentInfoDomainService.saveBatch(deptList);
    }

    @Override
    protected void handlerFailList(List<DeptImportExportDTO> list, Object... objects) {
        if (CollectionUtils.isEmpty(list))
            return;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        redissonUtils.set(RedisKeyEnums.DEPT_IMPORT_DATA_ERROR_PREFIX + userName, JSON.toJSONString(list), DEPT_IMPORT_DATA_ERROR_EXPIRE, TimeUnit.HOURS);
    }
}
