package com.gientech.ragcommon.infrastructure.utils;

import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.hwpf.HWPFDocument;
import org.apache.poi.hwpf.extractor.WordExtractor;
import org.apache.poi.xwpf.extractor.XWPFWordExtractor;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.springframework.lang.NonNull;

import java.io.*;
import java.net.URLEncoder;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@Slf4j
public class FileUtils {

    private static int BYTE_SIZE = 8;
    public static String CODE_UTF8 = "UTF-8";
    public static String CODE_UTF8_BOM = "UTF-8_BOM";
    public static String CODE_GBK = "GBK";
    public static String CODE_UNICODE = "Unicode";
    public static String CODE_UTF16 = "UTF-16";
    public static final int BUFFERSIZE = 10 * 1024 * 1024;//设读取文件的缓存为10MB

    private static String tmpDir = System.getProperty("java.io.tmpdir");


    static SimpleDateFormat df = new SimpleDateFormat("yyyy-MM-dd");

    //创建随机文件路径
    //在随机文件路径下创建指定文件夹
    //获取临时目录
    public static String getTmpPath() {
        return getTmpPath(UUID.randomUUID().toString());
    }

    //获取临时目录
    public static String getTmpPath(String path) {
        String date = df.format(new Date());
        String dir = tmpDir + "/" + date + "/" + path + "/";
        File file = new File(dir);
        if (!file.exists()) {
            file.mkdirs();
        }
        return dir;
    }


    public static String joinPath(String... paths) {
        StringBuffer stringBuffer = new StringBuffer();
        for (String path : paths) {
            stringBuffer.append(path).append("/");
        }
        return stringBuffer.toString();
    }


    /**
     * 读取 InputStream前n 条数据
     *
     * @param lineNum      读取条数 小于0 表示读取所有
     * @param objectStream 文件流
     * @return
     */
    public static List<String> conventStreamToStr(InputStream objectStream, int lineNum) {

        List<String> list = new LinkedList<>();
        if (lineNum == 0) return list;
        BufferedReader bufferedReader = null;
        try {
            bufferedReader = new BufferedReader(new InputStreamReader(objectStream, "GB2312"));
            String csvLine = "";
            while ((csvLine = bufferedReader.readLine()) != null) {
                list.add(csvLine);
                if (list.size() == lineNum) break;
            }
            return list;
        } catch (Exception e) {
            log.error("getObjectString : {}", e);
            return null;
        } finally {
            IOUtils.closeIO(objectStream);
            IOUtils.closeIO(bufferedReader);
        }
    }

    /**
     * 读取文件行数
     *
     * @param objectStream
     * @param encode
     * @return
     */
    public static int getLineCount(InputStream objectStream, String encode) {
        int result = 0;

        BufferedReader bufferedReader = null;
        try {
            bufferedReader = new BufferedReader(new InputStreamReader(objectStream, encode));
            while (bufferedReader.readLine() != null) {
                result++;
            }
            return result;
        } catch (Exception e) {
            log.error(e.getMessage(), e);
            throw new RuntimeException(e);
        } finally {
            IOUtils.closeIO(objectStream);
            IOUtils.closeIO(bufferedReader);
        }

    }

    /**
     * 读取 InputStream前n 条数据
     *
     * @param lineNum      读取条数 小于0 表示读取所有
     * @param objectStream 文件流
     * @param encode       编码格式
     * @return
     */
    public static List<String> conventStreamToStr(InputStream objectStream, int lineNum, String encode) {

        List<String> list = new LinkedList<>();
        if (lineNum == 0) return list;
        BufferedReader bufferedReader = null;
        try {
            bufferedReader = new BufferedReader(new InputStreamReader(objectStream, encode));
            String csvLine = "";
            while ((csvLine = bufferedReader.readLine()) != null) {
                list.add(csvLine);
                if (list.size() == lineNum) break;
            }
            return list;
        } catch (Exception e) {
            log.error("getObjectString : {}", e);
            return null;
        } finally {
            IOUtils.closeIO(objectStream);
            IOUtils.closeIO(bufferedReader);
        }
    }

