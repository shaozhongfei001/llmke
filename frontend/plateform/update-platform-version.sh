#!/bin/bash

###############################################################################
# 更新平台版本号脚本
# 功能：
#   1. 检查服务器健康状态
#   2. 获取版本信息
#   3. 更新 .env 文件中的 VITE_PLATEFORM_VERSION
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务器地址配置
HEALTH_URL="http://10.2.22.20:8999/health"
VERSION_URL="http://10.2.22.20:8999/api/version/info"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 如果脚本在根目录，ROOT_DIR 就是脚本目录；如果在子目录，ROOT_DIR 是父目录
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
    ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    ROOT_DIR="$SCRIPT_DIR"
fi
ENV_FILE="$ROOT_DIR/.env"

# 超时时间（秒）
TIMEOUT=10

###############################################################################
# 工具函数
###############################################################################

# 打印信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# 打印成功
print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 打印警告
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 打印错误
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "命令 '$1' 未找到，请先安装"
        return 1
    fi
    return 0
}

# 检查 jq 是否存在，如果不存在则使用备用方法
check_jq() {
    if command -v jq &> /dev/null; then
        return 0
    else
        print_warning "未找到 jq 命令，将使用备用方法解析 JSON" >&2
        return 1
    fi
}

###############################################################################
# 检查服务器健康状态
###############################################################################
check_health() {
    print_info "步骤 1/3: 正在检查服务器健康状态..."
    print_info "请求地址: $HEALTH_URL"
    
    # 使用 curl 发送请求
    response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -H "Content-Type: application/json" \
        "$HEALTH_URL" 2>&1) || {
        print_error "无法连接到服务器: $HEALTH_URL"
        print_error "请检查网络连接或服务器地址是否正确"
        return 1
    }
    
    # 分离响应体和状态码
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    print_info "HTTP 状态码: $http_code"
    
    # 检查 HTTP 状态码
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        print_success "服务器健康检查通过 (HTTP $http_code)"
        if [ -n "$response_body" ]; then
            print_info "服务器响应: $response_body"
        fi
        return 0
    else
        print_error "服务器响应异常 (HTTP $http_code)"
        if [ -n "$response_body" ]; then
            print_error "错误信息: $response_body"
        fi
        return 1
    fi
}

