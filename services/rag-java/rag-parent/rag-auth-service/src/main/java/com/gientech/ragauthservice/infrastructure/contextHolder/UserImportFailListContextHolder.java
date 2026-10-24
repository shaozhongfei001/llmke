package com.gientech.ragauthservice.infrastructure.contextHolder;

import cn.hutool.core.collection.CollUtil;
import com.gientech.ragcommon.auth.dto.UserImportDTO;
import com.google.common.collect.Lists;

import java.util.List;
import java.util.Optional;

public class UserImportFailListContextHolder {
    private static final ThreadLocal<List<UserImportDTO>> contextHolder = new ThreadLocal<>();

    public static void setUserImportFailList(List<UserImportDTO> failList) {
        List<UserImportDTO> existFailList = Optional.ofNullable(getUserImportFailList()).orElse(Lists.newArrayList());
        if (CollUtil.isNotEmpty(failList))
            existFailList.addAll(failList);
        contextHolder.set(existFailList);
    }

    public static void setUserImportFailList(UserImportDTO userImportDTO) {
        List<UserImportDTO> existFailList = Optional.ofNullable(getUserImportFailList()).orElse(Lists.newArrayList());
        existFailList.add(userImportDTO);
        contextHolder.set(existFailList);
    }

    public static List<UserImportDTO> getUserImportFailList() {
        return contextHolder.get();
    }

    public static void clear() {
        contextHolder.remove();
    }
}