    /**
     * 读取 InputStream n条数据
     *
     * @param offset       读取条数起点
     * @param lineNum      读取条数 小于0 表示读取所有
     * @param objectStream 文件流
     * @param encode       编码格式
     * @return
     */
    public static List<String> conventStreamToStr(InputStream objectStream, int offset, int lineNum, String encode) {

        List<String> list = new LinkedList<>();
        if (lineNum == 0) return list;
        BufferedReader bufferedReader = null;
        try {
            bufferedReader = new BufferedReader(new InputStreamReader(objectStream, encode));
            String csvLine = "";
            int i = 0;
            while ((csvLine = bufferedReader.readLine()) != null) {
                if (i == 0 || i >= offset) {
                    list.add(csvLine);
                }
                if (list.size() == lineNum) break;
                i++;
            }
            return list;
        } catch (Exception e) {
            log.error("getObjectString : {}", e);
            return null;
        } finally {
            IOUtils.closeIO(objectStream);
            IOUtils.closeIO(bufferedReader);
        }
    }

    /**
     * 将InputStream转换为String
     *
     * @param inputStream
     * @return
     * @throws IOException
     */
    public static String convertInputStreamToString(InputStream inputStream)
            throws IOException {

        ByteArrayOutputStream result = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int length;
        while ((length = inputStream.read(buffer)) != -1) {
            result.write(buffer, 0, length);
        }

        return result.toString(StandardCharsets.UTF_8.name());
    }

    /**
     * 通过文件缓存流获取编码集名称
     *
     * @param bis
     * @return
     * @throws Exception
     */
    public static String getEncode(@NonNull BufferedInputStream bis, boolean ignoreBom) throws Exception {
        bis.mark(bis.available() + 1);

        String encodeType = StringUtils.EMPTY;
        byte[] head = new byte[3];
        bis.read(head);
        if (head[0] == -1 && head[1] == -2) {
            encodeType = CODE_UTF16;
        } else if (head[0] == -2 && head[1] == -1) {
            encodeType = CODE_UNICODE;
        } //带BOM
        else if (head[0] == -17 && head[1] == -69 && head[2] == -65) {
            if (ignoreBom) {
                encodeType = CODE_UTF8;
            } else {
                encodeType = CODE_UTF8_BOM;
            }
        } else if (CODE_UNICODE.equals(encodeType)) {
            encodeType = CODE_UTF16;
        } else if (isUTF8(bis)) {
            encodeType = CODE_UTF8;
        } else {
            encodeType = CODE_GBK;
        }
        log.info("encodeType : " + encodeType);
        return encodeType;
    }

    /**
     * 是否是无BOM的UTF8格式，不判断常规场景，只区分无BOM UTF8和GBK
     *
     * @param bis
     * @return
     */
    private static boolean isUTF8(@NonNull BufferedInputStream bis) throws Exception {
        bis.reset();
        int code = bis.read();
        do {
            BitSet bitSet = convert2BitSet(code);
            //判断是否为单字节
            if (bitSet.get(0)) {
                //多字节时，再读取N个字节
                if (!checkMultiByte(bis, bitSet)) {
                    return false;
                }
            } else {
                //单字节时什么都不用做，再次读取字节
            }
            code = bis.read();
        } while (code != -1);
        return true;
    }

    /**
     * 将整形转为BitSet
     *
     * @param code
     * @return
     */
    private static BitSet convert2BitSet(int code) {
        BitSet bitSet = new BitSet(BYTE_SIZE);

        for (int i = 0; i < BYTE_SIZE; i++) {
            int tmp3 = code >> (BYTE_SIZE - i - 1);
            int tmp2 = 0x1 & tmp3;
            if (tmp2 == 1) {
                bitSet.set(i);
            }
        }
        return bitSet;
    }

