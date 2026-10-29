#!/usr/bin/env bash
# R14：接口注册表补齐（幂等）—— 新增 Java 端点后不必人工插 SQL
#
# 背景（真实卡点）：网关做**接口级**鉴权，权限来自 gienrag.interface_info + resource_interface。
# C 新增 `GET /index/knowledgeBase/file/presign`（引用原文短时效预签名）后，直连服务 200，
# 经网关一律 `401 {"errorCode":"30021","没有足够的权限"}`——因为 interface_info 里没有这条 url。
# 当时靠 TL 手工插行救火。凡是"上线新端点"都会重演，所以固化成脚本。
#
# 口径：
#   - 幂等：按 (url, method) 查 interface_info；缺则插，已存在则只补映射
#   - 映射：resource_interface(resource_id, interface_id, is_del=1) 与既有 viewFile/previewStream 同口径
#   - 失败即非零退出（不允许"插了一半还报成功"）
#
# 用法: init-endpoints.sh [容器名=r12-mysql] [库名=gienrag]
set -uo pipefail
R12="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CT="${1:-r12-mysql}"
DB="${2:-gienrag}"

ok()   { printf '  [ok] %s\n' "$1"; }
warn() { printf '  [!!] %s\n' "$1"; }
die()  { printf '  [FAIL] %s\n' "$1"; exit 1; }

# --- 必需端点清单：url|method|app_name|app_abbr|名称|resource_id ---
# resource_id=8 是 index 服务的资源，与 seed 里 viewFile/previewStream 一致
ENDPOINTS=(
  "/index/knowledgeBase/file/presign|GET|rag-index-service|index|引用原文预签名（短时效）|8"

  # R14-LIVE-04：/graph/* 在 seed 里 interface_info 有 17 条，但 resource_interface 一条都没挂，
  # 网关 authenticate() 恒 false —— 任何角色（含 admin）访问图谱一律 401/30021。
  # 现象极具误导性：菜单能点、页面能进，只有图数据接口全红。
  "/graph/info/nodes|GET|rag-graph-service|graph|图节点类型|8"
  "/graph/info/edges|GET|rag-graph-service|graph|图边类型|8"
  "/graph/graphStatistics/getWholeGraphStatistics|GET|rag-graph-service|graph|全图统计|8"
  "/graph/search/wholeGraphSearch|POST|rag-graph-service|graph|全图检索|8"
  "/graph/search/subGraph|GET|rag-graph-service|graph|子图检索|8"
  "/graph/search/file/pageNum|GET|rag-graph-service|graph|按页取三元组|8"
  "/graph/search/instances|GET|rag-graph-service|graph|图实例|8"
  "/graph/search/keywordSearch|GET|rag-graph-service|graph|关键词检索|8"
  "/graph/search/nodeSearch|POST|rag-graph-service|graph|节点检索|8"
  "/graph/search/edgeSearch|POST|rag-graph-service|graph|边检索|8"
  "/graph/search/searchNodesByIds|POST|rag-graph-service|graph|按 id 查节点|8"
  "/graph/search/nodeStepSearch|POST|rag-graph-service|graph|单跳检索|8"
  "/graph/search/commonNeighbourSearch|POST|rag-graph-service|graph|共同邻居|8"
  "/graph/search/pathSearch|POST|rag-graph-service|graph|路径检索|8"
  "/graph/search/cypherSearch|POST|rag-graph-service|graph|cypher 检索|8"
  "/graph/search/canSearchNodeOneStep|GET|rag-graph-service|graph|可单跳判定|8"
  "/graph/search/ping|GET|rag-graph-service|graph|连通性探针|8"
)

# 口令解析顺序与 init-db.sh 保持一致（否则两个脚本对"没配 .env"的反应不同，装机时更难判）
ROOT_PW="${R12_MYSQL_ROOT_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}"
if [ -z "$ROOT_PW" ] && [ -f "${R12_ENV_FILE:-$R12/.env}" ]; then
  ROOT_PW="$(sed -n 's/^R12_MYSQL_ROOT_PASSWORD=//p' "${R12_ENV_FILE:-$R12/.env}" | head -1)"
