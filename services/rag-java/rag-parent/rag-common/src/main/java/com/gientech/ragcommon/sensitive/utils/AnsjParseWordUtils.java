package com.gientech.ragcommon.sensitive.utils;

import cn.hutool.core.collection.CollectionUtil;
import com.alibaba.cloud.commons.lang.StringUtils;
import com.gientech.ragcommon.sensitive.dto.SensitiveWordHitDTO;
import com.google.common.collect.Sets;
import lombok.extern.slf4j.Slf4j;
import org.ansj.domain.Result;
import org.ansj.domain.Term;
import org.ansj.library.DicLibrary;
import org.ansj.splitWord.analysis.NlpAnalysis;
import org.springframework.stereotype.Component;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

/**
 *  Ansj分词工具类
 **/
@Component
@Slf4j
public class AnsjParseWordUtils {

//    @PostConstruct
//    public void init() {
//        nlpSegmentWord("分词:用于预热词典");
//        log.info("init ansj parse");
//    }

    /**
     * 对文本进行NlpAnalysis分词
     *
     * @param text 原文
     * @return 文章分词列表
     */
    public HashSet<String> nlpSegmentWord(String text) {
        log.info("开始分词 nlpSegmentWord");
        if (StringUtils.isBlank(text)) {
            return Sets.newHashSet();
        }
        Result parsedResult = NlpAnalysis.parse(text);
        List<Term> terms = parsedResult.getTerms();
        HashSet<String> words = terms.stream()
                .map(Term::getName).collect(Collectors.toCollection(HashSet::new));
        log.info("结束分词 nlpSegmentWord");
        return words;
    }

    /**
     * 分词并解析出全文包含的敏感词
     *
     * @param content          源内容
     * @param sensitiveWords   目标敏感词
     * @return 文章命中的敏感词列表
     */
    public List<SensitiveWordHitDTO> markSensitiveWord(String content, HashSet<String> sensitiveWords) {
        if (StringUtils.isBlank(content) || CollectionUtil.isEmpty(sensitiveWords)) {
            return null;
        }
        //动态添加用户自定义词典
        DynamicUseDefalutDic(sensitiveWords);
        //获取分词后的内容，连续的
        Result parsedResult = NlpAnalysis.parse(content);
        List<Term> terms = parsedResult.getTerms();
        //处理结果
        AtomicInteger count = new AtomicInteger();
        return terms.stream().filter(term -> sensitiveWords.contains(term.getName()))
                .map(term -> {
                    //当前文本词命中敏感词
                    SensitiveWordHitDTO sensitiveWordDto = new SensitiveWordHitDTO();
                    count.getAndIncrement();
                    sensitiveWordDto.setId(count.intValue());
                    sensitiveWordDto.setWord(term.getName());
                    sensitiveWordDto.setContext(collectContext(terms, term, 5));
                    return sensitiveWordDto;
                }).collect(Collectors.toList());
    }

    private static String collectContext(List<Term> terms, Term targetTerm, int contextSize) {
        StringBuilder contextBuilder = new StringBuilder();
        int index = terms.indexOf(targetTerm);
        // 添加前contextSize个词
        for (int i = Math.max(0, index - contextSize); i < index; i++) {
            if (i >= 0 && i < terms.size()) {
                contextBuilder.append(terms.get(i).getName());
            }
        }
        // 添加敏感词本身
        contextBuilder.append(targetTerm.getName());
        // 添加后contextSize个词
        for (int i = index + 1; i <= Math.min(terms.size() - 1, index + contextSize); i++) {
            if (i >= 0 && i < terms.size()) {
                contextBuilder.append(terms.get(i).getName());
            }
        }
        return contextBuilder.toString().trim();
    }


    public Boolean checkHitSensitiveWords(String content, HashSet<String> sensitiveWords) {
        if (StringUtils.isBlank(content) || CollectionUtil.isEmpty(sensitiveWords)) {
            return false;//没有敏感词
        }
        //动态添加用户自定义词典
        DynamicUseDefalutDic(sensitiveWords);
        //对原文进行分词
        Result parsedResult = NlpAnalysis.parse(content);
        List<Term> terms = parsedResult.getTerms();
        HashSet<String> contentSet = terms.stream()
                .map(Term::getName).collect(Collectors.toCollection(HashSet::new));
        //取交集
        contentSet.retainAll(sensitiveWords);
        //有交集代表命中敏感词
        return CollectionUtil.isNotEmpty(contentSet);
    }

    /**
     * 动态定义分词器底层的词典
     * 按照 词名--词性--词频 格式插入
     * @param dicWords 词语
     */
    private static void DynamicUseDefalutDic(HashSet<String> dicWords) {
        dicWords.parallelStream().forEach(word->{
            DicLibrary.insert(DicLibrary.DEFAULT, word.toLowerCase(), "n", 100);
        });
    }
}
