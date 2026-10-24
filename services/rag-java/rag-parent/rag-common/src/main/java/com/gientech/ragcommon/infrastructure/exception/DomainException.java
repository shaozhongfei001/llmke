package com.gientech.ragcommon.infrastructure.exception;

import com.gientech.ragcommon.global.ErrCodeEnum;

/**
 * @Descrption:
 * @Author: ws
 * @Date: 2024/5/27 15:43
 **/
public class DomainException extends RuntimeException {

    private String errCode;
    private String message;

    public DomainException(String errCode, String message) {
        super(message);
        this.errCode = errCode;
        this.message = message;
    }

    public DomainException(String errCode, String message, Exception ex) {
        super(message,ex);
        this.errCode = errCode;
        this.message = message;
    }

    public DomainException(String message) {
        super(message);
        this.errCode = ErrCodeEnum.UNKNOWN.getErrCode();
        this.message = message;
    }

    public DomainException(ErrCodeEnum errCodeEnum) {
        super(errCodeEnum.getErrMsg());
        this.errCode = errCodeEnum.getErrCode();
        this.message = errCodeEnum.getErrMsg();
    }

    public DomainException(ErrCodeEnum errCodeEnum, Exception ex) {
        super(errCodeEnum.getErrMsg());
        this.errCode = errCodeEnum.getErrCode();
        this.message = errCodeEnum.getErrMsg();
    }

    public String getErrCode() {
        return errCode;
    }

    public String getMessage() {
        return message;
    }
}