    /**
     * 检测多字节，判断是否为utf8，已经读取了一个字节
     *
     * @param bis
     * @param bitSet
     * @return
     */
    private static boolean checkMultiByte(@NonNull BufferedInputStream bis, @NonNull BitSet bitSet) throws Exception {
        int count = getCountOfSequential(bitSet);
        //已经读取了一个字节，不能再读取
        byte[] bytes = new byte[count - 1];
        bis.read(bytes);
        for (byte b : bytes) {
            if (!checkUtf8Byte(b)) {
                return false;
            }
        }
        return true;
    }

    /**
     * 检测bitSet中从开始有多少个连续的1
     *
     * @param bitSet
     * @return
     */
    private static int getCountOfSequential(@NonNull BitSet bitSet) {
        int count = 0;
        for (int i = 0; i < BYTE_SIZE; i++) {
            if (bitSet.get(i)) {
                count++;
            } else {
                break;
            }
        }
        return count;
    }

    /**
     * 检测单字节，判断是否为utf8
     *
     * @param b
     * @return
     */
    private static boolean checkUtf8Byte(byte b) {
        BitSet bitSet = convert2BitSet(b);
        return bitSet.get(0) && !bitSet.get(1);
    }


    //删除文件或者目录
    public static void deleteDireOrFile(String path) {
        File folder = new File(path);
        File[] files = folder.listFiles();
        if (files != null) {
            for (File f : files) {
                if (f.isDirectory()) {
                    deleteDireOrFile(f.toString());
                } else {
                    f.delete();
                    log.info("删除文件 :{} 成功: ", f.toString());
                }
            }
            folder.delete();
        }
        log.info("文件删除成功: {}", path);
        folder.delete();
    }


    //合并目录下所有文件
    public static boolean mergeDirFile(String mergePath, String outFilePath, boolean isDelChunk) throws IOException {
        File folder = new File(mergePath);
        File[] files = folder.listFiles();
        if (files == null) return false;

        Arrays.sort(files);//排序
        //定义输出目录
        FileChannel outFileChannel = new FileOutputStream(outFilePath, true).getChannel();
        for (File f : files) {
            if (f.isFile() && !f.getAbsolutePath().equals(outFilePath)) {
                log.info("合并文件：{}", f.getAbsolutePath());
                FileChannel fc = new FileInputStream(f.getAbsolutePath()).getChannel();
                outFileChannel.transferFrom(fc, outFileChannel.size(), fc.size());
                fc.close();

                if (isDelChunk) f.delete();
            }
        }
        outFileChannel.close();
        log.info("文件合并成功");
        return true;
    }


