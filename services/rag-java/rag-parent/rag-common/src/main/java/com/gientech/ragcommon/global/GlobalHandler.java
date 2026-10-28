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

    /** R14-C-FIX-06：SSE 错误体手工序列化用。 */
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

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
    public CommonResponse applicationExceptionHandle(ApplicationException e, HttpServletRequest request,
                                                     HttpServletResponse response) {
        // R13-SEC-A1：权限不足是"拒绝"，不是"服务端故障"。
        // 原实现统一返回 500，导致前端/监控把越权拒绝误判为系统异常，也让负例断言失真。
        boolean denied = ErrCodeEnum.INSUFFICIENT_PERMISSIONS.getErrCode().equals(e.getErrCode());
        // R13-FIX-API-02：目标不存在属于客户端错误（404），不要伪装成 5xx；
        // 否则监控/前端无法区分"资源没了"和"服务端炸了"。
        boolean notFound = ErrCodeEnum.KB_NOT_EXISTS_ERROR.getErrCode().equals(e.getErrCode())
                || ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR.getErrCode().equals(e.getErrCode());
        // R14-C-FIX-15：配置缺失是客户端可修正的前置条件问题（400），既不伪装成 5xx 也不伪装成 403。
        boolean badRequest = ErrCodeEnum.DEFAULT_ASSISTANT_NOT_CONFIGURED.getErrCode().equals(e.getErrCode());
        // R14-LIVE-07：可预期的"用户输入/会话"错误必须是 4xx，不能伪装成 5xx。
        // 实测：验证码输错抛 ApplicationException(30000) -> 500，前端控制台/监控都把它当服务故障；
        // 同样 /file/stream 参数非法(5004) 也是 500，用户看到"PDF请求失败: 500"而非"参数不对"。
        boolean clientInput = ErrCodeEnum.VERIFY_CODE_ERROR.getErrCode().equals(e.getErrCode())
                || ErrCodeEnum.PARAM_ILLEGAL.getErrCode().equals(e.getErrCode())
                || ErrCodeEnum.PARAM_IS_NULL.getErrCode().equals(e.getErrCode());
        if (denied) {
            response.setStatus(HttpStatus.FORBIDDEN.value());
        } else if (notFound) {
            response.setStatus(HttpStatus.NOT_FOUND.value());
        } else if (badRequest || clientInput) {
            response.setStatus(HttpStatus.BAD_REQUEST.value());
        } else {
            response.setStatus(HttpStatus.INTERNAL_SERVER_ERROR.value());
        }
        log.error("application exception occur:{}", e);
        // R14-C-FIX-06：SSE 端点（produces=text/event-stream，如 /qa/ai/question）无法用 POJO 转换器
        // 写错误体，实测会退化成 "500 + 空 body"，拒绝态不可判定（违反 R14-F08 口径）。
        // 这里对 Accept 含 text/event-stream 的请求显式写 JSON 错误体（HTTP 状态仍是 403/404/500）。
        if (wantsEventStream(request)) {
            try {
                response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                response.setCharacterEncoding("UTF-8");
                String body = OBJECT_MAPPER.writeValueAsString(CommonResponse.fail(e.getMessage(), e.getErrCode()));
                response.getWriter().write(body);
                response.getWriter().flush();
                return null;
            } catch (Exception ignore) {
                // 写不出去就退回默认处理，不掩盖原始异常
            }
        }
        return CommonResponse.fail(e.getMessage(), e.getErrCode());
    }

    /** Accept 里带 text/event-stream 的请求走"手工写 JSON 错误体"分支。 */
    private boolean wantsEventStream(HttpServletRequest request) {
        if (request == null) {
            return false;
        }
        String accept = request.getHeader("Accept");
        return accept != null && accept.toLowerCase().contains("text/event-stream");
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
        // R13-PV-03：二进制响应（PDF 预览、文件下载）不能被包装成 CommonResponse，
        // 否则 Spring 会把 CommonResponse 强转成 byte[] 抛 ClassCastException（500）。
        boolean isBinary = body instanceof byte[]
                || MediaType.APPLICATION_PDF.equals(selectedContentType)
                || MediaType.APPLICATION_OCTET_STREAM.equals(selectedContentType);
        if (isFeignCall || isStream || isBinary) {
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
