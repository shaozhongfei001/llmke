package com.gientech.start.storage.exception;

/** 文件存储异常（R12 兼容实现）。 */
public class FileStorageException extends RuntimeException {

    public FileStorageException(String message) {
        super(message);
    }

    public FileStorageException(String message, Throwable cause) {
        super(message, cause);
    }
}
