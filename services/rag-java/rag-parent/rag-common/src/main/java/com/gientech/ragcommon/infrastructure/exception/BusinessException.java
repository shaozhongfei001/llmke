package com.gientech.ragcommon.infrastructure.exception;

import com.gientech.ragcommon.global.ErrCodeEnum;
import lombok.Getter;

/**
 * @author: shirleychen
 * @date 2025/9/15 15:31
 * @description
 */
@Getter
public class BusinessException extends RuntimeException {

    private String errCode;
    private String message;

    public BusinessException(String errCode, String message) {
        this.errCode = errCode;
        this.message = message;
    }

    public BusinessException(String message) {
        this.message = message;
        this.errCode = ErrCodeEnum.UNKNOWN.getErrCode();
    }


    public BusinessException(Throwable cause, String errCode, String message) {
        super(cause);
        this.errCode = errCode;
        this.message = message;
    }

    public BusinessException(ErrCodeEnum errCodeEnum) {
        this.errCode = errCodeEnum.getErrCode();
        this.message = errCodeEnum.getErrMsg();
    }
}
