package com.gientech.ragcommon.infrastructure.exception;

import com.gientech.ragcommon.global.ErrCodeEnum;
import lombok.Setter;

/**
 * @Description: 应用层异常
 * @Author: ws
 * @Date: 2024/5/27 15:43
 */
public class ApplicationException extends RuntimeException {

    private String errCode;
    @Setter
    private String message;

    public ApplicationException(String errCode, String message) {
        super(message);
        this.errCode = errCode;
        this.message = message;
    }

    public ApplicationException(String errCode, String message, Exception ex) {
        super(message,ex);
        this.errCode = errCode;
        this.message = message;
    }

    public ApplicationException(String message) {
        super(message);
        this.errCode = ErrCodeEnum.UNKNOWN.getErrCode();
        this.message = message;
    }

    public ApplicationException(ErrCodeEnum errCodeEnum) {
        super(errCodeEnum.getErrMsg());
        this.errCode = errCodeEnum.getErrCode();
        this.message = errCodeEnum.getErrMsg();
    }
    public ApplicationException(ErrCodeEnum errCodeEnum, String additionalMsg) {
        super(errCodeEnum.getErrMsg());
        this.errCode = errCodeEnum.getErrCode();
        this.message = errCodeEnum.getErrMsg() + ":" + additionalMsg;
    }

    public ApplicationException(ErrCodeEnum errCodeEnum, Exception ex) {
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
