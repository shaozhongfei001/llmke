package com.gientech.ragcommon.feign;

import com.alibaba.fastjson2.JSON;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import feign.Request;
import feign.Response;
import feign.Util;
import feign.codec.ErrorDecoder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/5/27 15:43
 */
@Configuration
@Slf4j
public class FeignErrorDecode implements ErrorDecoder {

    @Override
    public Exception decode(String methodKey, Response response) {
        log.info("methodKey:{}", methodKey);
        log.info("status:{}", response.status());

        if (response.status() >= HttpStatus.BAD_REQUEST.value() && response.status() <= HttpStatus.INTERNAL_SERVER_ERROR.value()) {
            //抛出自定义异常，走全局异常处理
            try {
                String responseBody = Util.toString(response.body().asReader(StandardCharsets.UTF_8));
                Request request = response.request();
                if (request.headers().containsKey("X-Python-Label-Client")) {
                    return new ApplicationException(ErrCodeEnum.PY_LABEL_ERROR.getErrCode(), responseBody);
                }
                CommonResponse commonResponse = JSON.parseObject(responseBody, CommonResponse.class);
                return new ApplicationException(commonResponse.getErrorCode(), commonResponse.getErrorMsg());
            } catch (IOException e) {
                log.error(e.getMessage());
                throw new ApplicationException(e.getMessage());
            }
        }
        return feign.FeignException.errorStatus(methodKey, response);
    }
}
