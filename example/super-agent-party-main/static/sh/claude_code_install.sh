#!/bin/bash

# 脚本出错时立即退出
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 安装 Node.js 的函数
install_nodejs() {
    local platform=$(uname -s)
    
    case "$platform" in
        Linux|Darwin)
            echo -e "${YELLOW}🚀 Installing Node.js on Unix/Linux/macOS｜安装 Node.js...${NC}"
            echo -e "${YELLOW}📥 Downloading and installing nvm｜安装 nvm...${NC}"
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
            echo -e "${YELLOW}🔄 Loading nvm environment｜加载 nvm 环境变量...${NC}"
            \. "$HOME/.nvm/nvm.sh"
            echo -e "${YELLOW}📦 Downloading and installing Node.js v22｜安装 Node.js v22...${NC}"
            nvm install 22
            echo -e "${GREEN}✅ Node.js installation completed! Version｜Node.js 已安装，当前版本: $(node -v)${NC}"
            echo -e "${GREEN}✅ Current nvm version｜当前 nvm 版本: $(nvm current)${NC}"
            echo -e "${GREEN}✅ npm version｜npm 版本: $(npm -v)${NC}"
            ;;
        *)
            echo -e "${RED}Unsupported platform｜暂不支持的系统: $platform${NC}"
            exit 1
            ;;
    esac
}

# 检查 Node.js
if command -v node >/dev/null 2>&1; then
    current_version=$(node -v | sed 's/v//')
    major_version=$(echo "$current_version" | cut -d. -f1)
    
    if [ "$major_version" -ge 18 ]; then
        echo -e "${GREEN}Node.js is already installed｜Node.js 已安装: v$current_version${NC}"
    else
        echo -e "${YELLOW}Node.js v$current_version is installed but version < 18. Upgrading｜Node.js 版本升级中...${NC}"
        install_nodejs
    fi
else
    echo -e "${YELLOW}Node.js not found. Installing｜Node.js 未安装，开始安装...${NC}"
    install_nodejs
fi

# 检查 Claude Code
if command -v claude >/dev/null 2>&1; then
    echo -e "${GREEN}Claude Code is already installed｜Claude Code 已安装: $(claude --version)${NC}"
else
    echo -e "${YELLOW}Claude Code not found. Installing｜Claude Code 未安装，开始安装...${NC}"
    npm install -g @anthropic-ai/claude-code
fi

# 配置 Claude Code
echo -e "${YELLOW}Configuring Claude Code to skip onboarding｜免除 Claude Code 的 onboarding 环节...${NC}"
node --eval '
    const fs = require("fs");
    const os = require("os");
    const path = require("path");
    const homeDir = os.homedir(); 
    const filePath = path.join(homeDir, ".claude.json");
    try {
        let config = {};
        if (fs.existsSync(filePath)) {
            config = JSON.parse(fs.readFileSync(filePath, "utf-8"));
        }
        config.hasCompletedOnboarding = true;
        fs.writeFileSync(filePath, JSON.stringify(config, null, 2), "utf-8");
    } catch (e) {}'

# --- 环境变量配置 ---

# 1. 确定 shell 配置文件
current_shell=$(basename "$SHELL")
case "$current_shell" in
    bash) rc_file="$HOME/.bashrc" ;;
    zsh) rc_file="$HOME/.zshrc" ;;
    fish) rc_file="$HOME/.config/fish/config.fish" ;;
    *) rc_file="$HOME/.profile" ;;
esac

