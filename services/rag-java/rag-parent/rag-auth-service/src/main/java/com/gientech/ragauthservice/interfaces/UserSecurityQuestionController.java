package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.UserSecurityQuestionAppService;
import com.gientech.ragcommon.auth.dto.UserSecurityQuestionDTO;
import com.gientech.ragauthservice.interfaces.req.SaveSecurityQuestionReq;
import com.gientech.ragauthservice.interfaces.req.UpdatePasswordByQuestionReq;
import com.gientech.ragauthservice.interfaces.req.ValidateSecurityQuestionReq;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "user_security_question")
@RestController
@RequestMapping("/userSecurityQuestion")
public class UserSecurityQuestionController {

    @Autowired
    private UserSecurityQuestionAppService userSecurityQuestionAppService;

    @Operation(summary = "创建用户密保问题")
    @PostMapping("/save")
    @OperationLog(operateType = "创建用户密保问题")
    public Boolean save(@RequestBody @Validated SaveSecurityQuestionReq saveSecurityQuestionReq) {
        List<UserSecurityQuestionDTO> userSecurityQuestionList = saveSecurityQuestionReq.getUserSecurityQuestionList();
        String verifyCode = saveSecurityQuestionReq.getVerifyCode();
        return userSecurityQuestionAppService.saveOfLoginUser(userSecurityQuestionList, verifyCode);
    }

    @Operation(summary = "更新用户密保问题")
    @PostMapping("/update")
    @OperationLog(operateType = "更新用户密保问题")
    public Boolean update(@RequestBody List<UserSecurityQuestionDTO> userSecurityQuestionDTOList) {
        return userSecurityQuestionAppService.saveOfLoginUser(userSecurityQuestionDTOList, null);
    }

    @Operation(summary = "查询用户密保问题")
    @GetMapping("/findByUserName/{userName}")
    @OperationLog(operateType = "查询用户密保问题")
    public List<UserSecurityQuestionDTO> findByUserName(@PathVariable("userName") String userName) {
        List<UserSecurityQuestionDTO> userSecurityQuestionDTOList = userSecurityQuestionAppService.findByUserName(userName, true);
        return userSecurityQuestionDTOList;
    }


    @Operation(summary = "验证密保问题")
    @PostMapping("/validateSecurityQuestion")
    @OperationLog(operateType = "验证密保问题")
    public String validateSecurityQuestion(@RequestBody @Validated ValidateSecurityQuestionReq validateSecurityQuestionReq) {
        return userSecurityQuestionAppService.validateSecurityQuestion(validateSecurityQuestionReq);
    }

    @Operation(summary = "通过密保问题更新密码")
    @PostMapping("/updatePasswordByQuestion")
    @OperationLog(operateType = "通过密保问题更新密码")
    public Boolean updatePasswordByQuestion(@RequestBody @Validated UpdatePasswordByQuestionReq updatePasswordByQuestionReq) {
        return userSecurityQuestionAppService.updatePasswordByQuestion(updatePasswordByQuestionReq);
    }
}
