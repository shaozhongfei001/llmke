package com.gientech.ragcommon.library;

import lombok.extern.slf4j.Slf4j;
import org.ansj.dic.PathToStream;
import org.ansj.exception.LibraryException;
import org.apache.commons.lang3.StringUtils;

import java.io.InputStream;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/8/30 11:04
 */
@Slf4j
public class ClassPath2Stream extends PathToStream {
    @Override
    public InputStream toStream(String path) {
        //获取当前路径
        ClassLoader classLoader = getClass().getClassLoader();
        path = path.substring(8).split("\\|")[1];
        if (StringUtils.isNotBlank(path)) {
            return classLoader.getResourceAsStream(path);
        }
        throw new LibraryException(" path :" + path + " not found or can not to read");
    }
}
