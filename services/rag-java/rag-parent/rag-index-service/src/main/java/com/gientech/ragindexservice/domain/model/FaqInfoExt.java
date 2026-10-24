package com.gientech.ragindexservice.domain.model;

import com.gientech.ragindexservice.domain.entity.FaqInfo;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/5/14 15:34
 */
@Data
public class FaqInfoExt extends FaqInfo {
    private boolean folder;
    private String folderName;
    private String label;
    private String fileName;
    private List<FaqInfo> similarQuestions;
}
