package com.gientech.ragcommon.global;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.BusinessException;
import com.google.common.collect.Lists;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import lombok.NonNull;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.util.CollectionUtils;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.validation.ObjectError;
import org.springframework.validation.method.MethodValidationException;
import org.springframework.validation.method.ParameterErrors;
import org.springframework.validation.method.ParameterValidationResult;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyAdvice;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;


/**
 * @Description:
 * @Author: ws
 * @Date: 2024/5/27 15:43
 */
@RestControllerAdvice(annotations = RestController.class)
@Slf4j
public class GlobalHandler implements ResponseBodyAdvice<Object> {

    private ArrayList<String> noConvertUrl = Lists.newArrayList("/v3/api-docs/swagger-config", "/v3/api-docs", "/authenticate", "/faq/downloadTemplate","/ai/questionForCZBank","/word/downloadTemplate");

    /**
     * Global capture parameter exception
     *
     * @param ex MethodArgumentNotValidException
     * @return
     */
    @ResponseBody
    @ExceptionHandler(value = MethodArgumentNotValidException.class)
    public CommonResponse bindException(MethodArgumentNotValidException ex) {
        BindingResult bindingResult = ex.getBindingResult();
        String errorMessage = "";
        if (bindingResult.getFieldErrors().size() > 0) {
            ObjectError error = bindingResult.getFieldErrors().get(0);
            String code = error.getCode();
            String msg = error.getDefaultMessage();
            String field = ((FieldError) error).getField();
            errorMessage = code + "[" + field + "]" + msg;
        }
        log.error("exception occur:{}", ex);
        return CommonResponse.fail(errorMessage, ErrCodeEnum.UNKNOWN.getErrCode());
    }

    @ResponseBody
    @ExceptionHandler(value = HandlerMethodValidationException.class)
    public CommonResponse handlerMethodValidationException(HandlerMethodValidationException ex) {
        List<ParameterValidationResult> allValidationResults = ex.getAllValidationResults();
        String errorMessage = CollectionUtils.isEmpty(allValidationResults)? ex.getReason():allValidationResults.stream().map(ParameterValidationResult::toString).collect(Collectors.joining(","));
        log.error("exception occur:{}", ex);
        return CommonResponse.fail(errorMessage, ErrCodeEnum.PARAM_VALID_FAILURE.getErrCode());
    }

    /**
     * Global capture ConstraintViolationException.class
     *
     * @param ex ConstraintViolationException
     * @return
     */
    @ResponseBody
    @ExceptionHandler(value = ConstraintViolationException.class)
    public CommonResponse ConstraintViolationExceptionHandler(ConstraintViolationException ex) {
        Set<ConstraintViolation<?>> set = ex.getConstraintViolations();
        String errorMessage = "";
        if (set.size() > 0) {
            errorMessage = set.iterator().next().getMessageTemplate();
        }
        log.error("exception occur:{}", ex);
        return CommonResponse.fail(ex.getMessage(), ErrCodeEnum.PARAM_VALID_FAILURE.getErrCode());
    }

    @ExceptionHandler(ApplicationException.class)
    public CommonResponse applicationExceptionHandle(ApplicationException e, HttpServletResponse response) {
        // R13-SEC-A1：权限不足是"拒绝"，不是"服务端故障"。
        // 原实现统一返回 500，导致前端/监控把越权拒绝误判为系统异常，也让负例断言失真。
        boolean denied = ErrCodeEnum.INSUFFICIENT_PERMISSIONS.getErrCode().equals(e.getErrCode());
        response.setStatus(denied ? HttpStatus.FORBIDDEN.value() : HttpStatus.INTERNAL_SERVER_ERROR.value());
        log.error("application exception occur:{}", e);
        return CommonResponse.fail(e.getMessage(), e.getErrCode());
    }

    @ExceptionHandler(BusinessException.class)
    public CommonResponse businessExceptionHandle(BusinessException e, HttpServletResponse response) {
        response.setStatus(HttpStatus.OK.value());
        log.error("business exception occur:{}", e);
        return CommonResponse.fail(e.getMessage(), e.getErrCode());
    }

    @ExceptionHandler(Exception.class)
    public CommonResponse exceptionHandle(Exception e, HttpServletResponse response) {
        response.setStatus(HttpStatus.INTERNAL_SERVER_ERROR.value());
        log.error("exception occur:{}", e);
        return CommonResponse.fail(e.getMessage(), ErrCodeEnum.UNKNOWN.getErrCode());
    }

    @Override
    public boolean supports(MethodParameter returnType, Class<? extends HttpMessageConverter<?>> converterType) {
        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = servletRequestAttributes.getRequest();
        String requestURI = request.getRequestURI();
        Boolean isConvert = true;
        for (String url : noConvertUrl) {
            if(requestURI.contains(url)){
                isConvert = false;
                break;
            }
        }
        return isConvert;
    }

    @Override
    public Object beforeBodyWrite(Object body, @NonNull MethodParameter returnType,
                                  @NonNull MediaType selectedContentType, @NonNull Class selectedConverterType,
                                  @NonNull ServerHttpRequest request, @NonNull ServerHttpResponse response) {
        boolean isFeignCall = request.getHeaders().containsKey("X-Feign-Client");
        boolean isStream = Objects.equals(response.getHeaders().getContentType(), MediaType.APPLICATION_OCTET_STREAM);
        if (isFeignCall || isStream) {
            return body;
        }

        if(body instanceof String) {
            try {
                return new ObjectMapper().writeValueAsString(CommonResponse.success(body));
            } catch (JsonProcessingException e) {
                log.error(e.getMessage());
            }
        }

        return (body instanceof CommonResponse) ? body : CommonResponse.success(body);
    }
}
