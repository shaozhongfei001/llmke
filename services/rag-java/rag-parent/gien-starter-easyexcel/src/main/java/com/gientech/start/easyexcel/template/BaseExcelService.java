package com.gientech.start.easyexcel.template;

import com.alibaba.excel.EasyExcel;
import com.alibaba.excel.context.AnalysisContext;
import com.alibaba.excel.read.listener.ReadListener;
import com.alibaba.excel.support.ExcelTypeEnum;
import com.gientech.start.easyexcel.result.ExcelImportResult;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Excel 导入导出模板基类（R12 兼容实现）。
 * 语义：
 *  - importData 读取全部行后交给 handlerSuccessList 做业务校验/落库；
 *    失败行由子类写入传入的 failList（objects 透传）。
 *  - exportData 按 DTO 上的 @ExcelProperty 输出；data 为 null 时输出表头模板。
 * 见 docs/r12/ADAPTATIONS.md#A-02。
 */
public abstract class BaseExcelService<T> {

    protected abstract void handlerSuccessList(List<T> list, Object... objects);

    protected abstract void handlerFailList(List<T> list, Object... objects);

    public ExcelImportResult<T> importData(MultipartFile file, Class<T> clazz) {
        return importData(file, clazz, new Object[0]);
    }

    public ExcelImportResult<T> importData(MultipartFile file, Class<T> clazz, Object... objects) {
        List<T> rows = read(file, clazz);
        ExcelImportResult<T> result = new ExcelImportResult<>();
        result.setTotal(rows.size());

        handlerSuccessList(rows, objects);

        List<T> failList = extractFailList(objects);
        result.setFailList(failList);
        result.setSuccessList(new ArrayList<>(rows));
        if (!failList.isEmpty()) {
            handlerFailList(failList, objects);
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private List<T> extractFailList(Object... objects) {
        if (objects != null) {
            for (int i = objects.length - 1; i >= 0; i--) {
                if (objects[i] instanceof List<?> l) {
                    return (List<T>) l;
                }
            }
        }
        return new ArrayList<>();
    }

    private List<T> read(MultipartFile file, Class<T> clazz) {
        List<T> rows = new ArrayList<>();
        if (file == null || file.isEmpty()) {
            return rows;
        }
        try {
            EasyExcel.read(file.getInputStream(), clazz, new ReadListener<T>() {
                @Override
                public void invoke(T data, AnalysisContext context) {
                    rows.add(data);
                }

                @Override
                public void doAfterAllAnalysed(AnalysisContext context) {
                    // no-op
                }
            }).sheet().doRead();
        } catch (IOException e) {
            throw new IllegalStateException("读取 Excel 失败: " + file.getOriginalFilename(), e);
        }
        return rows;
    }

    public void exportData(String fileName, List<T> data, Class<T> clazz, ExcelTypeEnum type,
                           HttpServletResponse response) {
        try {
            String name = URLEncoder.encode(fileName == null ? "export" : fileName, StandardCharsets.UTF_8)
                    .replace("+", "%20");
            response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            response.setHeader("Content-Disposition",
                    "attachment;filename=" + name + "." + (type == null ? "xlsx" : type.getValue()));
            List<T> rows = data == null ? new ArrayList<>() : data;
            EasyExcel.write(response.getOutputStream(), clazz)
                    .excelType(type == null ? ExcelTypeEnum.XLSX : type)
                    .sheet(fileName == null ? "sheet1" : fileName)
                    .doWrite(rows);
        } catch (IOException e) {
            throw new IllegalStateException("导出 Excel 失败: " + fileName, e);
        }
    }
}
