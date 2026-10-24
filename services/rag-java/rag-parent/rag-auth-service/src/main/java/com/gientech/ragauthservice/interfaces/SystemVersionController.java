package com.gientech.ragauthservice.interfaces;

import cn.hutool.core.bean.BeanUtil;
import com.gientech.ragauthservice.infrastructure.SystemVersionConfig;
import com.gientech.ragcommon.auth.dto.SystemVersionDTO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Objects;

/**
 * @Descrption: 系统版本信息
 * @Author:liutaiyun
 * @Date:2024/08/27 14:12
 **/

@Tag(name = "系统版本")
@RestController
@RequestMapping("/version")
public class SystemVersionController {

    @Autowired
    public SystemVersionConfig systemVersionConfig;

    @Operation(summary = "查询当前版本")
    @GetMapping ("/getCurrentVersion")
    public SystemVersionDTO getCurrentVersion() {
        if (Objects.isNull(systemVersionConfig) || StringUtils.isBlank(systemVersionConfig.getVersion())) {
            SystemVersionDTO version = new SystemVersionDTO();
            version.setVersion("V1.0");
            version.setSubVersion("0");
            version.setDetail("知识问答服务");
            version.setDate("2024/04/01");
            return version;
        }

        return BeanUtil.copyProperties(systemVersionConfig, SystemVersionDTO.class);
    }
}
