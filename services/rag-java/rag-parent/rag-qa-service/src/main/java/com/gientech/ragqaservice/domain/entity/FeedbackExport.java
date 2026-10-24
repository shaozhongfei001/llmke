package com.gientech.ragqaservice.domain.entity;


import lombok.Data;
import java.io.Serializable;
import java.util.Date;

@Data
public class FeedbackExport implements Serializable {


    private String userName;


    private String issueType;


    private String supplementExplain;


    private String idealAnswer;



    private String deptName;


    private String userPhone;

    private String configName;

    private String questionsAndAnswers;

    private String context;

    private Date gmtCreate;

}
