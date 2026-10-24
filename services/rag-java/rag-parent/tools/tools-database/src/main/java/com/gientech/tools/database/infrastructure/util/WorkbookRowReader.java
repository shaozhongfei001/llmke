package com.gientech.tools.database.infrastructure.util;

import cn.hutool.poi.excel.sax.handler.RowHandler;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.openxml4j.exceptions.InvalidFormatException;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/9/9 16:08
 * @description
 */
public class WorkbookRowReader {

    /**
     * 使用 WorkbookFactory 遍历 Excel
     *
     * @param in          Excel 输入流（xls 或 xlsx）
     * @param sheetIndex  指定 sheet 序号，-1 表示全部 sheet
     * @param rowHandler  Hutool RowHandler 回调
     */
    public static void read(InputStream in, int sheetIndex, RowHandler rowHandler)
            throws IOException, InvalidFormatException {
        try (Workbook workbook = WorkbookFactory.create(in)) {
            int sheetCount = workbook.getNumberOfSheets();
            for (int i = 0; i < sheetCount; i++) {
                if (sheetIndex != -1 && i != sheetIndex) {
                    continue;
                }
                Sheet sheet = workbook.getSheetAt(i);
                for (Row row : sheet) {
                    List<Object> rowData = new ArrayList<>();
                    for (Cell cell : row) {
                        rowData.add(getCellValue(cell));
                    }
                    rowHandler.handle(i, row.getRowNum(), rowData);
                }
                rowHandler.doAfterAllAnalysed();
            }
        }
    }

    /** 获取单元格的通用值 */
    private static Object getCellValue(Cell cell) {
        if (cell == null) return "";
        return switch (cell.getCellType()) {
            case STRING -> cell.getStringCellValue();
            case NUMERIC -> DateUtil.isCellDateFormatted(cell)
                    ? cell.getDateCellValue()
                    : cell.getNumericCellValue();
            case BOOLEAN -> cell.getBooleanCellValue();
            case FORMULA -> cell.getCellFormula();
            case BLANK -> "";
            default -> "";
        };
    }
}