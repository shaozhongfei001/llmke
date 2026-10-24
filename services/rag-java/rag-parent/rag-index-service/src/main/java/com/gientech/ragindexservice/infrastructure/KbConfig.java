//package com.gientech.ragindexservice.infrastructure;
//
//import com.alibaba.fastjson2.JSONArray;
//import com.gientech.ragcommon.index.dto.KbEmbeddingModelDTO;
//import com.gientech.ragcommon.index.dto.KbParseTypeDTO;
//import lombok.Data;
//import org.apache.commons.lang3.StringUtils;
//import org.springframework.beans.factory.annotation.Value;
//import org.springframework.cloud.context.config.annotation.RefreshScope;
//import org.springframework.stereotype.Component;
//
//import java.util.List;
//
//@RefreshScope
//@Component
//@Data
//public class KbConfig {
//
//    @Value("${file-parse.embedding-models}")
//    private String kbEmbeddingModels;
//
//    @Value("${file-parse.types}")
//    private String kbParseTypes;
//
//    public String getDefaultParseType() {
//        List<KbParseTypeDTO> kbParseTypeDTOS = JSONArray.parseArray(kbParseTypes, KbParseTypeDTO.class);
//        for (KbParseTypeDTO kbParseTypeDTO : kbParseTypeDTOS) {
//            if (kbParseTypeDTO.getIsDefault())
//                return kbParseTypeDTO.getName();
//        }
//        return kbParseTypeDTOS.get(0).getName();
//    }
//
//    public String getDefaultModel() {
//        List<KbEmbeddingModelDTO> kbEmbeddingModelDTOS = JSONArray.parseArray(kbEmbeddingModels, KbEmbeddingModelDTO.class);
//        for (KbEmbeddingModelDTO kbEmbeddingModelDTO : kbEmbeddingModelDTOS) {
//            if (kbEmbeddingModelDTO.getIsDefault())
//                return kbEmbeddingModelDTO.getName();
//        }
//        return kbEmbeddingModelDTOS.get(0).getName();
//    }
//
//    public List<KbEmbeddingModelDTO> getKbEmbeddingModels() {
//        return StringUtils.isEmpty(kbEmbeddingModels) ? null : JSONArray.parseArray(kbEmbeddingModels, KbEmbeddingModelDTO.class);
//    }
//
//    public List<KbParseTypeDTO> getKbParseTypes() {
//        return StringUtils.isEmpty(kbParseTypes) ? null : JSONArray.parseArray(kbParseTypes, KbParseTypeDTO.class);
//    }
//}