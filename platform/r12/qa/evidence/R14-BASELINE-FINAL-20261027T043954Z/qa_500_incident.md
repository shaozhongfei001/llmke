# qa 服务全路径 500 取证  2026-10-27T12:40:29+0800

## 进程/制品
pid=953521 start=27 12:38:39
jar mtime=2026-10-27_12:39:47

## 全路径探测
/qa/actuator/health -> 500
/qa/ai/question -> 500

## 应用日志最后 ERROR（若有）
36132:2026-10-27 12:34:43.649 [http-nio-127.0.0.1-18083-exec-7] ERROR com.gientech.ragcommon.global.GlobalHandler - exception occur:{}
36313:2026-10-27 12:35:18.340 [http-nio-127.0.0.1-18083-exec-1] ERROR com.gientech.ragcommon.global.GlobalHandler - exception occur:{}
36523:2026-10-27 12:36:47.970 [parallel-9] ERROR reactor.util.Loggers$Slf4JLogger - Scheduler worker in group main failed with an uncaught exception

## 网关侧
2026-10-27 12:40:11.113 [reactor-http-epoll-8]  INFO com.gientech.raggateway.filter.AuthFilter - 网关鉴权开始 path:/auth/user/simpleLogin
2026-10-27 12:40:11.199 [reactor-http-epoll-9]  INFO com.gientech.raggateway.filter.AuthFilter - 网关鉴权开始 path:/qa/ai/question
2026-10-27 12:40:11.202 [reactor-http-epoll-9]  INFO com.gientech.raggateway.filter.AuthFilter - 网关鉴权完成，将用户信息传递到下游: userId:1,userName:admin,appKey:null
2026-10-27 12:40:16.414 [reactor-http-epoll-10]  INFO com.gientech.raggateway.filter.AuthFilter - 网关鉴权开始 path:/auth/user/kaptcha

## 对照：12:16–12:33 期间同一路径为 200（旧进程 pid 802208 @12:16:35）

## 关键：STALE_JAR（jar 比进程新）
jar mtime = 2026-10-27 12:39:47，进程 start = 12:38:39 → **jar 比进程新 68 秒**
即：进程启动时加载的是被覆盖前的字节，随后 jar 又被替换 → 懒加载缺类/半写文件 → 全路径 500（含 /actuator/health）。
请 r12ctl 对该服务执行 restart（不是 start）后再验。