# 2. 检查现有配置
existing_config=false
if [ -f "$rc_file" ]; then
    if grep -q "export ANTHROPIC_BASE_URL=" "$rc_file" && \
       grep -q "export ANTHROPIC_API_KEY=" "$rc_file" && \
       grep -q "export ANTHROPIC_MODEL=" "$rc_file"; then
        existing_config=true
        
        current_url=$(grep "export ANTHROPIC_BASE_URL=" "$rc_file" | head -n 1 | cut -d'=' -f2 | tr -d '"')
        current_key=$(grep "export ANTHROPIC_API_KEY=" "$rc_file" | head -n 1 | cut -d'=' -f2 | tr -d '"')
        current_model=$(grep "export ANTHROPIC_MODEL=" "$rc_file" | head -n 1 | cut -d'=' -f2 | tr -d '"')
        
        echo -e "${YELLOW}⚠️  Existing configuration detected in $rc_file｜检测到已有配置:${NC}"
        echo -e "  - API URL: $current_url"
        echo -e "  - API Key: ${current_key:0:4}****${current_key: -4}"
        echo -e "  - Model: $current_model"
        
        # 询问用户是否要修改配置
        read -p "Do you want to modify the configuration? (y/n)｜是否要修改配置? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}✅ Keeping existing configuration｜保留当前配置${NC}"
            echo -e "\n🔄 Please restart your terminal or run｜重新启动终端并运行:"
            echo -e "   source $rc_file"
            echo -e "\n🚀 Then you can start using Claude Code with｜使用下面命令进入 Claude Code:"
            echo -e "   claude"
            exit 0
        fi
        
        # 询问用户要修改哪些配置项
        echo -e "\n🔧 Which configuration items do you want to modify?｜请选择要修改的配置项:"
        echo -e "1. API URL"
        echo -e "2. API Key"
        echo -e "3. Model"
        echo -e "4. All of the above|上述全部"
        read -p "Enter your choice (1-4)｜输入你的选择 (1-4): " choice
        
        case $choice in
            1)
                read -p "Enter new API URL (current: $current_url)｜输入新的 API URL (当前: $current_url): " api_url
                api_url=${api_url:-$current_url}
                api_key=$current_key
                model=$current_model
                ;;
            2)
                echo -e "\n🔑 Enter new API Key (current: ${current_key:0:4}****${current_key: -4})｜输入新的 API Key (当前: ${current_key:0:4}****${current_key: -4}):"
                echo -e "   Note: The input is hidden for security. Please paste your API Key directly.｜注意：输入的内容不会显示在屏幕上，请直接输入"
                read -s api_key
                api_key=${api_key:-$current_key}
                api_url=$current_url
                model=$current_model
                echo
                ;;
            3)
                read -p "Enter new model name (current: $current_model)｜输入新的模型名称 (当前: $current_model): " model
                model=${model:-$current_model}
                api_url=$current_url
                api_key=$current_key
                ;;
            4)
                # 获取新的 API URL
                read -p "Enter new API URL (current: $current_url)｜输入新的 API URL (当前: $current_url): " api_url
                api_url=${api_url:-$current_url}
                
                # 获取新的 API Key
                echo -e "\n🔑 Enter new API Key (current: ${current_key:0:4}****${current_key: -4})｜输入新的 API Key (当前: ${current_key:0:4}****${current_key: -4}):"
                echo -e "   Note: The input is hidden for security. Please paste your API Key directly.｜注意：输入的内容不会显示在屏幕上，请直接输入"
                read -s api_key
                api_key=${api_key:-$current_key}
                echo
                
                # 获取新的 Model
                read -p "Enter new model name (current: $current_model)｜输入新的模型名称 (当前: $current_model): " model
                model=${model:-$current_model}
                ;;
            *)
                echo -e "${RED}Invalid choice｜无效的选择${NC}"
                exit 1
                ;;
        esac
    fi
fi

# 如果没有现有配置，或者用户选择了全部修改，则获取新配置
if [ "$existing_config" = false ]; then
    echo -e "\n🔧 Please configure the Claude Code parameters, the API interface must be of the Anthropic type."
    echo -e "\n🔧 请配置 Claude Code 参数，API接口必须为Anthropic类型的接口"
    
    # API URL
    echo -e "\n🌐 Enter the API URL (e.g. https://api.deepseek.com/anthropic/)｜输入 API URL (例如 https://api.deepseek.com/anthropic/):"
    read -p "API URL: " api_url
    while [ -z "$api_url" ]; do
        echo -e "${RED}⚠️  API URL cannot be empty｜API URL 不能为空${NC}"
        read -p "API URL: " api_url
    done

    # API Key
    echo -e "\n🔑 Enter your API Key｜输入你的 API Key:"
    echo -e "   Note: The input is hidden for security. Please paste your API Key directly.｜注意：输入的内容不会显示在屏幕上，请直接输入"
    read -s api_key
    echo
    while [ -z "$api_key" ]; do
        echo -e "${RED}⚠️  API Key cannot be empty｜API Key 不能为空${NC}"
        read -s api_key
        echo
    done

    # Model
    echo -e "\n🤖 Enter the model name (e.g. deepseek-chat)｜输入模型名称 (例如 deepseek-chat):"
    read -p "Model: " model
    while [ -z "$model" ]; do
        echo -e "${RED}⚠️  Model name cannot be empty｜模型名称不能为空${NC}"
        read -p "Model: " model
    done
fi

# 4. 更新环境变量
echo -e "\n${YELLOW}📝 Updating environment variables in $rc_file...｜正在更新环境变量到 $rc_file${NC}"

# 如果 rc 文件存在，则先清理旧的配置
if [ -f "$rc_file" ]; then
    temp_file=$(mktemp)
    grep -v -e "# Claude Code environment variables" \
            -e "export ANTHROPIC_BASE_URL" \
            -e "export ANTHROPIC_API_KEY" \
            -e "export ANTHROPIC_MODEL" "$rc_file" > "$temp_file"
    mv "$temp_file" "$rc_file"
fi

# 追加新的配置到文件末尾
echo "" >> "$rc_file"
echo "# Claude Code environment variables" >> "$rc_file"
echo "export ANTHROPIC_BASE_URL=\"$api_url\"" >> "$rc_file"
echo "export ANTHROPIC_API_KEY=\"$api_key\"" >> "$rc_file"
echo "export ANTHROPIC_MODEL=\"$model\"" >> "$rc_file"

echo -e "${GREEN}✅ Environment variables successfully updated in $rc_file${NC}"

echo -e "\n🎉 Configuration completed successfully｜配置已完成 🎉"
echo -e "\n🔄 Please restart the super agent party for the configuration to take effect.｜请重启super agent party以使配置生效"
echo -e "\n🔄 Please restart your terminal or run｜重新启动终端并运行:"
echo -e "   source $rc_file"
echo -e "\n🚀 Then you can start using Claude Code with｜使用下面命令进入 Claude Code:"
echo -e "   claude"