###############################################################################
# 获取版本信息
###############################################################################
get_version_info() {
    print_info "" >&2
    print_info "步骤 2/3: 正在获取版本信息..." >&2
    print_info "请求地址: $VERSION_URL" >&2
    
    # 使用 curl 发送请求
    response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -H "Content-Type: application/json" \
        "$VERSION_URL" 2>&1) || {
        print_error "无法连接到服务器: $VERSION_URL" >&2
        print_error "请检查网络连接或服务器地址是否正确" >&2
        return 1
    }
    
    # 分离响应体和状态码
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    print_info "HTTP 状态码: $http_code" >&2
    
    # 检查 HTTP 状态码
    if [ "$http_code" -lt 200 ] || [ "$http_code" -ge 300 ]; then
        print_error "获取版本信息失败 (HTTP $http_code)" >&2
        if [ -n "$response_body" ]; then
            print_error "错误信息: $response_body" >&2
        fi
        return 1
    fi
    
    print_info "服务器响应: $response_body" >&2
    
    # 尝试使用 jq 解析，如果失败则使用备用方法
    # 先检查 jq 是否存在（静默检查，不输出警告）
    if command -v jq &> /dev/null; then
        print_info "使用 jq 解析 JSON 响应..." >&2
        version=$(echo "$response_body" | jq -r '.product.version // empty' 2>/dev/null)
        
        if [ -z "$version" ] || [ "$version" = "null" ]; then
            print_error "响应数据中未找到 product.version 字段" >&2
            print_error "请检查 API 响应格式是否正确" >&2
            return 1
        fi
    else
        print_warning "未找到 jq 命令，将使用备用方法解析 JSON" >&2
        print_info "使用备用方法解析 JSON 响应..." >&2
        # 使用 grep 和 sed 提取版本号
        # 匹配 "product": { "version": "xxx" } 或类似格式
        version=$(echo "$response_body" | grep -o '"product"[[:space:]]*:[[:space:]]*{[^}]*"version"[[:space:]]*:[[:space:]]*"[^"]*"' | \
            sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
        
        if [ -z "$version" ]; then
            # 尝试更宽松的匹配
            version=$(echo "$response_body" | grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | \
                sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
        fi
        
        if [ -z "$version" ]; then
            print_error "无法从响应中提取版本号" >&2
            print_error "响应内容: $response_body" >&2
            print_error "请检查 API 响应格式，或安装 jq 工具以获得更好的 JSON 解析支持" >&2
            return 1
        fi
    fi
    
    print_success "成功获取版本号: $version" >&2
    # 清理版本号：去除前后空白和换行符，只输出版本号到 stdout
    echo -n "$version" | tr -d '\n\r' | xargs
}

###############################################################################
# 更新 .env 文件
###############################################################################
update_env_file() {
    local version=$1
    
    if [ -z "$version" ]; then
        print_error "版本号为空，无法更新"
        return 1
    fi
    
    print_info ""
    print_info "步骤 3/3: 正在更新 .env 文件..."
    print_info "目标文件: $ENV_FILE"
    print_info "版本号: $version"
    
    # 检查 .env 文件是否存在
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env 文件不存在，将创建新文件"
        touch "$ENV_FILE"
    fi
    
    # 检查是否已存在 VITE_PLATEFORM_VERSION
    if grep -q "^VITE_PLATEFORM_VERSION" "$ENV_FILE" 2>/dev/null; then
        print_info "发现已存在的 VITE_PLATEFORM_VERSION 配置，将更新..."
        
        # 备份原文件
        cp "$ENV_FILE" "$ENV_FILE.bak"
        print_info "已创建备份文件: $ENV_FILE.bak"
        
        # 清理版本号中的特殊字符，防止 sed 命令出错
        clean_version=$(echo -n "$version" | tr -d '\n\r\t' | sed 's/[\/&]/\\&/g')
        
        # 使用 sed 更新版本号（兼容 macOS 和 Linux）
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS 版本
            sed -i '' "s/^VITE_PLATEFORM_VERSION=.*/VITE_PLATEFORM_VERSION=$clean_version/" "$ENV_FILE"
        else
            # Linux 版本
            sed -i "s/^VITE_PLATEFORM_VERSION=.*/VITE_PLATEFORM_VERSION=$clean_version/" "$ENV_FILE"
        fi
        
        # 验证更新是否成功
        if grep -q "^VITE_PLATEFORM_VERSION=$clean_version" "$ENV_FILE" 2>/dev/null; then
            print_success "已更新 VITE_PLATEFORM_VERSION=$version"
            # 更新成功，删除临时备份文件
            rm -f "$ENV_FILE.bak"
            print_info "已删除临时备份文件"
        else
            print_error "更新失败，正在恢复备份..."
            # 更新失败，恢复备份
            if [ -f "$ENV_FILE.bak" ]; then
                cp "$ENV_FILE.bak" "$ENV_FILE"
                print_warning "已从备份恢复 .env 文件"
            fi
            return 1
        fi
    else
        print_info "未找到 VITE_PLATEFORM_VERSION 配置，将添加新配置..."
        
        # 确保文件末尾有换行符
        if [ -s "$ENV_FILE" ] && [ "$(tail -c 1 "$ENV_FILE")" != "" ]; then
            echo "" >> "$ENV_FILE"
        fi
        
        # 追加新配置
        echo "VITE_PLATEFORM_VERSION=$version" >> "$ENV_FILE"
        print_success "已添加 VITE_PLATEFORM_VERSION=$version"
    fi
    
    print_success "已成功更新 .env 文件"
    print_info "文件路径: $ENV_FILE"
}

###############################################################################
# 主函数
###############################################################################
main() {
    echo ""
    echo "=========================================="
    echo "  平台版本号更新脚本"
    echo "=========================================="
    echo ""
    
    # 检查必要的命令
    print_info "检查必要的工具..."
    if ! check_command "curl"; then
        print_error "请先安装 curl 工具"
        exit 1
    fi
    print_success "工具检查通过"
    echo ""
    
    # 步骤 1: 检查服务器健康状态
    if ! check_health; then
        print_error ""
        print_error "服务器健康检查失败，终止操作"
        exit 1
    fi
    
    # 步骤 2: 获取版本信息
    # 使用临时文件来分离 stdout 和 stderr
    temp_version_file=$(mktemp)
    temp_stderr_file=$(mktemp)
    
    # 执行函数，将 stderr 输出到临时文件，stdout 也输出到临时文件
    get_version_info > "$temp_version_file" 2> "$temp_stderr_file"
    func_exit_code=$?
    
    # 显示 stderr 中的提示信息
    cat "$temp_stderr_file" >&2
    
    # 读取版本号并清理
    version=$(cat "$temp_version_file" | tr -d '\n\r\t ' | xargs)
    
    # 清理临时文件
    rm -f "$temp_version_file" "$temp_stderr_file"
    
    if [ $func_exit_code -ne 0 ] || [ -z "$version" ]; then
        print_error ""
        print_error "获取版本信息失败，终止操作"
        exit 1
    fi
    
    # 步骤 3: 更新 .env 文件
    update_env_file "$version"
    if [ $? -ne 0 ]; then
        print_error ""
        print_error "更新 .env 文件失败"
        exit 1
    fi
    
    echo ""
    echo "=========================================="
    print_success "版本号更新完成！"
    echo "=========================================="
    echo ""
    print_info "当前版本号: $version"
    print_info "配置文件: $ENV_FILE"
    echo ""
}

# 执行主函数
main