fi
if [ -z "$ROOT_PW" ]; then
  printf '  [FAIL] 缺少 R12_MYSQL_ROOT_PASSWORD\n' >&2
  printf '         先执行安装文档第 3 步：cp %s/.env.template %s/.env 并填写口令\n' "$R12" "$R12" >&2
  exit 1
fi
docker ps --format '{{.Names}}' | grep -qx "$CT" || die "容器 $CT 未运行（先 docker compose up -d mysql）"

my() { docker exec -e MYSQL_PWD="$ROOT_PW" "$CT" mysql -uroot --default-character-set=utf8mb4 -N -B "$DB" -e "$1" 2>&1; }

echo "== init-endpoints（container=$CT db=$DB）=="
added=0; mapped=0; skipped=0
for row in "${ENDPOINTS[@]}"; do
  IFS='|' read -r url method app app_abbr name res_id <<< "$row"
  iid="$(my "select id from interface_info where url='$url' and method='$method' order by id limit 1;")"
  if [[ "$iid" =~ ^[0-9]+$ ]]; then
    ok "已存在 interface_info: $method $url (id=$iid)"
    skipped=$((skipped+1))
  else
    case "$iid" in *ERROR*|*error*) die "查询 interface_info 失败: $iid" ;; esac
    out="$(my "insert into interface_info(app_name,app_name_abbreviate,name,url,method,gmt_create,gmt_modified,create_by,update_by) values('$app','$app_abbr','$name','$url','$method',now(),now(),'r14-init','r14-init'); select last_insert_id();")"
    iid="$(printf '%s\n' "$out" | tail -1)"
    [[ "$iid" =~ ^[0-9]+$ ]] || die "插入 interface_info 失败: $out"
    ok "新增 interface_info: $method $url (id=$iid)"
    added=$((added+1))
  fi
  # 映射（幂等）
  cnt="$(my "select count(*) from resource_interface where resource_id=$res_id and interface_id=$iid;")"
  if [[ "$cnt" =~ ^[0-9]+$ ]] && [ "$cnt" -gt 0 ]; then
    ok "映射已存在: resource_id=$res_id <-> interface_id=$iid"
  else
    out="$(my "insert into resource_interface(resource_id,interface_id,is_del,gmt_create,gmt_modified,create_by,update_by) values($res_id,$iid,1,now(),now(),'r14-init','r14-init'); select last_insert_id();")"
    printf '%s' "$out" | grep -qE '^[0-9]+$' || die "插入 resource_interface 失败: $out"
    ok "新增映射: resource_id=$res_id <-> interface_id=$iid（is_del=1，与 seed 同口径）"
    mapped=$((mapped+1))
  fi
done

echo "== 回读校验 =="
for row in "${ENDPOINTS[@]}"; do
  IFS='|' read -r url method _ _ _ res_id <<< "$row"
  got="$(my "select count(*) from interface_info i join resource_interface r on r.interface_id=i.id where i.url='$url' and i.method='$method' and r.resource_id=$res_id;")"
  [[ "$got" =~ ^[0-9]+$ ]] || die "回读失败: $got"
  [ "$got" -ge 1 ] || die "回读不一致：$method $url 与 resource_id=$res_id 的映射不存在"
  ok "回读通过: $method $url -> resource_id=$res_id（映射 $got 条）"
done
printf '  [..] 新增 interface=%s 新增映射=%s 已存在跳过=%s\n' "$added" "$mapped" "$skipped"
ok "接口注册表补齐完成（幂等，可重复执行）"

# R14-LIVE-12：补完之后再做一次**代码 vs 注册表**的对账。
# 前面这一步只保证"清单里的接口都在"，对账保证"代码里的接口都在清单里"——
# 前者防漏配，后者防"新加了接口忘了加清单"。装机时只告警不失败（--warn-only），
# 发布前用不带 --warn-only 的方式跑，缺失即失败。
if [ -x "$(dirname "${BASH_SOURCE[0]}")/check-endpoints-sync.py" ]; then
  R12_MYSQL_ROOT_PASSWORD="$ROOT_PW" "$(dirname "${BASH_SOURCE[0]}")/check-endpoints-sync.py" --warn-only \
    || warn "接口对账脚本执行异常（不阻断装机，但请人工确认）"
fi
