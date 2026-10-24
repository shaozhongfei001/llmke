package com.gientech.ragqaservice.domain.model;


import lombok.Data;

import java.io.Serializable;


@Data
public class DbIdDO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String answerId;
}
