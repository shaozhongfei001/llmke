package com.gientech.ragqaservice.domain.entity;


import lombok.Data;

import java.io.Serializable;


@Data
public class ConfigNameAndAnswerId implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long answerId;

    private Long dialogueId;

    private String configName;

    private String configJson;

    private String dialogueConfig;
}
