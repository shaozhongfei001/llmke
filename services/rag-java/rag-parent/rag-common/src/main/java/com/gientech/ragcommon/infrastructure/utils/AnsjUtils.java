package com.gientech.ragcommon.infrastructure.utils;

import com.alibaba.fastjson2.JSON;
import com.google.common.collect.Sets;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.ansj.domain.Result;
import org.ansj.domain.Term;
import org.ansj.splitWord.analysis.NlpAnalysis;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * @Descrption: Ansj分词工具类
 * @Author:liutaiyun
 * @Date:2024/08/26 15:31
 **/
@Component
@Slf4j
public class AnsjUtils {

    @PostConstruct
    public void init() {
        HashSet<String> strings = nlpAnalysisParse("用来加载词典");
        log.info("ansj custom load:{}", JSON.toJSON(strings));
    }

    /**
     * 对文本进行NlpAnalysis分词
     *
     * @param text
     * @return
     */
    public static HashSet<String> nlpAnalysisParse(String text) {
        if (StringUtils.isBlank(text)) {
            return Sets.newHashSet();
        }

        Result parsedResult = NlpAnalysis.parse(text);
        List<Term> terms = parsedResult.getTerms();
        HashSet<String> words = terms.stream()
                .map(term -> term.getName()).collect(Collectors.toCollection(HashSet::new));
        return words;
    }

    public static void main(String[] args) {
        String text = "我爱北京天安门。";
        HashSet<String> result = nlpAnalysisParse(text);
        System.out.println(result);
    }
}
