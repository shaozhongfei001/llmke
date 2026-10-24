package com.gientech.ragauthservice.application.service;

import com.alibaba.fastjson.JSON;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * @author chenjuan
 * @date 2025/3/20 13:15
 */
@SpringBootTest
public class DepartmentInfoTest {

    @Autowired
    private DepartmentInfoAppService departmentInfoAppService;

    @Autowired
    private GroupAppService groupAppService;

    @Test
    void test() {
        System.out.println(JSON.toJSONString(groupAppService.treeGroup()));
    }
}
