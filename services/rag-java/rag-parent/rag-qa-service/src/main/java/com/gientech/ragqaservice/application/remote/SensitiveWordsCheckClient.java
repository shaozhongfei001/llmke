package com.gientech.ragqaservice.application.remote;


import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.sensitive.request.HitSensitiveWordRequest;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(name = "sensitive-words-service", path = "sensitive/word", configuration = FeignCustomConfig.class)
public interface SensitiveWordsCheckClient {
    @PostMapping("/checkHitSensitiveWord")
    Boolean checkHitSensitiveWord(@RequestBody HitSensitiveWordRequest wordRequest);
}
