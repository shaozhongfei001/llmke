package com.gientech.ragcommon.qa.dto;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Data
public class RetriveTagDTO {

    private String index;

    private String id;

    private String image_urls;

    public static RetriveTagDTO convertRetriveTagDTO(String retriveTag){
        try {
            if(StringUtils.isNotBlank(retriveTag)){
                retriveTag = retriveTag.replace("[retrive-tag ","").replace("][/retrive-tag]","");
                String index = retriveTag.substring(retriveTag.indexOf("][") + 2);
                retriveTag =  retriveTag.substring(0,retriveTag.indexOf("]["));
                RetriveTagDTO retriveTagDTO = new RetriveTagDTO();
                retriveTagDTO.setIndex(index);

                Pattern pattern = Pattern.compile("([^= ]+)=([^ ]*)");
                Matcher matcher = pattern.matcher(retriveTag);
                matcher.find();
                retriveTagDTO.setId(matcher.group(2));
                matcher.find();
                retriveTagDTO.setImage_urls(matcher.group(2));
                return retriveTagDTO;
            }
        }catch (Exception e){
            log.error(e.getMessage());
        }
        return null;
    }
}
