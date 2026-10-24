package com.gientech.ragqaservice.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.sensitive.dto.SensitiveWordsDTO;
import org.apache.skywalking.apm.toolkit.trace.Trace;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/8/28 11:39
 */
@FeignClient(name = "sensitive-words-service", path = "sensitive/library", configuration = FeignCustomConfig.class)
public interface SensitiveWordsClient {
    @Trace
    @GetMapping("/getListByIds")
    List<SensitiveWordsDTO> getListByIds(@RequestParam("ids") Long[] ids);
}
