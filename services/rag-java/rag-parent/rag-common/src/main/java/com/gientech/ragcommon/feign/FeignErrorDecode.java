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
                // V2/B1-D01b：下游 500 且响应体为空时，原实现 JSON.parseObject("") 得到 null，
                // 随后 commonResponse.getErrorCode() 抛出 "Cannot parse null string"，
                // 把"未授权/服务异常"掩盖成"解析失败"，排查时指向完全错误的方向（实测踩过）。
                // 这里显式区分：空体/null 一律返回带 methodKey 与 HTTP 状态的明确原因。
                if (responseBody == null || responseBody.isBlank()) {
                    log.error("feign 下游返回空响应体, methodKey:{}, status:{}", methodKey, response.status());
                    return new ApplicationException(ErrCodeEnum.INTERIOR_ERROR.getErrCode(),
                            "下游服务返回空响应体: " + methodKey + " HTTP " + response.status());
                }
                CommonResponse commonResponse;
                try {
                    commonResponse = JSON.parseObject(responseBody, CommonResponse.class);
                } catch (RuntimeException parseError) {
                    // 下游返回 HTML / 纯文本错误页时，fastjson 抛 JSONException 会盖掉真实状态码
                    log.error("feign 下游响应不是 JSON, methodKey:{}, status:{}, body:{}", methodKey,
                            response.status(), responseBody.substring(0, Math.min(200, responseBody.length())));
                    return new ApplicationException(ErrCodeEnum.INTERIOR_ERROR.getErrCode(),
                            "下游响应非 JSON: " + methodKey + " HTTP " + response.status());
                }
                if (commonResponse == null) {
                    log.error("feign 下游响应无法解析为 CommonResponse, methodKey:{}, body:{}",
                            methodKey, responseBody.substring(0, Math.min(200, responseBody.length())));
                    return new ApplicationException(ErrCodeEnum.INTERIOR_ERROR.getErrCode(),
                            "下游响应无法解析: " + methodKey + " HTTP " + response.status());
                }
                return new ApplicationException(commonResponse.getErrorCode(), commonResponse.getErrorMsg());
            } catch (IOException e) {
                log.error(e.getMessage());
                throw new ApplicationException(e.getMessage());
            }
        }
        return feign.FeignException.errorStatus(methodKey, response);
    }
}
