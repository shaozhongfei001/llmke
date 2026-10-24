package com.gientech.ragcommon.sensitive.request;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashSet;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class HitSensitiveWordRequest {
    private String content;
    private HashSet<String> words;
}
