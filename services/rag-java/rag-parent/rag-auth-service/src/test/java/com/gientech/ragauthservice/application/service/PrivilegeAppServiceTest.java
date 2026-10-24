package com.gientech.ragauthservice.application.service;

import com.alibaba.fastjson.JSON;
import com.gientech.ragcommon.index.dto.Collaborator;
import lombok.extern.slf4j.Slf4j;
import org.checkerframework.checker.units.qual.A;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/3/14 16:36
 */
@SpringBootTest
@Slf4j
public class PrivilegeAppServiceTest {
    @Autowired
    private PrivilegeAppService privilegeAppService;


    @Test
    public void test(){
//        List<Collaborator> userListGroupByPermission = privilegeAppService.getUserListGroupByPermission(1, 1536L);
//        log.info(JSON.toJSONString(userListGroupByPermission));
    }


}
