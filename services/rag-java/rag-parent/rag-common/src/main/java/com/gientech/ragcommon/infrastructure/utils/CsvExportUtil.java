package com.gientech.ragcommon.infrastructure.utils;

import cn.hutool.core.util.ObjectUtil;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;

import java.io.*;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Map;

@Slf4j
public class CsvExportUtil {
    /**
     * CSV文件列分隔符
     */
    private static final String CSV_COLUMN_SEPARATOR = ",";

    /**
     * CSV文件行分隔符
     */
    private static final String CSV_ROW_SEPARATOR = System.lineSeparator();

    /**
     * @param dataList 集合数据
     * @param titles   表头部数据
     * @param keys     表内容的键值
     * @param os       输出流
     */
    public static void doExport(List<Map<String, Object>> dataList, String[] titles, String keys, OutputStream os) throws Exception {
        StringBuffer buf = new StringBuffer();
        String[] keyArr = null;
        keyArr = keys.split(",");
        // 组装表头
        for (String title : titles) {
            buf.append(title).append(CSV_COLUMN_SEPARATOR);
        }
        buf.append(CSV_ROW_SEPARATOR);

        // 组装数据
        if (CollectionUtils.isNotEmpty(dataList)) {
            for (Map<String, Object> data : dataList) {
                for (String key : keyArr) {
                    if (key.equals("TmplateJson") || key.equals("code") || key.equals("input") || key.equals("output")) {
                        if (ObjectUtil.isEmpty(data.get(key))) {
                            buf.append(data.get(key)).append(CSV_COLUMN_SEPARATOR);
                        } else {
                            String replace = data.get(key).toString().replaceAll(",", "!");
                            StringBuffer append = buf.append(data.get(key).toString().replaceAll(",", "!")).append(CSV_COLUMN_SEPARATOR);
                        }
                    } else {
                        if (ObjectUtil.isEmpty(data.get(key))) {
                            buf.append("").append(CSV_COLUMN_SEPARATOR);
                        } else {
                            buf.append(data.get(key)).append(CSV_COLUMN_SEPARATOR);
                        }
                    }
                }
                buf.append(CSV_ROW_SEPARATOR);
            }
        }
        // 写出响应
        os.write(buf.toString().getBytes("UTF-8"));
        os.flush();
    }

    /**
     * 设置Header
     *
     * @param fileName
     * @param response
     * @throws
     */
    public static void responseSetProperties(String fileName, HttpServletResponse response) throws UnsupportedEncodingException {
        // 设置文件后缀
        SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMddHHmmss");
        String fn = fileName + sdf.format(new Date()) + ".xlsx";
        // 读取字符编码
        String utf = "UTF-8";
        // 设置响应
        response.setContentType("application/ms-txt.numberformat:@");
        response.setCharacterEncoding(utf);
        response.setHeader("Pragma", "public");
        response.setHeader("Cache-Control", "max-age=30");
        response.setHeader("Content-Disposition", "attachment; filename=" + URLEncoder.encode(fn, utf));
    }

}
