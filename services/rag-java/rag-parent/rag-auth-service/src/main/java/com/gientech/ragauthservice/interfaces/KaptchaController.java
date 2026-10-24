package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.KaptchaAppService;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;

/**
 * 验证码
 */
@RestController
@RequestMapping("/kaptcha")
public class KaptchaController {
    @Autowired
    private KaptchaAppService kaptchaAppService;


    @Operation(summary = "获取6位图形验证码")
    @GetMapping("/kaptchaSix")
    public void kaptchaSix(
            HttpServletRequest request,
            HttpServletResponse response) throws IOException {
        kaptchaAppService.genKaptchaImageSix(request, response);
    }
}
