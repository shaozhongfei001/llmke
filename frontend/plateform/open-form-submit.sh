#!/bin/bash

###############################################################################
# 打开表单提交页面脚本
# 功能：在浏览器中打开 http://10.2.22.20:8999/form-submit
###############################################################################

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 表单地址
FORM_URL="http://10.2.22.20:8999/form-submit"

# 打开浏览器
open_browser() {
    local url=$1
    
    # 根据操作系统选择打开浏览器的方式
    case "$(uname -s)" in
        Darwin*)
            # macOS
            open "$url" 2>/dev/null && return 0
            ;;
        Linux*)
            # Linux
            if command -v xdg-open &> /dev/null; then
                xdg-open "$url" 2>/dev/null && return 0
            elif command -v gnome-open &> /dev/null; then
                gnome-open "$url" 2>/dev/null && return 0
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            # Windows (Git Bash, MSYS2, Cygwin)
            start "$url" 2>/dev/null && return 0
            ;;
    esac
    
    return 1
}

# 主函数
main() {
    echo ""
    echo -e "${BLUE}正在打开浏览器...${NC}"
    
    if open_browser "$FORM_URL"; then
        echo -e "${GREEN}✓ 已成功打开浏览器${NC}"
        echo -e "${BLUE}URL: ${FORM_URL}${NC}"
    else
        echo ""
        echo -e "${BLUE}无法自动打开浏览器，请手动访问：${NC}"
        echo -e "${GREEN}点击填写版本表单：${FORM_URL}${NC}"
        echo ""
    fi
}

# 执行主函数
main

