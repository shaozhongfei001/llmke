package com.gientech.ragqaservice.domain.conventer;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.dto.DialogDTO;
import com.gientech.ragcommon.qa.request.AiRequest;
import com.gientech.ragcommon.qa.entity.Config;
import com.gientech.ragqaservice.domain.entity.Dialogue;
import com.gientech.ragqaservice.domain.model.DialogueDO;
import org.apache.commons.lang3.StringUtils;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.Objects;


/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/07/23 13:56
 **/
@Mapper(uses = {SearchConfigConvertor.class, SysTypeEnumConvertor.class})
public interface DialogueConvertor {

    DialogueConvertor INSTANCE = Mappers.getMapper(DialogueConvertor.class);

//    Dialogue dialogCreateRequestToDialogue(DialogCreateRequest request);

    Dialogue dialogueDOToDialogue(DialogueDO dialogueDO);

    DialogueDO dialogueToDialogueDO(Dialogue dialogue);

    DialogDTO dialogueToDialogDTO(Dialogue dialogue);

    Page<Dialogue> dialogDOPageToDialogPage(Page<DialogueDO> dialogueDOPage);

    Page<DialogDTO> dialogPageToDialogDTOPage(Page<Dialogue> page);

    Dialogue aiRequest2Dialogue(AiRequest aiRequest);


    default Config searchConfigStrToSearchConfig(String searchConfigStr) {
        if (StringUtils.isBlank(searchConfigStr)) {
            return null;
        } else {
            return JSONObject.parseObject(searchConfigStr, Config.class);
        }
    }

    default String searchConfigToSearchConfigStr(Config config) {
        if (Objects.isNull(config)) {
            return null;
        } else {
            return JSONObject.toJSONString(config);
        }
    }
}
