#!/usr/bin/env bash
# 回滚到 default.target 直挂（R14 systemd 隔离前）
set -e
B=platform/r12/backup/systemd-20261027T172612
cp -a "$B"/r12-*.service "$B"/r12-*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
for u in r12-models r12-alg r12-docparse r12-graphsvc; do systemctl --user enable $u; done
for s in rag-auth-service rag-index-service rag-qa-service sensitive-words-service rag-gateway; do systemctl --user enable r12-java@$s.service; done
systemctl --user enable r12-watchdog.timer
systemctl --user disable r12.target 2>/dev/null || true
systemctl --user daemon-reload
systemctl --user status r12.target --no-pager | head -3
echo rollback-done
