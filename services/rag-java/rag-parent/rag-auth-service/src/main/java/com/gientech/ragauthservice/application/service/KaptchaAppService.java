package com.gientech.ragauthservice.application.service;

import cn.hutool.crypto.digest.DigestUtil;
import com.gientech.ragauthservice.infrastructure.CodeUtils;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.utils.IPUtils;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.google.code.kaptcha.Producer;
import com.google.code.kaptcha.impl.DefaultKaptcha;
import com.google.code.kaptcha.util.Config;
import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.util.Properties;
import java.util.concurrent.TimeUnit;

/**
 * 图形验证码
 */
@Service
public class KaptchaAppService {

    @Autowired
    private RedissonUtils redissonUtils;

    /**
     * 六位图形验证码
     */
    private Producer captchaProducerSix;

    private final String CAPTCHA_PREFIX_SIX = "captcha:six:";

    private final long CAPTCHA_CODE_EXPIRED = 60 * 3;


    public KaptchaAppService() {
        DefaultKaptcha captchaProducer = new DefaultKaptcha();
        Properties properties = new Properties();
        properties.setProperty("kaptcha.border", "yes");
        properties.setProperty("kaptcha.border.color", "105,179,90");
        properties.setProperty("kaptcha.textproducer.font.color", "blue");
        properties.setProperty("kaptcha.image.width", "110");
        properties.setProperty("kaptcha.image.height", "40");
        properties.setProperty("kaptcha.textproducer.font.size", "30");
        properties.setProperty("kaptcha.session.key", "code");
        properties.setProperty("kaptcha.textproducer.char.length", "6");
        properties.setProperty("kaptcha.textproducer.font.names", "宋体,楷体,微软雅黑");
        Config config = new Config(properties);
        captchaProducer.setConfig(config);

        this.captchaProducerSix = captchaProducer;
    }

    /**
     * 生成6位图形验证码
     * @param request
     * @param response
     * @throws IOException
     */
    public void genKaptchaImageSix(HttpServletRequest request, HttpServletResponse response) throws IOException {
        response.setDateHeader("Expires", 0);
        response.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
        response.addHeader("Cache-Control", "post-check=0, pre-check=0");
        response.setHeader("Pragma", "no-cache");
        response.setContentType("image/jpeg");
        //生成验证码
        String capText = captchaProducerSix.createText();
        //存储
        String captchaKey = getCaptchaKeySix(request);
        redissonUtils.set(captchaKey, capText, CAPTCHA_CODE_EXPIRED, TimeUnit.SECONDS);

        //向客户端写出
        BufferedImage bi = captchaProducerSix.createImage(capText);
        ServletOutputStream out = response.getOutputStream();
        ImageIO.write(bi, "jpg", out);
        try {
            out.flush();
        } finally {
            out.close();
        }
    }

    /**
     * 验证6位图形验证码
     * @param verifyCode
     * @return
     */
    public Boolean validateKaptchaSix(String verifyCode){
        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = servletRequestAttributes.getRequest();
        // 校验验证码
        String captchaKey = getCaptchaKeySix(request);
        String verifyCodeExpected = redissonUtils.get(captchaKey);
        boolean rst = verifyCode.equalsIgnoreCase(verifyCodeExpected);
        return rst;
    }

    /**
     * 验证4位图形验证码
     * @param verifyCode
     * @return
     */
    public Boolean validateKaptchaFour(String verifyCode){
        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = servletRequestAttributes.getRequest();
        // 校验验证码
        String verifyCodeExpected = redissonUtils.get(CodeUtils.getCaptchaKey(request));
        if (!verifyCode.equalsIgnoreCase(verifyCodeExpected)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }
        boolean rst = verifyCode.equalsIgnoreCase(verifyCodeExpected);
        return rst;
    }

    private String getCaptchaKeySix(HttpServletRequest request) {
        String ip = IPUtils.getIpAddr(request);
        String userAgent = request.getHeader("User-Agent");
        String key = CAPTCHA_PREFIX_SIX + DigestUtil.md5Hex(ip + userAgent);
        return key;
    }


}
