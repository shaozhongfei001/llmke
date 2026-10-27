#!/usr/bin/env bash
# R14：门禁自检 —— 证明"这些门禁真的会失败"，而不是只会打印绿色
#
# 为什么需要它：本轮出现过 3 次"门禁自己坏了却显示通过"
#   1) `[STALE_JAR]` 因 date 参数写错 + jar 路径重复拼接，永远返回"不 stale"（C 报，我修）
#   2) 看门狗用退出码表示告警 -> unit failed -> timer 被 systemd 停（门禁自己停摆）
#   3) 版本/历史类断言只看"有数据"不看"数据是什么"（R13 遗留，F 在收紧）
# 所以每个门禁都必须带一个**能证明它会失败**的用例：注入已知缺陷 -> 必须 FAIL；还原 -> 必须 PASS。
#
# 做法：不改仓库、不动运行态。对 check-exposure 用 PATH 注入假 `ss` 伪造监听面；
#       对 check-units 用临时目录注入重复指令。
#
# 用法: gates-selftest.sh   退出码 0=全部用例通过；1=有用例未按预期失败/通过
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d /tmp/r14-gate-selftest.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ok()   { printf '  [ok] %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  [FAIL] %s\n' "$1"; fail=$((fail+1)); }

# 造一个可控的假 ss：内容由 $1 决定
fake_ss() {  # fake_ss <输出文件>
  local out="$1"
  mkdir -p "$TMP/fakebin"
  cat > "$TMP/fakebin/ss" <<EOF
#!/usr/bin/env bash
cat "$out"
EOF
  chmod +x "$TMP/fakebin/ss"
}

echo "== 用例 A：本项目数据面出现非回环监听 -> check-exposure 必须 FAIL =="
printf 'LISTEN 0 4096 0.0.0.0:19200 0.0.0.0:*\n' > "$TMP/leak.txt"
fake_ss "$TMP/leak.txt"
if PATH="$TMP/fakebin:$PATH" bash "$R12/bin/check-exposure.sh" --expect-closed > "$TMP/a.out" 2>&1; then
  bad "数据面 0.0.0.0:19200 竟然判通过（门禁假绿）"
else
  grep -q '19200' "$TMP/a.out" && ok "非回环数据面被判 FAIL（退出非零，且列出 19200）" || bad "退出非零但输出里没有该端口"
fi

echo "== 用例 B：只有 IPv4-mapped 回环 -> check-exposure 必须 PASS =="
printf 'LISTEN 0 100 [::ffff:127.0.0.1]:18081 *:*\nLISTEN 0 100 [::ffff:7f00:1]:18082 *:*\n' > "$TMP/loop.txt"
fake_ss "$TMP/loop.txt"
if PATH="$TMP/fakebin:$PATH" bash "$R12/bin/check-exposure.sh" --expect-closed > "$TMP/b.out" 2>&1; then
  ok "[::ffff:127.0.0.1] 与 [::ffff:7f00:1] 正确识别为回环（退出 0）"
else
  bad "IPv4-mapped 回环被误判为对外（正则回归）"
  sed -n '1,12p' "$TMP/b.out" | sed 's/^/      /'
fi

echo "== 用例 C：unit 出现重复单值指令 -> check-units 必须 FAIL =="
mkdir -p "$TMP/repo/systemd" "$TMP/repo/bin"
cp "$R12/bin/check-units.sh" "$TMP/repo/bin/"
# 造一个带重复 RemainAfterExit 的 oneshot 单元（正是 R14 事故形态）
cat > "$TMP/repo/systemd/r12-selftest.service" <<'EOF'
[Unit]
Description=selftest
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/true
ExecStop=/bin/true
RemainAfterExit=no
[Install]
WantedBy=default.target
EOF
if bash "$TMP/repo/bin/check-units.sh" --repo-only > "$TMP/c.out" 2>&1; then
  bad "重复 RemainAfterExit 未被发现（门禁假绿）"
else
  grep -q 'RemainAfterExit' "$TMP/c.out" && ok "重复 RemainAfterExit 被判 FAIL（正是 11:00 事故的形态）" || bad "退出非零但没指出重复指令"
fi
# 反例：把重复去掉必须通过（证明不是"永远失败"）
sed -i '/^RemainAfterExit=no$/d' "$TMP/repo/systemd/r12-selftest.service"
if bash "$TMP/repo/bin/check-units.sh" --repo-only > "$TMP/c2.out" 2>&1; then
  ok "去掉重复后检查通过（不是恒定失败）"
else
  bad "去掉重复后仍失败（门禁误报）"
  sed -n '1,12p' "$TMP/c2.out" | sed 's/^/      /'
fi

echo "== 用例 D：STALE_JAR 判据必须能取到时间（12:40 真实故障）=="
# diag 里任何 RUNNING 服务出现 '-' 就说明取值失败（那就是 C 报的假阴性形态）
diag_out="$(bash "$R12/bin/r12ctl.sh" diag 2>/dev/null)"
if printf '%s\n' "$diag_out" | awk 'NR>1 && $2!="-" && ($3=="-" || $4=="-") {print; exit 1}'; then
  ok "diag 对所有 RUNNING 服务都取到了 JAR_TS/PROC_TS（无 '-'）"
else
  bad "diag 出现 '-'：jar 或进程时间取值失败，[STALE_JAR] 会退化为假阴性"
  printf '%s\n' "$diag_out" | sed 's/^/      /'
fi

echo
if [ "$fail" -gt 0 ]; then echo "  [FAIL] 门禁自检未通过：$fail 项（通过 $pass 项）"; exit 1; fi
echo "  [ok] 门禁自检全部通过：$pass 项（每个门禁都被证明"会失败"）"
