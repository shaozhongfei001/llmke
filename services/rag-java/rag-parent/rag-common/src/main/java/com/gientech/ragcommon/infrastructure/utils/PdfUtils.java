package com.gientech.ragcommon.infrastructure.utils;

import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;

@Slf4j
public class PdfUtils {

    public static Integer getPdfPages(String filePath) {
        Integer numberOfPages = 0;
        if(StringUtils.isEmpty(filePath))
            return numberOfPages;
        try {
            URL url = new URL(filePath);
            PDDocument document = PDDocument.load(url.openStream());
            numberOfPages = document.getNumberOfPages();
            document.close();
        } catch (IOException e) {
            log.error(e.getMessage());
        }
        return numberOfPages;
    }

    public static Integer getPdfPages(InputStream inputStream) {
        Integer numberOfPages = 0;
        try {
            PDDocument document = PDDocument.load(inputStream);
            numberOfPages = document.getNumberOfPages();
            document.close();
        } catch (IOException e) {
            log.error(e.getMessage());
        }finally {
            if(inputStream != null){
                try {
                    inputStream.close();
                } catch (IOException e) {
                    log.error(e.getMessage());
                }
            }

        }
        return numberOfPages;
    }
}
