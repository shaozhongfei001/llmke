package com.gientech.ragqaservice.domain.entity;


import lombok.Data;

import java.io.Serializable;


@Data
public class DbId implements Serializable {

    private static final long serialVersionUID = 1L;

    private String answerId;
}
