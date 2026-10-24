package com.gientech.ragindexservice.utils;


import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import org.apache.poi.hwpf.HWPFDocument;
import org.apache.poi.hwpf.converter.WordToFoConverter;
import org.apache.poi.hwpf.usermodel.Range;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class Test1 {

    static String LIBREOFFICE_PATH = "C:/Program Files/LibreOffice/program/soffice.exe"; // Windows示例路径，根据实际情况调整
    static String INPUT_FILE_PATH = "C:/Users/23216/Desktop/aa/银行基本知识点.doc";
    static String OUTPUT_FILE_PATH = "C:/Users/23216/Desktop/aa/银行基本知识点.docx";

    public static void main(String[] args) throws Exception{

       String s = "{\"top_k\":{\"min\":1,\"max\":15},\"max_tokens\":{\"min\":1,\"max\":10000},\"max_round\":{\"min\":1,\"max\":10}}";

        System.out.println(System.currentTimeMillis());
    }

    public static void test6()throws Exception{
        FileInputStream fis = new FileInputStream(INPUT_FILE_PATH);
        HWPFDocument document = new HWPFDocument(fis);
        Range range = document.getRange();

        // 创建一个新的空白docx文档
        XWPFDocument newDocument = new XWPFDocument();

        // 转换文档的段落
        for (int i = 0; i < range.numParagraphs(); i++) {
            XWPFParagraph paragraph = newDocument.createParagraph();
            paragraph.createRun().setText(range.getParagraph(i).text());
        }

        // 写入新的docx文件
        FileOutputStream out = new FileOutputStream(OUTPUT_FILE_PATH);
        newDocument.write(out);
        out.close();

        System.out.println("转换完成");
    }

//    public static boolean getLicense() {
//        boolean result = false;
//        try {
//            //这个地方xml文件的物理路径要写正确
//            Resource resource = new ClassPathResource("license.xml");
//            InputStream is = resource.getInputStream();
//            License aposeLic = new License();
//            aposeLic.setLicense(is);
//            result = true;
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//        return result;
//    }
//
//    public static void doc2pdf(String inPath, String outPath) {
//        if (!getLicense()) {
//            return;
//        }
//        try {
//            File file = new File(outPath);
//            FileOutputStream os = new FileOutputStream(file);
//            Document doc = new Document(inPath);
//            doc.save(os, SaveFormat.DOCX);// 这里可以写你想要装换的类型：DOC, DOCX, PDF，HTML
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }



    public static  void  test5()throws Exception{
//        Document doc = new XWPFDocument(new FileInputStream(INPUT_FILE_PATH));
//        XWPFDocument docx = new XWPFDocument();
//        WordToFoConverter converter = new WordToFoConverter(doc);
////        WordToFoConverter converter = new WordToFoConverter(DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument());
//
//        converter.processDocument(doc);
//
//        FileOutputStream out = new FileOutputStream(OUTPUT_FILE_PATH);
//        docx.write(out);
//        out.close();
    }

    public static  void  test4(){
//        File inputWord = new File(INPUT_FILE_PATH);
//        File outputFile = new File(OUTPUT_FILE_PATH);
//        try{
//            InputStream docxInputStream = new FileInputStream(inputWord);
//            OutputStream outputStream = new FileOutputStream(outputFile);
//            IConverter converter = LocalConverter.builder().build();
//            converter.convert(docxInputStream).as(DocumentType.DOC).to(outputStream).as(DocumentType.DOCX).execute();
//            outputStream.close();
//            outputFile.createNewFile();
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
    }

    public static void test3() throws Exception {

        InputStream is = new FileInputStream(INPUT_FILE_PATH);
        HWPFDocument wordDocument = new HWPFDocument(is);
        WordToFoConverter converter = new WordToFoConverter(DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument());
        //对HWPFDocument进行转换
        converter.processDocument(wordDocument);
        Writer writer = new FileWriter(new File(OUTPUT_FILE_PATH));
        Transformer transformer = TransformerFactory.newInstance().newTransformer();
        transformer.setOutputProperty(OutputKeys.ENCODING, "utf-8");
        //是否添加空格
        transformer.setOutputProperty(OutputKeys.INDENT, "yes");
        transformer.transform(
                new DOMSource(converter.getDocument()),
                new StreamResult(writer));
    }


    public static void test2() throws Exception {
//        FileInputStream fis = new FileInputStream(INPUT_FILE_PATH);
//        HWPFDocument doc = new HWPFDocument(fis);
//        fis.close();
//
//        WordToFoConverter converter = new WordToFoConverter(doc);
//        Range range = doc.getRange();
//        FileOutputStream fos = new FileOutputStream(OUTPUT_FILE_PATH);
//        converter.processDocument(doc,fos);
//       fos.close();


    }

    public static void test1() {


        Path inputFile = Paths.get(INPUT_FILE_PATH);
        Path outputFile = Paths.get(OUTPUT_FILE_PATH);

        try {
            // 确保输入文件存在
            if (!Files.exists(inputFile)) {
                System.err.println("Input file not found: " + inputFile);
                return;
            }

            // 执行LibreOffice转换命令
            ProcessBuilder pb = new ProcessBuilder(LIBREOFFICE_PATH, "--headless", "--convert-to", "docx", "--outdir", outputFile.getParent().toString(), inputFile.toString());
            Process process = pb.start();

            // 等待转换完成
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                System.err.println("LibreOffice conversion failed with exit code: " + exitCode);
            } else {
                System.out.println("Conversion from .doc to .docx successful.");
            }
        } catch (IOException | InterruptedException e) {
            System.err.println("An error occurred during conversion:");
            e.printStackTrace();
        }
    }
}
