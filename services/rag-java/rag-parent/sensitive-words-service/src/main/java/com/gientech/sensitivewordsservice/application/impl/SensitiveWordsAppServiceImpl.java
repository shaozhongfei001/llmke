package com.gientech.sensitivewordsservice.application.impl;

import com.baomidou.mybatisplus.core.toolkit.StringUtils;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.utils.CharsetEncodeUtils;
import com.gientech.ragcommon.sensitive.request.HitSensitiveWordRequest;
import com.gientech.sensitivewordsservice.application.SensitiveWordsAppService;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.domain.service.SensitiveWordsLibraryDomainService;
import com.gientech.ragcommon.sensitive.utils.AnsjParseWordUtils;
import lombok.extern.slf4j.Slf4j;
import org.apache.logging.log4j.core.appender.AppenderLoggingException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;

@Slf4j
@Service
public class SensitiveWordsAppServiceImpl implements SensitiveWordsAppService {

    @Autowired
    private AnsjParseWordUtils ansjParseWordUtils;

    @Autowired
    private SensitiveWordsLibraryDomainService sensitiveWordsLibraryDomainService;

    /**
     * 根据词库id改动内部的敏感词
     *
     * @param libraryId 词库id
     * @param words     敏感词列表
     * @return 成功/失败
     */
    @Override
    public Boolean updateSensitiveWords(Long libraryId, LinkedHashSet<String> words) {

        SensitiveWords sensitiveWords = sensitiveWordsLibraryDomainService.queryWordsLibraryById(libraryId);
        if (Objects.isNull(sensitiveWords)) {
            throw new ApplicationException("敏感词库不存在");
        }
        try {
            return sensitiveWordsLibraryDomainService.updateSensitiveWords(libraryId, words);
        } catch (Exception e) {
            log.error("updateSensitiveWords error {},id {} , words {}", e, libraryId, words);
            throw new ApplicationException("保存敏感词失败");
        }
    }

    /**
     * 根据词库id批量导入敏感词
     *
     * @param libraryId 词库id
     * @param file      敏感词列表文件 .csv  .txt
     * @return 成功/失败
     */
    @Override
    public Boolean importSensitiveWords(Long libraryId, MultipartFile file) {
        SensitiveWords sensitiveWords = sensitiveWordsLibraryDomainService.queryWordsLibraryById(libraryId);
        if (Objects.isNull(sensitiveWords)) {
            throw new AppenderLoggingException("敏感词库不存在");
        }
        //解析用户文件 file
        LinkedHashSet<String> words = parseCsvAndTxt(file);
        return sensitiveWordsLibraryDomainService.coverOldAndReceiveNewSensitiveWords(sensitiveWords, words);
    }

    private LinkedHashSet<String> parseCsvAndTxt(MultipartFile file) {
        if (file.isEmpty()) {
            throw new ApplicationException("敏感词文件或文件内容为空");
        }
        String originalFilename = file.getOriginalFilename();
        if (!isSupportFile(originalFilename)) {
            throw new ApplicationException("请上传CSV文件或TXT文件");
        }
        LinkedHashSet<String> words = new LinkedHashSet<>();
        BufferedInputStream bufferedInputStream = null;
        InputStreamReader inputStreamReader = null;
        Reader reader = null;
        BufferedReader bufferedReader = null;
        try {
            bufferedInputStream = new BufferedInputStream(file.getInputStream());
            String encode = CharsetEncodeUtils.charsetEncode(bufferedInputStream);
            inputStreamReader = new InputStreamReader(file.getInputStream(), encode);
            reader = new BufferedReader(inputStreamReader);
            bufferedReader = new BufferedReader(reader);
            String line;
            while ((line = bufferedReader.readLine()) != null) {
                readLine(line, words);
            }
        } catch (ApplicationException e) {
            log.error("parseCsvAndTxt error", e);
            throw new ApplicationException(ErrCodeEnum.WORDS_TOO_LONG);
        } catch (Exception e) {
            log.error("parseCsvAndTxt error", e);
            throw new ApplicationException("解析文件过程异常");
        } finally {
            if (bufferedReader != null) {
                try {
                    bufferedReader.close();
                } catch (IOException e) {
                    log.error("parseCsvAndTxt error", e);
                }
                if (reader != null) {
                    try {
                        reader.close();
                    } catch (IOException e) {
                        log.error("parseCsvAndTxt error", e);
                    }
                }
                if (inputStreamReader != null) {
                    try {
                        inputStreamReader.close();
                    } catch (IOException e) {
                        log.error("parseCsvAndTxt error", e);
                    }
                }
                if (bufferedInputStream != null) {
                    try {
                        bufferedInputStream.close();
                    } catch (IOException e) {
                        log.error("parseCsvAndTxt error", e);
                    }
                }
            }
        }
        return words;
    }

    private boolean isSupportFile(String originalFilename) {
        return originalFilename.toLowerCase().endsWith(".csv") || originalFilename.toLowerCase().endsWith(".txt");
    }

    private void readLine(String line, Set<String> words) {
        if (line == null || line.trim().isEmpty()) {
            return;//空行
        }
        //去掉空白字符、中英文标点符号
        String normalizedLine = line.replaceAll("\\s*", "")
                .replaceAll("[\\pP+~$`^=|<>～｀＄＾＋＝｜＜＞￥×]", "");
        if (StringUtils.isBlank(normalizedLine)) {
            return;//清洗后的词为空
        }
        if (StringUtils.isNotBlank(normalizedLine) && normalizedLine.length() > 16)
            throw new ApplicationException(ErrCodeEnum.WORDS_TOO_LONG);
        words.add(normalizedLine);
    }

    @Override
    public ResponseEntity<InputStreamResource> downloadTemplate(String fileType) throws Exception {
        String templateFileDir = "swtemplates/";
        String templateFilePath = null;
        if (fileType.equals("csv"))
            templateFilePath = templateFileDir + "敏感词.csv";
        else if (fileType.equals("txt"))
            templateFilePath = templateFileDir + "敏感词.txt";
        ClassPathResource resource = new ClassPathResource(templateFilePath);
        InputStream inputStream = resource.getInputStream();

        String filename = templateFilePath.substring(templateFilePath.indexOf("/") + 1);
        String encodedFilename = URLEncoder.encode(filename, StandardCharsets.UTF_8.toString());
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        headers.setContentDispositionFormData("attachment", encodedFilename);
        return ResponseEntity.ok().headers(headers).body(new InputStreamResource(inputStream));
    }

    @Override
    public Boolean checkHitSensitiveWord(HitSensitiveWordRequest wordRequest) {
        return ansjParseWordUtils.checkHitSensitiveWords(wordRequest.getContent(), wordRequest.getWords());
    }
}
