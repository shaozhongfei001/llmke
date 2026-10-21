# DNS / /etc/hosts 解析陷阱

> 通用运维经验模板。示例中的主机名一律使用 `<db-hostname>` 占位；
> 请替换为你自己环境的值，真实主机名/IP 不得提交进仓库。

## 问题
当 Oracle 连接配置使用主机名（如 `<db-hostname>`）而非 IP 时，/etc/hosts 中的错误条目会导致主机名解析到 `127.0.0.1`，从而连接超时 (ORA-12170)。

## 检测方法
```bash
getent hosts <db-hostname>
# 如果返回 127.0.0.1 而非真实内网 IP，则存在此问题
```

## 原因
/etc/hosts 中有类似条目覆盖了真实 DNS：
```
127.0.0.1 <db-hostname>
```

## 修复
注释掉 /etc/hosts 中的错误条目：
```bash
sudo sed -i '/^127\.0\.0\.1\s\+<db-hostname>/s/^/# /' /etc/hosts
```

验证：
```bash
getent hosts <db-hostname>
# 应返回真实内网 IP
```

## 注意事项
- 修改 /etc/hosts 需要 sudo 权限
- 自动化 patch 工具通常会拒绝写入 /etc/hosts（系统敏感文件），必须用 terminal + sudo
- Step 1 校验输入参数时应主动检查 DNS 解析，不要等到连接超时才发现
- 如果环境无法修改 /etc/hosts，可以改用直接指定 IP 地址作为 ORACLE_HOST（该值只进本地 .env，不进 git）

## 历史
- 某实战环境曾把数据库主机名错误映射到 127.0.0.1（虚拟机端口转发残留条目），改为正确 DNS 解析后恢复
