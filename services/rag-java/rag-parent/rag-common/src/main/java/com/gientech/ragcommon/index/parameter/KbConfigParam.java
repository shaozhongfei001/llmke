package com.gientech.ragcommon.index.parameter;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class KbConfigParam {
    private Integer chunkSize;
    private String fileType;
    private String embeddingModelName;
    private int fileFaqMaxNums;
    private int similarQuestionMaxNums;
    private boolean enablePolish;
    private String graphPrompt;
}
