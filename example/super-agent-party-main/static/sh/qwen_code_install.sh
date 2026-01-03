#!/usr/bin/env bash
set -e

# ------------ 颜色输出 ------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'

# ------------ 安装 Node.js（若未安装或版本 < 18） ------------
install_nodejs(){
    local plat=$(uname -s)
    case "$plat" in
        Linux|Darwin)
            echo -e "${YELLOW}📥 安装 nvm …${NC}"
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
            # 加载 nvm
            export NVM_DIR="$HOME/.nvm"
            # shellcheck disable=SC1090
            [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
            echo -e "${YELLOW}📦 安装 Node.js 22 …${NC}"
            nvm install 22
            ;;
        *)
            echo -e "${RED}❌ 暂不支持的系统：$plat${NC}"; exit 1
            ;;
    esac
}

if ! command -v node &>/dev/null; then
    echo -e "${YELLOW}Node.js 未安装，开始安装 …${NC}"
    install_nodejs
else
    major=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$major" -ge 18 ]; then
        echo -e "${GREEN}✅ Node.js 已安装：$(node -v)${NC}"
    else
        echo -e "${YELLOW}Node.js 版本过低，升级中 …${NC}"
        install_nodejs
    fi
fi

# ------------ 安装 Qwen Code ------------
if ! command -v qwen &>/dev/null; then
    echo -e "${YELLOW}📦 安装 Qwen Code …${NC}"
    npm install -g @qwen-code/qwen-code
else
    echo -e "${GREEN}✅ Qwen Code 已安装：$(qwen --version)${NC}"
fi

# ------------ 结束提示 ------------
echo -e "\n${GREEN}🎉 安装完成！${NC}"
echo -e "使用命令：  ${GREEN}qwen${NC}  即可启动 Qwen Code\n"