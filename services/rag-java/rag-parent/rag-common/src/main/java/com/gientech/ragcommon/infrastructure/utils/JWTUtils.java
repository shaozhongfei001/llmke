package com.gientech.ragcommon.infrastructure.utils;

import com.auth0.jwt.JWT;
import com.auth0.jwt.JWTVerifier;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.interfaces.Claim;
import com.auth0.jwt.interfaces.DecodedJWT;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

public class JWTUtils {

    private static final long GRACE_TIME = 24 * 60 * 60 * 1000;

    private static final String signature = "signature-gien-rag";

    public static String generateToken(Long userId, String userName) {
        try {
            long now = System.currentTimeMillis();
            Date exp = new Date(now + GRACE_TIME);
            Map<String, Object> header = new HashMap<>(2);
            header.put("typ", "JWT");
            header.put("alg", "HMAC256");
            return JWT.create()
                    .withHeader(header)
                    .withIssuer("GIEN-RAG")
                    .withAudience(userName)
                    .withClaim("userId", userId)
                    .withClaim("userName", userName)
                    .withSubject("mixedQuantum")
                    .withExpiresAt(exp)
                    .withIssuedAt(new Date(now))
                    .sign(Algorithm.HMAC256(signature));
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public static boolean verifyToken(String token, String username) {
        try {
            JWTVerifier verifier = JWT.require(Algorithm.HMAC256(signature)).withAudience(username).build();
            verifier.verify(token);
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    /**
     * 获得token中的信息
     */
    public static String getUsername(String token) {
        DecodedJWT jwt = JWT.decode(token);
        Claim userName = jwt.getClaim("userName");
        return userName.asString();
    }

    public static Long getUserId(String token) {
        DecodedJWT jwt = JWT.decode(token);
        Claim userId = jwt.getClaim("userId");
        return userId.asLong();
    }

    public static Date getExpiresTime(String token) {
        DecodedJWT jwt = JWT.decode(token);
        return jwt.getExpiresAt();
    }

    public static void main(String[] args) {
        String userName = "admin";
        Long userId = 1000L;
        String token = JWTUtils.generateToken(userId, userName);
        System.out.println(token);
        System.out.println("token验证:"+JWTUtils.verifyToken(token,userName));
        System.out.println("用户Id:"+JWTUtils.getUserId(token));
        System.out.println("用户名称:"+JWTUtils.getUsername(token));
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        System.out.println("过期时间:"+sdf.format(JWTUtils.getExpiresTime(token)));
    }
}