    public static void closeIO(InputStream inputStream, OutputStream outputStream) {
        if (inputStream != null) {
            try {
                inputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        if (outputStream != null) {
            try {
                outputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static void closeIO(OutputStream outputStream) {
        if (outputStream != null) {
            try {
                outputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static void closeIO(InputStream... inputStreams) {
        if (inputStreams != null && inputStreams.length > 0) {
            for (int i = 0; i < inputStreams.length; i++) {
                closeIO(inputStreams[i], null);
            }
        }
    }

    public static void closeIO(Reader... bfr) {
        if (bfr != null && bfr.length > 0) {
            for (int i = 0; i < bfr.length; i++) {
                closeIO(bfr[i]);
            }
        }
    }

    public static void closeIO(Reader reader) {
        if (reader != null) {
            try {
                reader.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static void closeIO(InputStreamReader isReader) {
        if (isReader != null) {
            try {
                isReader.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static void closeIO(OutputStream outputStream, InputStream inputStream) {
        if (inputStream != null) {
            try {
                inputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        if (outputStream != null) {
            try {
                outputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * InputStream 打包压缩成zip
     *
     * @param inputStreamMap 文件里列表<文件名， 流>
     * @param zipFileName    导出的压缩包文件名
     */
    public static void insListToZip(Map<String, InputStream> inputStreamMap, String zipFileName, HttpServletResponse response) {
        if (inputStreamMap == null || inputStreamMap.isEmpty()) {
            Objects.requireNonNull(inputStreamMap, "inputStreamMap is null");
        }
        ZipOutputStream zipos = null;
        try {
            zipFileName = URLEncoder.encode(zipFileName, "UTF-8");
            response.setHeader("filename", zipFileName + ".zip");

            //设置压缩流：直接写入response，实现边压缩边下载
            zipos = new ZipOutputStream(response.getOutputStream());
            byte[] buf = new byte[BUFFERSIZE];
            //获取需要打入包中的文件名和文件流
            for (Map.Entry<String, InputStream> entry : inputStreamMap.entrySet()) {
                String filename = entry.getKey();
                zipos.putNextEntry(new ZipEntry(filename));

                InputStream fileis = entry.getValue();
                if (fileis != null) {
                    int readLen = -1;
                    while ((readLen = fileis.read(buf, 0, 1024 * 1024 * 5)) != -1)
                        zipos.write(buf, 0, readLen);

                    zipos.closeEntry();
                    fileis.close();
                }
            }
        } catch (IOException e) {
            log.error("压缩成zip出错：{}", e);
        } finally {
            if (zipos == null) return;
            try {
                zipos.close();
            } catch (IOException e) {
                log.error("压缩成zip出错：{}", e);
            }
        }
    }

    /**
     * 获取pdf文档的内容
     */
    public static InputStream getInputStreamFromPdf(InputStream is) throws IOException {
        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
             Writer writer = new OutputStreamWriter(outputStream)) {
            PDDocument doc = PDDocument.load(is);
            PDFTextStripper pdfTextStripper = new PDFTextStripper();
            //获取文档内容
            String text = pdfTextStripper.getText(doc);
            // 按段落分割
           /* String[] paragraphs = text.split("\\r?\\n\\r?\\n");
            for (String paragraph : paragraphs) {
                System.out.println(paragraph);
            }*/
            writer.append(text);
            writer.flush();
            return new ByteArrayInputStream(outputStream.toByteArray());
        } catch (Exception e) {
            log.error(e.getMessage());
            throw new RuntimeException("Error processing pdf document", e);
        }
    }

    /**
     * 获取docx文档的内容
     *
     * @param is 输入流
     * @return InputStreamReader
     */
    public static InputStream getInputStreamFromDocx(InputStream is) throws IOException {
        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
             Writer writer = new OutputStreamWriter(outputStream)) {
            XWPFDocument document = new XWPFDocument(is);
            XWPFWordExtractor extractor = new XWPFWordExtractor(document);
            // 获取所有段落
         /*    List<XWPFParagraph> paragraphs = document.getParagraphs();
            // 遍历段落并打印文本内容
            for (XWPFParagraph paragraph : paragraphs) {
                System.out.println(paragraph.getText());
            }*/
            //获取文档全部内容
            writer.append(extractor.getText());
            writer.flush();
            return new ByteArrayInputStream(outputStream.toByteArray());
        } catch (Exception e) {
            log.error(e.getMessage());
            throw new RuntimeException("Error processing Word document", e);
        }
    }

    /**
     * 获取doc文档的内容
     *
     * @param is 输入流
     * @return InputStreamReader
     */
    public static InputStream getInputStreamFromDoc(InputStream is) throws IOException {
        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
             Writer writer = new OutputStreamWriter(outputStream)) {

            HWPFDocument document = new HWPFDocument(is);
            WordExtractor extractor = new WordExtractor(document);

            //获取文档内容
            writer.append(extractor.getText());
            writer.flush();

            return new ByteArrayInputStream(outputStream.toByteArray());

        } catch (Exception e) {
            // Handle the exception or rethrow it
            log.error(e.getMessage());
            throw new RuntimeException("Error processing Word document", e);
        }
    }
    public static String getExt(String url) {
        if (com.alibaba.excel.util.StringUtils.isNotBlank(url)) {
            int lastIndexOf = url.lastIndexOf(".");
            if (lastIndexOf > 0) {
                return url.substring(lastIndexOf + 1).toLowerCase(Locale.ROOT);
            }

        }
        throw new IllegalArgumentException("convertedFilePath is blank.");
    }
}


