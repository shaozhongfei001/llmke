package com.gientech.ragindexservice.utils;

import org.jodconverter.core.office.OfficeException;
import org.jodconverter.remote.RemoteConverter;
import org.jodconverter.remote.office.RemoteOfficeManager;

import java.io.File;


public class RemoteOfficeManagerTest {


    public static void main(String[] args) throws OfficeException {
        System.out.println("----1");
        RemoteOfficeManager officeManager = RemoteOfficeManager.builder()
                .urlConnection("http://10.15.12.11:9996") // 设置远程服务的 URL
                .build();
        officeManager.start();
//
        // 创建 RemoteConverter
        RemoteConverter converter = RemoteConverter.make(officeManager);
        File inputFile = new File("C:\\Users\\23216\\Desktop\\异常文件\\11111111111.pptx");
        File outputFile = new File("C:\\Users\\23216\\Desktop\\异常文件\\转化后的文件\\2222211111.pdf");
        converter.convert(inputFile)
                .to(outputFile).execute();
    }
}
