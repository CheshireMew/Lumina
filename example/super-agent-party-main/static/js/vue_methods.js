const md = window.markdownit({
    html: true,
    linkify: true,
    typographer: true,
    highlight: function (str, lang) {
    let language = lang === 'a2ui' || (lang && hljs.getLanguage(lang)) ? lang : 'plaintext';
    const isPotentialMermaid = (code) => {
    // 检测标准语法特征
    const mermaidPatterns = [
        // 检测图表类型声明
        /^\s*(graph|sequenceDiagram|gantt|classDiagram|pie|stateDiagram|gitGraph|journey|flowchart|mindmap|quadrantChart|erDiagram|requirementDiagram|gitGraph|C4Context|timeline|zenuml|sankey-beta|xychart-beta|block-beta|packet-beta|kanban|architecture-beta|radar-beta)\b/i,
        // 检测节点关系语法
        /-->|==>|:::|\|\|/,
        // 检测样式配置语法
        /^style\s+[\w]+\s+/im,
        // 检测注释语法
        /%%\{.*\}\n?/
    ];
    
    return mermaidPatterns.some(pattern => pattern.test(code));
    };
    // 自动升级普通文本中的 Mermaid 内容
    if (language === 'plaintext' && isPotentialMermaid(str)) {
    language = 'mermaid';
    };
    const previewable = ['html', 'mermaid'].includes(language);
    const downloadButton = previewable ? 
    `<button class="download-button" data-lang="${language}"><i class="fa-solid fa-download"></i></button>` : '';
    // 添加预览按钮
    const previewButton = previewable ? 
    `<button class="preview-button" data-lang="${language}"><i class="fa-solid fa-eye"></i></button>` : '';
    try {
    return `<pre class="code-block"><div class="code-header"><span class="code-lang">${language}</span><div class="code-actions">${previewButton}${downloadButton}<button class="copy-button"><i class="fa-solid fa-copy"></i></button></div></div><div class="code-content"><code class="hljs language-${language}">${hljs.highlight(str, { language }).value}</code></div></pre>`;
    } catch (__) {
    return `<pre class="code-block"><div class="code-header"><span class="code-lang">${language}</span><div class="code-actions">${previewButton}${downloadButton}<button class="copy-button"><i class="fa-solid fa-copy"></i></button></div></div><div class="code-content"><code class="hljs">${md.utils.escapeHtml(str)}</code></div></pre>`;
    }
}
});

if (window.markdownitFootnote) {
    md.use(window.markdownitFootnote);
    
    // 【新增】覆盖默认的脚注渲染规则，只返回数字，去掉方括号 []
    md.renderer.rules.footnote_caption = (tokens, idx) => {
        var n = Number(tokens[idx].meta.id + 1).toString();
        return n;
    };
}

if (window.markdownitTaskLists) {
    md.use(window.markdownitTaskLists, {
        enabled: true,   // 渲染为 <input type="checkbox">
        label: true,     // 将文字包裹在 <label> 中
        labelAfter: true // label 放在 checkbox 之后
    });
} else {
    console.warn('markdown-it-task-lists 插件未加载，任务列表将不会渲染。');
}

// 检查插件是否已加载
if (window.markdownitContainer) {
    
    // 1. 定义 "warning" 容器 (对应 CSS 中的 .highlight-block-reasoning)
    // 使用方法: 
    // ::: warning 标题
    // 内容...
    // :::
    md.use(window.markdownitContainer, 'warning', {
        validate: function(params) {
            return params.trim().match(/^warning\s*(.*)$/);
        },
        render: function (tokens, idx) {
            var m = tokens[idx].info.trim().match(/^warning\s*(.*)$/);
            if (tokens[idx].nesting === 1) {
                // 开头标签: <div class="highlight-block-reasoning"> ...
                var title = m[1] ? md.utils.escapeHtml(m[1]) : '';
                var titleHtml = title ? '<strong>' + title + '</strong><br>' : '';
                return '<div class="highlight-block-reasoning">' + titleHtml;
            } else {
                // 结束标签: </div>
                return '</div>\n';
            }
        }
    });

    // 2. 定义 "info" 容器 (对应 CSS 中的 .highlight-block)
    // 使用方法: 
    // ::: info 提示
    // 内容...
    // :::
    md.use(window.markdownitContainer, 'info', {
        validate: function(params) {
            return params.trim().match(/^info\s*(.*)$/);
        },
        render: function (tokens, idx) {
            var m = tokens[idx].info.trim().match(/^info\s*(.*)$/);
            if (tokens[idx].nesting === 1) {
                var title = m[1] ? md.utils.escapeHtml(m[1]) : '';
                var titleHtml = title ? '<strong>' + title + '</strong><br>' : '';
                return '<div class="highlight-block">' + titleHtml;
            } else {
                return '</div>\n';
            }
        }
    });
} else {
    console.warn('markdown-it-container 插件未加载，自定义容器将不会渲染。');
}


// 添加更复杂的临时占位符
const LATEX_PLACEHOLDER_PREFIX = 'LATEX_PLACEHOLDER_';
let latexPlaceholderCounter = 0;

const ALLOWED_EXTENSIONS = [
// 办公文档
    'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'pdf', 'pages', 
    'numbers', 'key', 'rtf', 'odt', 'epub',

// 编程开发
'js', 'ts', 'py', 'java', 'c', 'cpp', 'h', 'hpp', 'go', 'rs',
'swift', 'kt', 'dart', 'rb', 'php', 'html', 'css', 'scss', 'less',
'vue', 'svelte', 'jsx', 'tsx', 'json', 'xml', 'yml', 'yaml', 
'sql', 'sh',

// 数据配置
'csv', 'tsv', 'txt', 'md', 'log', 'conf', 'ini', 'env', 'toml'
]
// MIME类型白名单
const MIME_WHITELIST = [
'text/plain',
'application/msword',
'application/vnd.openxmlformats-officedocument',
'application/pdf',
'application/json',
'text/csv',
'text/x-python',
'application/xml',
'text/x-go',
'text/x-rust',
'text/x-swift',
'text/x-kotlin',
'text/x-dart',
'text/x-ruby',
'text/x-php'
]

// 图片上传相关配置
const ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'];
const IMAGE_MIME_WHITELIST = [
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
  'image/bmp'
];

let vue_methods = {
  handleUpdateAction() {
    if (this.updateDownloaded) {
      window.electronAPI.quitAndInstall();
    } else if (this.updateAvailable) {
      window.electronAPI.downloadUpdate();
    }
  },
  formatFileUrl(originalUrl) {
    if (!this.isElectron) {
      try {
        const url = new URL(originalUrl);
        // 替换0.0.0.0为当前域名
        if (url.hostname === '0.0.0.0' || url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
          url.hostname = window.location.hostname;
          // 如果需要强制使用HTTPS可以添加：
          url.protocol = window.location.protocol;
          url.port = window.location.port;
        }
        return url.toString();
      } catch(e) {
        return originalUrl;
      }
    }
    else {
      try {
        const url = new URL(originalUrl);
        if (url.hostname === '127.0.0.1') {
          url.hostname = "localhost";
          // 如果需要强制使用HTTPS可以添加：
          url.protocol = window.location.protocol;
          url.port = window.location.port;
        }
        return url.toString();
      } catch(e) {
        return originalUrl;
      }
    }
    return originalUrl;
  },
  async resetMessage(index) {
    this.messages[index].content = " ";
    this.system_prompt = " ";
    await this.autoSaveSettings();
  },

  async deleteMessage(index) {
    this.stopGenerate();
    this.messages.splice(index, 1);
    await this.autoSaveSettings();
  },

  openEditDialog(type, content, index = null) {
    this.editType = type;
    this.editContent = content;
    this.editIndex = index;
    this.showEditDialog = true;
    this.selectSystemPromptId =null;
  },
  async saveEdit() {
    this.showEditDialog = false;
    if (this.editType === 'system') {
      this.system_prompt = this.editContent;
    }
    if (this.editType === 'user') {
      // 移除this.editIndex之后的所有消息
      this.messages.splice(this.editIndex);
      this.userInput = this.editContent;
      this.stopGenerate();
      await this.sendMessage();
    }else{
      this.messages[this.editIndex].content = this.editContent; // 更新this.editIndex对应的消息内容
    }
    await this.autoSaveSettings();
  },
    async addParam() {
      this.settings.extra_params.push({
        name: '',
        type: 'string',  // 默认类型
        value: ''        // 根据类型自动初始化
      });
      await this.autoSaveSettings();
    },
    async updateParamType(index) {
      const param = this.settings.extra_params[index];
      // 根据类型初始化值
      switch(param.type) {
        case 'boolean':
          param.value = false;
          break;
        case 'integer':
        case 'float':
          param.value = 0;
          break;
        default:
          param.value = '';
      }
      await this.autoSaveSettings();
    },
    async removeParam(index) {
      this.settings.extra_params.splice(index, 1);
      await this.autoSaveSettings();
    },
    switchTollmTools() {
      this.activeMenu = 'toolkit';
      this.subMenu = 'llmTool';
    },
    switchToHttpTools() {
      this.activeMenu = 'toolkit';
      this.subMenu = 'customHttpTool';
    },
    switchToComfyui() {
      this.activeMenu = 'toolkit';
      this.subMenu = 'comfyui';
    },
    switchToStickerPacks() {
      this.activeMenu = 'toolkit';
      this.subMenu = 'sticker';
    },
    switchToMainAgent() {
      this.activeMenu = 'api-group';
      this.subMenu = 'agents';
    },
    switchToTTS() {
      this.activeMenu = 'model-config';
      this.subMenu = 'tts';
    },
    switchToExtensionPage() {
      this.activeMenu = 'api-group';
      this.subMenu = 'extension';
    },
    cancelLLMTool() {
      this.showLLMForm = false
      this.resetForm()
    },
    handleTypeChange(val) {
      this.newLLMTool.base_url = this.defaultBaseURL
      this.newLLMTool.api_key = this.defaultApikey
      this.fetchModelsForType(val)
    },
    changeImgHost(val) {
      this.BotConfig.img_host = val;
      this.autoSaveSettings()
    },
    // 获取模型列表
    async fetchModelsForType(type) {
      try {
        const response = await fetch(`/llm_models`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: type,
            base_url: this.newLLMTool.base_url,
            api_key: this.newLLMTool.api_key
          })
        })
        
        const { data } = await response.json()
        this.modelOptions = data.models || []
      } catch (error) {
        console.error('Failed to fetch models:', error)
      }
    },
    // 保存工具
    saveLLMTool() {
      const tool = { ...this.newLLMTool }
      // 添加工具ID
      tool.id = uuid.v4();
      if (this.editingLLM) {
        this.llmTools[this.editingLLM] = tool
      } else {
        this.llmTools.push(tool)
      }
      this.showLLMForm = false
      this.resetForm()
      this.autoSaveSettings()
    },
    // 删除工具
    removeLLMTool(index) {
      this.llmTools.splice(index, 1)
      this.autoSaveSettings()
    },
    // 重置表单
    resetForm() {
      this.newLLMTool = {
        name: '',
        type: 'openai',
        description: '',
        base_url: '',
        api_key: '',
        model: '',
        enabled: true
      }
      this.editingLLM = null
    },
    // 类型标签转换
    toolTypeLabel(type) {
      const found = this.llmInterfaceTypes.find(t => t.value === type)
      return found ? found.label : type
    },
    // 检查更新
    async checkForUpdates() {
      if (isElectron) {
        try {
          await window.electronAPI.checkForUpdates();
        } catch (err) {
          showNotification(err.message, 'error');
        }
      }
    },

    // 下载更新
    async downloadUpdate() {
      if (isElectron && this.updateAvailable) {
        try {
          await window.electronAPI.downloadUpdate();
        } catch (err) {
          showNotification(err.message, 'error');
        }
      }
    },

    // 安装更新
    async installUpdate() {
      if (isElectron && this.updateDownloaded) {
        await window.electronAPI.quitAndInstall();
      }
    },

    // 处理更新按钮点击
    async handleUpdate() {
      if (!this.updateSuccess) {
        try {
          await this.downloadUpdate();
          this.updateSuccess = true;
          setTimeout(() => {
            this.installUpdate();
          }, 1000);
        } catch (err) {
          showNotification(err.message, 'error');
        }
      } else {
        await this.installUpdate();
      }
    },

    generateConversationTitle(messages) {
      const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
      
      if (lastUserMessage) {
        let textContent;
        
        // 判断 content 是否为字符串还是对象数组
        if (typeof lastUserMessage.content === 'string') {
          textContent = lastUserMessage.content;
        } else if (Array.isArray(lastUserMessage.content)) {
          // 提取所有文本类型的内容并拼接
          textContent = lastUserMessage.content.filter(item => item.type === 'text')
                           .map(item => item.text).join(' ');
        } else {
          // 如果既不是字符串也不是对象数组，设置为空字符串或其他默认值
          textContent = '';
        }
    
        // 拼接 fileLinks_content 部分，如果有
        const fullContent = textContent + (lastUserMessage.fileLinks_content ?? '');
        
        return fullContent.substring(0, 30) + (fullContent.length > 30 ? '...' : '');
      }
      
      return this.t('newChat');
    },
    async confirmDeleteConversation(convId) {
      if (convId === this.conversationId) {
        this.messages = [{ id: Date.now() + Math.random(), role: 'system', content: this.system_prompt }];
      }
      
      this.conversations = this.conversations.filter(c => c.id !== convId);
      await this.saveConversations(); // 保存对话列表
    },
    async loadConversation(convId) {
      const conversation = this.conversations.find(c => c.id === convId);
      if (conversation) {
        this.conversationId = convId;
        this.messages = [...conversation.messages];
        this.fileLinks = conversation.fileLinks;
        this.mainAgent = conversation.mainAgent;
        this.showHistoryDialog = false;
        this.system_prompt = conversation.system_prompt;
      }
      else {
        this.system_prompt = " ";
        this.messages = [{ id: Date.now() + Math.random(), role: 'system', content: this.system_prompt }];
      }
      if(this.allBriefly){
        this.messages.forEach((m) => {
          m.briefly = true;
        })
      }else{
        this.messages.forEach((m) => {
          m.briefly = false;
        })
      }
      this.inAutoMode = false; // 重置自动模式状态
      this.scrollToBottom();
      this.sendMessagesToExtension(); // 发送消息到插件
      this.autoSaveSettings();
    },
    switchToagents() {
      this.activeMenu = 'api-group';
      this.subMenu = 'agents';
    },
    switchToa2aServers() {
      this.activeMenu = 'toolkit';
      this.subMenu = 'a2a';
    },
    switchToSystemPrompts() {
      this.activeMenu = 'role';
      this.subMenu = 'memory';
      this.activeMemoryTab = 'prompts';
    },
    async syncProviderConfig(targetConfig) {
      // 当有选中供应商时执行同步
      if (targetConfig.selectedProvider) {
        // 在供应商列表中查找匹配项
        const provider = this.modelProviders.find(
          p => p.id === targetConfig.selectedProvider && !p.disabled
        );
        if (provider) {
          // 同步核心配置
          const shouldUpdate = 
            targetConfig.model !== provider.modelId ||
            targetConfig.base_url !== provider.url ||
            targetConfig.api_key !== provider.apiKey;
          if (shouldUpdate) {
            targetConfig.model = provider.modelId || '';
            targetConfig.base_url = provider.url || '';
            targetConfig.api_key = provider.apiKey || '';
            console.log(`已同步 ${provider.vendor} 配置`);
          }
        } else {
          // 清理无效的供应商选择
          console.warn('找不到匹配的供应商，已重置配置');
          targetConfig.selectedProvider = null;
          targetConfig.model = '';
          targetConfig.base_url = '';
          targetConfig.api_key = '';
        }
        await this.autoSaveSettings();
      }
    },
    updateMCPExample() {
      this.currentMCPExample = this.mcpExamples[this.newMCPType];
    },
    
    toggleMCPServer(name, status) {
      this.mcpServers[name].disabled = !status
      this.autoSaveSettings()
    },
    switchTomcpServers() {
      this.activeMenu = 'toolkit';
      this.subMenu = 'mcp'
    },
    // 窗口控制
    minimizeWindow() {
      if (isElectron) window.electronAPI.windowAction('minimize');
    },
    maximizeWindow() {
      if (isElectron) window.electronAPI.windowAction('maximize');
    },
    closeWindow() {
      if (isElectron) window.electronAPI.windowAction('close');
    },
    async handleSelect(key) {
      if (key === 'model-config') {
        this.activeMenu = 'model-config';
        this.subMenu = 'service'; // 默认显示第一个子菜单
      }
      else if (key === 'role') {
        this.activeMenu = 'role';
        this.subMenu = 'memory'; // 默认显示第一个子菜单
      }
      else if (key === 'toolkit') {
        this.activeMenu = 'toolkit';
        this.subMenu = 'tools'; // 默认显示第一个子菜单
      }
      else if (key === 'api-group') {
        this.activeMenu = 'api-group';
        this.subMenu = 'openai'; // 默认显示第一个子菜单
      }
      else if (key === 'storage') {
        this.activeMenu = 'storage';
        this.subMenu = 'text'; // 默认显示第一个子菜单
        response = await fetch(`/update_storage`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json'
            }
        });
        if (response.ok) {
          console.log('Storage files updated successfully');
          data = await response.json();
          this.textFiles = data.textFiles;
          this.imageFiles = data.imageFiles;
          this.videoFiles = data.videoFiles;
          this.autoSaveSettings();
        }
        else {
          console.error('Failed to update storage files');
        }
      }
      else if (key === 'deploy-bot') {
        this.activeMenu = 'deploy-bot';
        this.subMenu = 'table_pet'; // 默认显示第一个子菜单
      }
      else {
        this.activeMenu = key;
      }
      this.activeMenu = key;
    }, 
    toggleIcon() {
      this.isExpanded = !this.isExpanded; // 点击时切换状态
      this.maximizeWindow();
    },
    //  使用占位符处理 LaTeX 公式
    formatMessage(content,index) {
      const parts = this.splitCodeAndText(content);
      let latexPlaceholderCounter = 0;
      const latexPlaceholders = [];
      let inUnclosedCodeBlock = false;
    
      let processedContent = parts.map(part => {
        if (part.type === 'code') {
          inUnclosedCodeBlock = !part.closed;
          return part.content; // 直接保留原始代码块内容
        } else if (inUnclosedCodeBlock) {
          // 处理未闭合代码块中的内容
          return part.content
            .replace(/`/g, '\\`') // 转义反引号
            .replace(/\$/g, '\\$'); // 转义美元符号
        } else {
          // 处理非代码内容
          // 处理think标签
          const thinkTagRegexWithClose = /<think>([\s\S]*?)<\/think>/g;
          const thinkTagRegexOpenOnly = /<think>[\s\S]*$/;
          
          let formatted = part.content
            .replace(thinkTagRegexWithClose, match => 
              match.replace('<think>', '<div class="highlight-block-reasoning">').replace('</think>', '</div>')
            )
            .replace(thinkTagRegexOpenOnly, match => 
              match.replace('<think>', '<div class="highlight-block-reasoning">')
            );
    
          // 处理LaTeX公式
          const latexRegex = /(\$.*?\$)|(\\\[.*?\\\])|(\\$.*?$)/g;
          return formatted.replace(latexRegex, (match) => {
            const placeholder = `LATEX_PLACEHOLDER_${latexPlaceholderCounter++}`;
            latexPlaceholders.push({ placeholder, latex: match });
            return placeholder;
          });
        }
      }).join('');
      // 删除包含非ASCII码的HTML标签
      processedContent = removeNonAsciiTags(processedContent)
      // 渲染Markdown
      let rendered = md.render(processedContent);
    
      // 恢复LaTeX占位符
      latexPlaceholders.forEach(({ placeholder, latex }) => {
        rendered = rendered.replace(placeholder, latex);
      });
    
      // 处理未闭合代码块的转义字符
      rendered = rendered.replace(/\\\`/g, '`').replace(/\\\$/g, '$');

      this.$nextTick(() => {
        MathJax.typesetPromise()
          .then(() => {
            this.initCopyButtons();
            this.initPreviewButtons();
          })
          .catch(console.error);
      });


      if (index == this.messages.length - 1 && this.messages[index].role === 'assistant' && this.messages[index]?.briefly && this.messages[index]?.content != this.messages[index]?.pure_content&&this.isTyping) {
        rendered = `<i class="fa-solid fa-lightbulb">${this.t('thinking')}</i><br>` + rendered
      }

      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = rendered;
      // 处理链接标签
      const links = tempDiv.getElementsByTagName('a');
      for (const link of links) {
        // 【新增】检测是否为脚注相关的链接
        // 1. footnote-ref: 正文中的上标数字 (通常包裹在 sup 中，或自身带有该类)
        // 2. footnote-backref: 底部列表跳回正文的箭头
        const isFootnoteRef = link.parentElement && link.parentElement.classList.contains('footnote-ref');
        const isFootnoteBack = link.classList.contains('footnote-backref');

        if (isFootnoteRef || isFootnoteBack) {
          // 如果是脚注，不做任何文件路径处理，也不强制新窗口打开
          // 它们只需要能在当前页面锚点跳转即可
          continue; 
        }

        // --- 下面是原本的普通链接处理逻辑 ---
        const originalHref = link.getAttribute('href');
        if (originalHref) {
          link.setAttribute('href', this.formatFileUrl(originalHref));
        }
        link.setAttribute('target', '_blank');
      }
      
      return tempDiv.innerHTML;
    },
    copyLink(uniqueFilename) {
      const url = `${this.partyURL}/uploaded_files/${uniqueFilename}`
      navigator.clipboard.writeText(url)
        .then(() => {
          showNotification(this.t('copy_success'))
        })
        .catch(() => {
          showNotification(this.t('copy_failed'), 'error')
        })
    },
    copyApiKey(apiKey){
      navigator.clipboard.writeText(apiKey)
        .then(() => {
          showNotification(this.t('copy_success'))
        })
        .catch(() => {
          showNotification(this.t('copy_failed'), 'error')
        })
    },
    copyProvider(provider,index){
      // 在this.modelProviders的index之后插入一个复制版本
      this.modelProviders.splice(index + 1, 0, { ...provider, id: Date.now() });
      this.autoSaveSettings();
    },
    previewImage(img) {
      this.previewImageUrl = `${this.partyURL}/uploaded_files/${img.unique_filename}`
      this.previewVisible = true
      console.log(this.previewImageUrl)
    },
    copyMessageContent(message) {
      // 获取原始内容（用户消息直接复制，AI消息复制原始markdown）
      let content = message.role === 'user' 
        ? message.content 
        : message.rawContent || message.content;
      // 处理文件链接
      if (message.fileLinks?.length) {
        content += '\n\n' + message.fileLinks.map(link => `[${link.name}](${link.path})`).join('\n');
      }
      navigator.clipboard.writeText(content)
        .then(() => showNotification(this.t('copy_success')))
        .catch(() => showNotification(this.t('copy_failed'), 'error'));
    },
    initPreviewButtons() {
      // 清理旧事件监听器
      if (this._previewEventHandler) {
        document.body.removeEventListener('click', this._previewEventHandler);
      }
      // 主事件处理器
      this._previewEventHandler = (e) => {
        const button = e.target.closest('.preview-button');
        if (!button) return;
        e.preventDefault();
        e.stopPropagation();
        console.debug('🏁 预览按钮触发:', button);
        // 获取代码上下文
        const codeBlock = button.closest('.code-block');
        if (!codeBlock) {
          console.error('❌ 未找到代码块容器');
          return;
        }
        // 获取代码内容
        const lang = button.dataset.lang;
        const codeContent = codeBlock.querySelector('code')?.textContent?.trim();
        if (!codeContent) {
          console.warn('⚠️ 空代码内容', codeBlock);
          this.showErrorToast('代码内容为空');
          return;
        }
        // codeBlock中查找/创建预览容器
        let previewContainer = codeBlock.querySelector('.preview-container');
        const isNewContainer = !previewContainer;
        
        if (isNewContainer) {
          previewContainer = document.createElement('div');
          previewContainer.className = 'preview-container loading';
          codeBlock.appendChild(previewContainer);
        }
        // 状态切换逻辑
        if (previewContainer.classList.contains('active')) {
          this.collapsePreview(previewContainer, button);
        } else {
          this.expandPreview({ previewContainer, button, lang, codeContent });
        }
      };
      // 绑定事件监听
      document.body.addEventListener('click', this._previewEventHandler);
      //console.log('🔧 预览按钮事件监听已初始化');
    },
    // 展开预览面板
    expandPreview({ previewContainer, button, lang, codeContent }) {
      console.log('🔼 展开预览:', { lang, length: codeContent.length });
      
      const codeBlock = button.closest('.code-block');
  
      // 检查是否已有预览
      const existingPreview = codeBlock.querySelector('.preview-container.active');
      if (existingPreview) {
        this.collapsePreview(existingPreview, button);
        return;
      }
      // 标记代码块状态
      codeBlock.dataset.previewActive = "true";
      
      // 隐藏代码内容
      const codeContentDiv = codeBlock.querySelector('.code-content');
      codeContentDiv.style.display = 'none';
      
      // 更新按钮状态
      button.innerHTML = '<i class="fa-solid fa-eye-slash"></i>';
      
      previewContainer.classList.add('active', 'loading');
      if (lang === 'mermaid'){
        previewContainer.style.width =  '85vw';
      }
      
      // 渲染内容
      requestAnimationFrame(() => {
        try {
          if (lang === 'html') {
            this.renderHtmlPreview(previewContainer, codeContent);
            // 动态调整iframe高度
            const iframe = previewContainer.querySelector('iframe');
            iframe.onload = () => {
              iframe.style.height = iframe.contentWindow.document.body.scrollHeight + 'px';
            };
          } else if (lang === 'mermaid') {
            this.renderMermaidPreview(previewContainer, codeContent).then(() => {
              // Mermaid渲染完成后调整高度
              const svg = previewContainer.querySelector('svg');
              if (svg) {
                previewContainer.style.minHeight = svg.getBBox().height + 'px';
              }
            });
          }
          previewContainer.classList.remove('loading');
        } catch (err) {
          console.error('🚨 预览渲染失败:', err);
          this.showPreviewError(previewContainer, err);
        }
      });
    },
    // 修改 collapsePreview 方法
    collapsePreview(previewContainer, button) {
      console.log('🔽 收起预览');
      
      const codeBlock = previewContainer.parentElement;
  
      // 重置代码块状态
      delete codeBlock.dataset.previewActive;
      
      // 显示代码内容
      const codeContentDiv = codeBlock.querySelector('.code-content');
      codeContentDiv.style.display = 'block';
      
      // 移除预览容器
      previewContainer.remove();
      
      // 重置按钮状态
      button.innerHTML = '<i class="fa-solid fa-eye"></i>';
    },
    // HTML渲染器
    renderHtmlPreview(container, code) {
      console.log('🌐 渲染HTML预览');
      
      const sandbox = document.createElement('iframe');
      sandbox.srcdoc = `<!DOCTYPE html>
        <html>
          <head>
            <base href="/">
          </head>
          <body>${code}</body>
        </html>`;
      
      sandbox.style.cssText = `
        width: 70vw;
        height: 70vh;
        border: none;
        border-radius: 8px;
        background: transparent;
      `;
      
      container.replaceChildren(sandbox);
    },
    // Mermaid渲染器（带重试机制）
    async renderMermaidPreview(container, code) {
      console.log('📊 渲染Mermaid图表');
      
      const diagramContainer = document.createElement('div');
      diagramContainer.className = 'mermaid-diagram';
      container.replaceChildren(diagramContainer);
      // 异步渲染逻辑
      let retryCount = 0;
      const maxRetries = 3;
      
      const attemptRender = async () => {
        try {
          diagramContainer.textContent = code;
          await mermaid.run({
            nodes: [diagramContainer],
            suppressErrors: false
          });
          console.log('✅ Mermaid渲染成功');
        } catch (err) {
          if (retryCount < maxRetries) {
            retryCount++;
            console.warn(`🔄 重试渲染 (${retryCount}/${maxRetries})`);
            diagramContainer.innerHTML = '';
            await new Promise(resolve => setTimeout(resolve, 500 * retryCount));
            await attemptRender();
          } else {
            throw new Error(`Mermaid渲染失败: ${err.message}`);
          }
        }
      };
      await attemptRender();
    },
    // 错误处理
    showPreviewError(container, error) {
      container.classList.add('error');
      container.innerHTML = `
        <div class="error-alert">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <div>
            <h4>预览渲染失败</h4>
            <code>${error.message}</code>
          </div>
        </div>
      `;
    },
    // 新增方法：检测未闭合代码块
    hasUnclosedCodeBlock(parts) {
      return parts.some(p => p.type === 'code' && !p.closed);
    },

    splitCodeAndText(content) {
      const codeFenceRegex = /(```[\s\S]*?)(?:```|$)/g; // 修改正则表达式
      const parts = [];
      let lastIndex = 0;
      let hasUnclosed = false;

      // 处理代码块
      let match;
      while ((match = codeFenceRegex.exec(content)) !== null) {
        const textBefore = content.slice(lastIndex, match.index);
        if (textBefore) parts.push({ type: 'text', content: textBefore });

        // 判断是否闭合
        const isClosed = match[0].endsWith('```');
        const codeContent = isClosed ? 
          match[0] : 
          match[0] + '\n```'; // 自动补全闭合

        parts.push({
          type: 'code',
          content: codeContent,
          closed: isClosed
        });

        lastIndex = codeFenceRegex.lastIndex;
        hasUnclosed = !isClosed;
      }

      // 处理剩余内容
      const remaining = content.slice(lastIndex);
      if (remaining) {
        if (hasUnclosed) {
          // 将剩余内容视为代码块
          parts.push({
            type: 'code',
            content: remaining + '\n```',
            closed: false
          });
        } else {
          parts.push({ type: 'text', content: remaining });
        }
      }

      return parts;
    },
    initDownloadButtons() {
        document.body.addEventListener('click', async (e) => {
            const button = e.target.closest('.download-button');
            if (!button) return;
            const lang = button.dataset.lang;
            const codeBlock = button.closest('.code-block');
            const previewButton = codeBlock.querySelector('.preview-button');
            const existingPreview = codeBlock.querySelector('.preview-container.active');
            // 如果previewButton不在预览状态，则执行预览操作
            if (!existingPreview) {
                // 触发预览按钮的点击事件
                previewButton.click();
                // 等待预览完成
                await new Promise(resolve => setTimeout(resolve, 500)); // 根据实际情况调整延时
            }
            const previewContainer = codeBlock.querySelector('.preview-container');
            try {
                if (lang === 'mermaid') {
                    // 使用html2canvas来截图
                    html2canvas(previewContainer, {
                        // 如果Mermaid图表面板有滚动条，你可能需要设置宽度和高度
                        width: previewContainer.offsetWidth,
                        height: previewContainer.offsetHeight,
                    }).then(canvas => {
                        canvas.toBlob(blob => {
                            this.triggerDownload(blob, 'mermaid-diagram.png');
                        });
                    }).catch(error => {
                        console.error('截图失败:', error);
                        showNotification('截图失败，请检查控制台', 'error');
                    });
                }
                else if (lang === 'html') {
                    const iframe = previewContainer.querySelector('iframe');
                    const canvas = await html2canvas(iframe.contentDocument.body);
                    canvas.toBlob(blob => {
                        this.triggerDownload(blob, 'html-preview.png');
                    });
                }
            } catch (error) {
                console.error('下载失败:', error);
                showNotification('下载失败，请检查控制台', 'error');
            }
        });
    },

    triggerDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },
    
    handleCopy(event) {
      const button = event.target.closest('.copy-button')
      if (button) {
        const codeBlock = button.closest('.code-block')
        const codeContent = codeBlock?.querySelector('code')?.textContent || ''
        
        navigator.clipboard.writeText(codeContent).then(() => {
          showNotification(this.t('copy_success'))
        }).catch(() => {
          showNotification(this.t('copy_failed'), 'error')
        })
        
        event.stopPropagation()
        event.preventDefault()
      }
    },
    
    initCopyButtons() {
      // 移除旧的ClipboardJS初始化代码
      document.querySelectorAll('.copy-button').forEach(btn => {
        btn.removeEventListener('click', this.handleCopy)
        btn.addEventListener('click', this.handleCopy)
      })
    },  
    // 滚动到最新消息
    /* 判断元素是否接近底部 */
    isElemNearBottom(el, threshold = 300) {
      if (!el) return true;               // 元素不存在就默认“需要滚底”
      return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
    },

    /* 聊天区原逻辑，不变 */
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (this.isElemNearBottom(container)) {
          container.scrollTop = container.scrollHeight;
        }
      });
      this.scrollPanelToBottom();
    },

    /* 侧边栏滚动：完全一样的思路 */
    scrollPanelToBottom() {
      this.$nextTick(() => {
        const panel = this.$refs.messagesPanel;
        if (this.isElemNearBottom(panel)) {
          panel.scrollTop = panel.scrollHeight;
        }
      });
    },
    changeMainAgent(agent) {
      this.mainAgent = agent;
      if (agent === 'super-model') {
        this.system_prompt = " "
      }
      else {
        this.system_prompt = this.agents[agent].system_prompt;
        console.log(this.system_prompt);
      }
      this.syncSystemPromptToMessages(this.system_prompt);
    },
    async changeQQAgent(agent) {
      this.qqBotConfig.QQAgent = agent;
      await this.autoSaveSettings();
    },
    // WebSocket相关
    initWebSocket() {
      const http_protocol = window.location.protocol;
      const ws_protocol = http_protocol === 'https:' ? 'wss:' : 'ws:';
      const ws_url = `${ws_protocol}//${window.location.host}/ws`;

      this.ws = new WebSocket(ws_url);

      // 设置心跳间隔和重连间隔（单位：毫秒）
      const HEARTBEAT_INTERVAL = 10000; // 每10秒发送一次 ping
      const RECONNECT_INTERVAL = 5000;  // 断开后每5秒尝试重连一次

      let heartbeatTimer = null;
      let reconnectTimer = null;

      const startHeartbeat = () => {
        heartbeatTimer = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
              this.ws.send(JSON.stringify({ type: 'ping' })); // 发送心跳包
            } catch (e) {
              console.error('Failed to send ping:', e);
            }
          }
        }, HEARTBEAT_INTERVAL);
      };

      const stopHeartbeat = () => {
        if (heartbeatTimer) {
          clearInterval(heartbeatTimer);
          heartbeatTimer = null;
        }
      };

      const scheduleReconnect = () => {
        stopHeartbeat();
        if (!reconnectTimer) {
          reconnectTimer = setTimeout(() => {
            console.log('Reconnecting WebSocket...');
            this.initWebSocket(); // 重新初始化
            reconnectTimer = null;
          }, RECONNECT_INTERVAL);
        }
      };

      // WebSocket 打开事件
      this.ws.onopen = () => {
        console.log('WebSocket connection established');
        stopHeartbeat(); // 防止重复心跳
        startHeartbeat();
      };

      // 接收消息
      this.ws.onmessage = async (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch (e) {
          console.log('Message from server:', event.data);
          return;
        }

      if (data.type === 'pong') {
        // 可以在这里处理 pong 回复，比如记录状态
        console.log('Received pong from server.');
      } 
      else if (data.type === 'behavior') {
          this.behaviorSettings = data.data.behaviorSettings || this.behaviorSettings;
          this.autoSaveSettings();
      }
      else if (data.type === 'settings') {
          this.isdocker = data.data.isdocker || false;
          this.settings = {
            model: data.data.model || '',
            base_url: data.data.base_url || '',
            api_key: data.data.api_key || '',
            temperature: data.data.temperature || 0.7,
            max_tokens: data.data.max_tokens || 4096,
            max_rounds: data.data.max_rounds || 0,
            selectedProvider: data.data.selectedProvider || '',
            top_p: data.data.top_p || 1,
            extra_params: data.data.extra_params || [],
          };
          this.isBtnCollapse = data.data.isBtnCollapse || false;
          this.system_prompt = data.data.system_prompt || '';
          this.SystemPromptsList = data.data.SystemPromptsList || [];
          this.conversations = data.data.conversations || this.conversations;
          this.conversationId = data.data.conversationId || this.conversationId;
          this.agents = data.data.agents || this.agents;
          this.mainAgent = data.data.mainAgent || this.mainAgent;
          this.qqBotConfig = data.data.qqBotConfig || this.qqBotConfig;
          this.feishuBotConfig = data.data.feishuBotConfig || this.feishuBotConfig;
          this.discordBotConfig = data.data.discordBotConfig || this.discordBotConfig;
          this.telegramBotConfig = data.data.telegramBotConfig || this.telegramBotConfig;
          this.targetLangSelected = data.data.targetLangSelected || this.targetLangSelected;
          this.allBriefly = data.data.allBriefly || this.allBriefly;
          this.BotConfig = data.data.BotConfig || this.BotConfig;
          this.liveConfig = data.data.liveConfig || this.liveConfig;
          this.WXBotConfig = data.data.WXBotConfig || this.WXBotConfig;
          this.stickerPacks = data.data.stickerPacks || this.stickerPacks;
          this.toolsSettings = data.data.tools || this.toolsSettings;
          this.llmTools = data.data.llmTools || this.llmTools;
          this.reasonerSettings = data.data.reasoner || this.reasonerSettings;
          this.visionSettings = data.data.vision || this.visionSettings;
          this.webSearchSettings = data.data.webSearch || this.webSearchSettings;
          this.codeSettings = data.data.codeSettings || this.codeSettings;
          this.CLISettings = data.data.CLISettings || this.CLISettings;
          this.ccSettings = data.data.ccSettings || this.ccSettings;
          this.qcSettings = data.data.qcSettings || this.qcSettings;
          this.HASettings = data.data.HASettings || this.HASettings;
          this.chromeMCPSettings = data.data.chromeMCPSettings || this.chromeMCPSettings;
          this.sqlSettings = data.data.sqlSettings || this.sqlSettings;
          this.KBSettings = data.data.KBSettings || this.KBSettings;
          this.textFiles = data.data.textFiles || this.textFiles;
          this.imageFiles = data.data.imageFiles || this.imageFiles;
          this.videoFiles = data.data.videoFiles || this.videoFiles;
          this.knowledgeBases = data.data.knowledgeBases || this.knowledgeBases;
          this.modelProviders = data.data.modelProviders || this.modelProviders;
          this.systemSettings = data.data.systemSettings || this.systemSettings;
          if (data.data.largeMoreButtonDict) {
            this.largeMoreButtonDict = this.largeMoreButtonDict.map(existingButton => {
              const newButton = data.data.largeMoreButtonDict.find(button => button.name === existingButton.name);
              if (newButton) {
                return { ...existingButton, enabled: newButton.enabled };
              }
              return existingButton;
            });
          }
          if (data.data.smallMoreButtonDict) {
            this.smallMoreButtonDict = this.smallMoreButtonDict.map(existingButton => {
              const newButton = data.data.smallMoreButtonDict.find(button => button.name === existingButton.name);
              if (newButton) {
                return { ...existingButton, enabled: newButton.enabled };
              }
              return existingButton;
            });
          }
          this.currentLanguage = data.data.currentLanguage || this.currentLanguage;
          this.mcpServers = data.data.mcpServers || this.mcpServers;
          this.a2aServers = data.data.a2aServers || this.a2aServers;
          this.memories = data.data.memories || this.memories;
          this.memorySettings = data.data.memorySettings || this.memorySettings;
          this.text2imgSettings = data.data.text2imgSettings || this.text2imgSettings;
          this.asrSettings = data.data.asrSettings || this.asrSettings;
          this.ttsSettings = data.data.ttsSettings || this.ttsSettings;
          this.behaviorSettings = data.data.behaviorSettings || this.behaviorSettings;
          this.VRMConfig = data.data.VRMConfig || this.VRMConfig;
          this.comfyuiServers = data.data.comfyuiServers || this.comfyuiServers;
          this.comfyuiAPIkey = data.data.comfyuiAPIkey || this.comfyuiAPIkey;
          this.workflows = data.data.workflows || this.workflows;
          this.customHttpTools = data.data.custom_http || this.customHttpTools;
          this.loadConversation(this.conversationId);
          // 初始化时确保数据一致性
          this.edgettsLanguage = this.ttsSettings.edgettsLanguage;
          this.edgettsGender = this.ttsSettings.edgettsGender;
          this.handleSystemLanguageChange(this.systemSettings.language);
          this.refreshButtonText = this.t('refreshList');
          if (this.HASettings.enabled) {
            this.changeHAEnabled();
          };
          if (this.chromeMCPSettings.enabled){
            this.changeChromeMCPEnabled();
          }
          if (this.sqlSettings.enabled){
            this.changeSqlEnabled();
          }
          this.changeMemory();
          // this.target_lang改成navigator.language || navigator.userLanguage;
          this.target_lang = this.targetLangSelected!="system"? this.targetLangSelected: navigator.language || navigator.userLanguage || 'zh-CN';
          this.loadDefaultModels();
          this.loadDefaultMotions();
          this.loadGaussScenes();
          this.checkMobile();
          this.checkQQBotStatus(); 
          this.checkFeishuBotStatus();
          this.checkTelegramBotStatus();
          this.checkDiscordBotStatus();
          this.checkLiveStatus();
          this.fetchRemotePlugins();
          if (this.asrSettings.enabled) {
            this.startASR();
          }
          if (this.activeMenu === 'home') this.startDriverGuide();
        } 
        else if (data.type === 'settings_saved') {
          if (!data.success) {
            showNotification(this.t('settings_save_failed'), 'error');
          }
        }
        // 新增：处理用户输入更新
        else if (data.type === 'update_user_input') {
          this.userInput = data.data.text;
        }
        // 更新或添加提示词
        else if (data.type === 'update_system_prompt') {
            const id = data.data.id;
            const text = data.data.text;
            this.extensionsSystemPromptsDict[id] = text; 
        }
        
        // 移除提示词 (对应后端 finally 中的逻辑)
        else if (data.type === 'remove_system_prompt') {
            const id = data.data.id;
            
            if (this.extensionsSystemPromptsDict[id]) {
                delete this.extensionsSystemPromptsDict[id];
            }
        }
        // 新增：处理工具输入
        else if (data.type === 'update_user_input') {
          this.userInput = data.data.text;
          this.sendMessage(role = 'system')
        }
        // 新增：处理关闭扩展侧边栏
        else if (data.type === 'trigger_close_extension') {
          console.log('关闭侧边栏')
          this.resetToDefaultView();
        }
        // 新增：处理触发发送消息
        else if (data.type === 'trigger_send_message') {
          this.sendMessage();
        }
        // 新增：清空消息列表
        else if (data.type === "trigger_clear_message" ){
          this.clearMessages();
        }
        // 新增：响应请求消息列表
        else if (data.type === 'request_messages') {
          // 发送当前消息列表给请求方
          this.sendMessagesToExtension();
        }
      };

      // WebSocket 关闭事件
      this.ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event.reason);
        stopHeartbeat();
        scheduleReconnect();
      };

      // WebSocket 错误事件
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.ws.close(); // 主动关闭连接，触发 onclose 事件
      };
    },

    async handleKeyDown(event) {
      if (event?.repeat) return;

      if (event.code === 'Space' && event.shiftKey) {
        event.preventDefault();   // 防止页面滚动
        if (
          this.readState.ttsChunks.length > 0 &&
          !this.readState.isPlaying
        ) {
          this.playNextSegmentOnce();
        }
        return;
      }
      if (event?.key === 'Enter' && this.activeMenu === 'home') {
        if (event?.shiftKey) {
          // 如果同时按下了Shift键，则不阻止默认行为，允许换行
          return;
        } else {
          // 阻止默认行为，防止表单提交或新行插入
          event.preventDefault();
          await this.sendMessage();
        }
      }
      if (event?.key === this.asrSettings.hotkey && this.asrSettings.interactionMethod == "keyTriggered") {
        event.preventDefault();
        this.asrSettings.enabled = false;
        await this.toggleASR();
      }
    },
    async handleKeyUp(event) {
      if (event?.repeat) return;
      if (event?.key === this.asrSettings.hotkey && this.asrSettings.interactionMethod == "keyTriggered") {
        event.preventDefault();
        this.asrSettings.enabled = true;
        // 等待2秒后关闭ASR
        await new Promise(resolve => setTimeout(resolve, 2000));
        await this.toggleASR();
        await this.sendMessage();
      }  
    },
    escapeHtml(unsafe) {
      return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    },  
    // 新增：发送当前消息列表到所有连接的客户端
    sendMessagesToExtension() {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({
            type: 'broadcast_messages',
            data: {
              messages: this.messages,
              conversationId: this.conversationId
            }
          }));
        } catch (e) {
          console.error('Failed to send messages to extension:', e);
        }
      }
    },
    async syncSystemPromptToMessages(newPrompt) {
      // 情况 1: 新提示词为空
      if (!newPrompt) {
        if (this.messages.length > 0 && this.messages[0].role === 'system') {
          this.messages.splice(0, 1); // 删除系统消息
        }
        return;
      }
  
      // 情况 2: 已有系统消息
      if (this.messages[0]?.role === 'system') {
        // 更新系统消息内容
        this.messages[0].content = newPrompt;
        console.log('Updated system message:', this.messages[0]);
        return;
      }
  
      // 情况 3: 没有系统消息
      this.messages.unshift({
        id: Date.now() + Math.random(), // 添加唯一ID
        role: 'system',
        content: newPrompt
      });
      console.log('Added system message:', this.messages[0]);
      await this.autoSaveSettings();
    },
    // 发送消息
    async sendMessage(role = 'user') { 
      if (!this.userInput.trim() || this.isTyping) return;
      if (this.readState.isPlaying && this.ttsSettings.enabled) { 
        if (this.isReadRunning){
          this.pauseRead();
        }else{
          this.stopSegmentTTS(isEnd=false);
        }
        this.isReadInterruption = true;
      }
      this.isTyping = true;
      // 开始计时
      this.startTimer();
      if (this.ttsSettings.enabledInterruption) {
        // 关闭正在播放的音频
        if (this.currentAudio){
          this.currentAudio.pause();
          this.currentAudio = null;
          this.stopGenerate();
        }
        this.TTSrunning = false;
      }
      // 👈 桌面截图：仅在 Electron 且 desktopVision 开启时
      if (isElectron && this.visionSettings?.desktopVision) {
        if (this.visionSettings.enableWakeWord && this.visionSettings.wakeWord) {
          // this.visionSettings.wakeWord以换行符分割成数组
          const wakeWords = this.visionSettings.wakeWord.split('\n');
          // this.userInput中不包含wakeWords中的元素，就不启用
          if (wakeWords.some(word => this.userInput.includes(word))) {
            try {
              const pngBuffer = await window.electronAPI.captureDesktop() // Buffer
              const blob = new Blob([pngBuffer], { type: 'image/png' })
              const file = new File([blob], `desktop_${Date.now()}.png`, { type: 'image/png' })
              // 直接塞进本次要上传的 images 数组，复用原有上传逻辑
              this.images.push({ file, name: file.name, path: '' })
            } catch (e) {
              console.error('桌面截图失败:', e)
              showNotification(this.t('desktop_capture_failed'), 'error')
            }
          }
        }
        else {
          try {
            const pngBuffer = await window.electronAPI.captureDesktop() // Buffer
            const blob = new Blob([pngBuffer], { type: 'image/png' })
            const file = new File([blob], `desktop_${Date.now()}.png`, { type: 'image/png' })
            // 直接塞进本次要上传的 images 数组，复用原有上传逻辑
            this.images.push({ file, name: file.name, path: '' })
          } catch (e) {
            console.error('桌面截图失败:', e)
            showNotification(this.t('desktop_capture_failed'), 'error')
          }
        }
      }
      // 声明变量并初始化为 null
      let ttsProcess = null;
      let audioProcess = null;
      const userInput = this.userInput.trim();
      let fileLinks = this.files || [];
      if (fileLinks.length > 0){
        const formData = new FormData();
        
        // 使用 'files' 作为键名，而不是 'file'
        for (const file of fileLinks) {
            if (file.file instanceof Blob) { // 确保 file.file 是一个有效的文件对象
                formData.append('files', file.file, file.name); // 添加第三个参数为文件名
            } else {
                console.error("Invalid file object:", file);
                showNotification(this.t('invalid_file'), 'error');
                return;
            }
        }
    
        try {
            console.log('Uploading files...');
            const response = await fetch(`/load_file`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server responded with an error:', errorText);
                showNotification(this.t('file_upload_failed'), 'error');
                return;
            }
            const data = await response.json();
            if (data.success) {
                fileLinks = data.fileLinks;
                // data.textFiles 添加到 this.textFiles
                this.textFiles = [...this.textFiles, ...data.textFiles];
            } else {
                showNotification(this.t('file_upload_failed'), 'error');
            }
          } catch (error) {
              console.error('Error during file upload:', error);
              showNotification(this.t('file_upload_failed'), 'error');
          }
        }
        let imageLinks = this.images || [];
        if (imageLinks.length > 0){
          const formData = new FormData();
          
          // 使用 'files' 作为键名，而不是 'file'
          for (const file of imageLinks) {
              if (file.file instanceof Blob) { // 确保 file.file 是一个有效的文件对象
                  formData.append('files', file.file, file.name); // 添加第三个参数为文件名
              } else {
                  console.error("Invalid file object:", file);
                  showNotification(this.t('invalid_file'), 'error');
                  return;
              }
          }
      
          try {
              console.log('Uploading images...');
              const response = await fetch(`/load_file`, {
                  method: 'POST',
                  body: formData
              });
              if (!response.ok) {
                  const errorText = await response.text();
                  console.error('Server responded with an error:', errorText);
                  showNotification(this.t('file_upload_failed'), 'error');
                  return;
              }
              const data = await response.json();
              if (data.success) {
                imageLinks = data.fileLinks;
                // data.imageFiles 添加到 this.imageFiles
                this.imageFiles = [...this.imageFiles, ...data.imageFiles];
              } else {
                showNotification(this.t('file_upload_failed'), 'error');
              }
          } catch (error) {
              console.error('Error during file upload:', error);
              showNotification(this.t('file_upload_failed'), 'error');
          }
        }
      const fileLinks_content = fileLinks.map(fileLink => `\n[文件名：${fileLink.name}\n文件链接: ${fileLink.path}]`).join('\n') || '';
      const fileLinks_list = Array.isArray(fileLinks) ? fileLinks.map(fileLink => fileLink.path).flat() : []
      // fileLinks_list添加到self.filelinks
      this.fileLinks = this.fileLinks.concat(fileLinks_list)
      // const escapedContent = this.escapeHtml(userInput.trim());
      // 添加用户消息
      this.messages.push({
        id: Date.now() + Math.random(), // 添加唯一ID
        role: role,
        content: userInput.trim(),
        fileLinks: fileLinks,
        fileLinks_content: fileLinks_content,
        imageLinks: imageLinks || []
      });
      this.sendMessagesToExtension();
      this.files = [];
      this.images = [];
      let max_rounds = this.settings.max_rounds || 0;
      let messages;
      // 把窗口滚动到底部
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        container.scrollTop = container.scrollHeight;
      });
      if (max_rounds === 0) {
        // 如果 max_rounds 是 0, 映射所有消息
        messages = this.messages.map(msg => {
          // 提取HTTP/HTTPS图片链接
          const httpImageLinks = msg.imageLinks?.filter(imageLink => 
            imageLink.path.startsWith('http')
          ) || [];
          
          // 构建图片URL文本信息
          const imageUrlsText = httpImageLinks.length > 0 
            ? '\n\n图片链接:\n' + httpImageLinks.map(link => link.path).join('\n')
            : '';
          
          return {
            role: msg.role,
            content: (msg.imageLinks && msg.imageLinks.length > 0)
              ? [
                  {
                    type: "text",
                    text: msg.pure_content??msg.content + (msg.fileLinks_content ?? '') + imageUrlsText
                  },
                  ...msg.imageLinks.map(imageLink => ({
                    type: "image_url",
                    image_url: { url: imageLink.path }
                  }))
                ]
              : msg.pure_content??msg.content + (msg.fileLinks_content ?? '') + imageUrlsText
          };
        });
      } else {
        // 准备发送的消息历史（保留最近 max_rounds 条消息）
        messages = this.messages
          .slice(-max_rounds)
          .map(msg => {
          // 提取HTTP/HTTPS图片链接
          const httpImageLinks = msg.imageLinks?.filter(imageLink => 
            imageLink.path.startsWith('http')
          ) || [];
          
          // 构建图片URL文本信息
          const imageUrlsText = httpImageLinks.length > 0 
            ? '\n\n图片链接:\n' + httpImageLinks.map(link => link.path).join('\n')
            : '';
          
          return {
            role: msg.role,
            content: (msg.imageLinks && msg.imageLinks.length > 0)
              ? [
                  {
                    type: "text",
                    text: msg.pure_content??msg.content + (msg.fileLinks_content ?? '') + imageUrlsText
                  },
                  ...msg.imageLinks.map(imageLink => ({
                    type: "image_url",
                    image_url: { url: imageLink.path }
                  }))
                ]
              : msg.pure_content??msg.content + (msg.fileLinks_content ?? '') + imageUrlsText
          };
        });
      }
      
      this.userInput = '';
      this.isSending = true;
      this.abortController = new AbortController(); 
      // 如果conversationId为null
      if (this.conversationId === null) {
        //创建一个新的对话
        this.conversationId = uuid.v4();
        const newConv = {
          id: this.conversationId,
          title: this.generateConversationTitle(messages),
          mainAgent: this.mainAgent,
          timestamp: Date.now(),
          messages: this.messages,
          fileLinks: this.fileLinks,
          system_prompt: this.system_prompt,
        };
        this.conversations.unshift(newConv);
      }
      // 如果conversationId不为null
      else {
        // 更新现有对话
        const conv = this.conversations.find(conv => conv.id === this.conversationId);
        if (conv) {
          conv.messages = this.messages;
          conv.mainAgent = this.mainAgent;
          conv.timestamp = Date.now();
          conv.title = this.generateConversationTitle(messages);
          conv.fileLinks = this.fileLinks;
          conv.system_prompt = this.system_prompt;
        }
      }
      await this.saveConversations();
      // 插入this.extensionsSystemPromptsDict到系统消息中
      if(this.extensionsSystemPromptsDict){
        // 去重并拼接所有的提示词
        const combinedPrompt = Object.values(this.extensionsSystemPromptsDict).filter(Boolean).join('\n\n');
        console.log(combinedPrompt);
        // 如果第一个消息时system
        if (messages[0].role === 'system') {
          // 将combinedPrompt添加到第一个消息的内容中
          messages[0].content += '\n\n' + combinedPrompt;
        } else {
          // 否则，将combinedPrompt添加到消息列表的开头
          messages.unshift({ role: 'system', content: combinedPrompt });
        }
      }
      try {
        console.log('Sending message...');
        // 请求参数需要与后端接口一致
        const response = await fetch(`/v1/chat/completions`, {  // 修改端点路径
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            // 添加API密钥验证（如果配置了api_key）
            // 'Authorization': `Bearer ${YOUR_API_KEY}`  
          },
          body: JSON.stringify({
            model: this.mainAgent,
            messages: messages,
            stream: true,
            fileLinks: this.fileLinks,
            asyncToolsID: this.asyncToolsID,
            reasoning_effort: this.reasoning_effort,
          }),
          signal: this.abortController.signal
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          // throw new Error(errorData.error?.message || this.t('error_unknown'));
          showNotification(errorData.error?.message || this.t('error_unknown'), 'error');
          throw new Error(errorData.error?.message || this.t('error_unknown')); // 抛出错误以停止执行
        }

        this.messages.push({
          id: Date.now() + Math.random(), // 添加唯一ID
          role: 'assistant',
          content: '',
          pure_content: '',
          currentChunk: 0,
          ttsChunks: [],
          chunks_voice:[],
          audioChunks: [],
          isPlaying:false,
          total_tokens: 0,
          first_token_latency: 0,
          elapsedTime: 0,
          first_sentence_latency: 0,
          TTSelapsedTime: 0,
        });
        if (this.allBriefly){
          this.messages[this.messages.length - 1].briefly = true;
        }
        if (this.ttsSettings.enabled) {
          // 启动TTS和音频播放进程
          this.startTTSProcess();
          this.startAudioPlayProcess();
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let tts_buffer = '';
        let isCodeBlock = false;
        this.cur_voice = 'default';   // 全局变量
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          
          // 处理可能包含多个事件的情况
          while (buffer.includes('\n\n')) {
            const eventEndIndex = buffer.indexOf('\n\n');
            const eventData = buffer.slice(0, eventEndIndex);
            buffer = buffer.slice(eventEndIndex + 2);
            
            if (eventData.startsWith('data: ')) {
              const jsonStr = eventData.slice(6).trim();
              if (jsonStr === '[DONE]') {
                this.isTyping = false;
                break;
              }
              
              try {
                const parsed = JSON.parse(jsonStr);
                const lastMessage = this.messages[this.messages.length - 1];
                
                if (lastMessage.content == '') {
                  // 结束计时并打印时间
                  this.stopTimer();
                  console.log(`first token processed in ${this.elapsedTime}ms`);
                  lastMessage.first_token_latency = this.elapsedTime;
                }

                // --- ✨ 核心修改：处理 content 并过滤代码块 ---
                if (parsed.choices?.[0]?.delta?.content) {
                  const contentChunk = parsed.choices[0].delta.content;

                  // 1. 始终将完整内容添加到消息显示（界面上需要显示代码）
                  // 注意：这一步原本是在下面做的，但为了逻辑清晰，流式数据进来先处理 TTS 过滤
                  // (下方的 content 拼接逻辑保留，这里仅处理 tts_buffer)

                  // 2. 处理 TTS 过滤逻辑：按 ``` 切割
                  const parts = contentChunk.split('```');
                  
                  for (let i = 0; i < parts.length; i++) {
                    // 只有不在代码块内时，才累加到 TTS 缓冲
                    if (!isCodeBlock) {
                      tts_buffer += parts[i];
                    }
                    
                    // 如果 i 不是最后一个元素，说明遇到了 ``` 分隔符，切换状态
                    if (i < parts.length - 1) {
                      isCodeBlock = !isCodeBlock;
                    }
                  }

                  // 3. 处理 TTS 分割与生成
                  if (this.ttsSettings.enabled) {
                    const {
                      chunks,
                      chunks_voice,
                      remaining,
                      remaining_voice
                    } = this.splitTTSBuffer(tts_buffer);
                    
                    // 将完整的句子添加到 ttsChunks
                    if (chunks.length > 0) {
                      lastMessage.chunks_voice.push(...chunks_voice);
                      lastMessage.ttsChunks.push(...chunks);
                    }
                    
                    // 更新 tts_buffer 为剩余部分
                    tts_buffer = remaining;
                    this.cur_voice = remaining_voice;
                  }
                }
                // --- ✨ 核心修改结束 ---

                // 处理 reasoning_content 逻辑
                if (parsed.choices?.[0]?.delta?.reasoning_content) {
                  let newContent = parsed.choices[0].delta.reasoning_content;
                  // const lastMessage = this.messages[this.messages.length - 1]; // 已在上面定义
                  
                  // 初始化高亮块
                  if (!this.isThinkOpen) {
                    lastMessage.content += '<div class="highlight-block-reasoning">';
                    this.isThinkOpen = true;
                  }
                  
                  // 处理换行（保留原始换行，通过 CSS 控制显示）
                  newContent = newContent.replace(/\n/g, '<br>'); // 可选：如果需要 HTML 换行
                  
                  // 追加内容到高亮块
                  lastMessage.content += newContent;
                  
                  this.scrollToBottom();
                }

                // 处理 tool_content 逻辑
                if (parsed.choices?.[0]?.delta?.tool_content) {
                  // const lastMessage = this.messages[this.messages.length - 1];
                  if (this.isThinkOpen) {
                    lastMessage.content += '</div>\n\n';
                    this.isThinkOpen = false; // 重置状态
                  }
                  if (parsed.choices?.[0]?.delta?.tool_link && this.toolsSettings.toolMemorandum.enabled) {
                    this.fileLinks.push(parsed.choices[0].delta.tool_link);
                  }
                  lastMessage.content += parsed.choices[0].delta.tool_content + '\n\n';
                  this.scrollToBottom();
                }

                // 处理 content 逻辑 (界面显示)
                if (parsed.choices?.[0]?.delta?.content) {
                  // const lastMessage = this.messages[this.messages.length - 1];
                  if (this.isThinkOpen) {
                    lastMessage.content += '</div>\n\n';
                    this.isThinkOpen = false; // 重置状态
                  }
                  lastMessage.content += parsed.choices[0].delta.content;
                  lastMessage.pure_content += parsed.choices[0].delta.content;
                  this.scrollToBottom();
                }

                if (parsed.usage && parsed.usage?.total_tokens) {
                  // const lastMessage = this.messages[this.messages.length - 1];
                  lastMessage.total_tokens  = parsed.usage.total_tokens;
                }
                
                this.stopTimer(); // 结束计时并打印时间
                lastMessage.elapsedTime = this.elapsedTime / 1000;

                if (parsed.choices?.[0]?.delta?.async_tool_id) {
                    // 判断parsed.choices[0].delta.async_tool_id是否在this.asyncToolsID中
                    if (this.asyncToolsID.includes(parsed.choices[0].delta.async_tool_id)) {
                      // 如果在，则删除
                      this.asyncToolsID = this.asyncToolsID.filter(id => id !== parsed.choices[0].delta.async_tool_id);
                    } else {
                      // 如果不在，则添加
                      this.asyncToolsID.push(parsed.choices[0].delta.async_tool_id);
                    }
                }
                this.sendMessagesToExtension(); // 发送消息到插件
              } catch (e) {
                console.error(e);
                showNotification(e, 'error');
              }
            }
          }
        }
        const lastMessage = this.messages[this.messages.length - 1];
        // 循环结束后，处理 tts_buffer 中的剩余内容
        if (tts_buffer.trim() && this.ttsSettings.enabled) {
          // 这里不需要再次调用 splitTTSBuffer，因为 remaining 已经是清理后的文本
          lastMessage.chunks_voice.push(this.cur_voice);
          lastMessage.ttsChunks.push(tts_buffer);
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          showNotification(this.t('message.stopGenerate'), 'info');
        } else {
          showNotification(error.message, 'error');
        }
      } finally {
        if (this.allBriefly){
          this.messages[this.messages.length - 1].briefly = true;
        }
        // 如果conversationId为null
        if (this.conversationId === null) {
          //创建一个新的对话
          this.conversationId = uuid.v4();
          const newConv = {
            id: this.conversationId,
            title: this.generateConversationTitle(messages),
            mainAgent: this.mainAgent,
            timestamp: Date.now(),
            messages: this.messages,
            fileLinks: this.fileLinks,
            system_prompt: this.system_prompt,
          };
          this.conversations.unshift(newConv);
        }
        // 如果conversationId不为null
        else {
          // 更新现有对话
          const conv = this.conversations.find(conv => conv.id === this.conversationId);
          if (conv) {
            conv.messages = this.messages;
            conv.mainAgent = this.mainAgent;
            conv.timestamp = Date.now();
            conv.title = this.generateConversationTitle(messages);
            conv.fileLinks = this.fileLinks;
            conv.system_prompt = this.system_prompt;
          }
        }
        if (this.ttsSettings.enabled) {
          // 等待TTS和音频播放进程完成
          await Promise.all([ttsProcess, audioProcess]);
        }
        this.isThinkOpen = false;
        this.isSending = false;
        this.isTyping = false;
        this.abortController = null;
        await this.autoSaveSettings();
        await this.saveConversations();
      }
    },
    async translateMessage(index) {
      const msg = this.messages[index];
      const originalContent = msg.content;
      if (msg.isTranslating) return;
      if (originalContent.trim() === '') return;

      // 1. 先占坑
      this.messages[index] = {
        ...msg,
        content: this.t('translating') + '...',
        isTranslating: true,
        originalContent
      };

      try {
        const abortController = new AbortController();
        this.abortController = abortController;

        // 2. 组装 TTS 提示
        let newttsList = [];
        if (this.ttsSettings?.newtts) {
          for (const key in this.ttsSettings.newtts) {
            if (this.ttsSettings.newtts[key].enabled) newttsList.push(key);
          }
        }
        const ttsMsg = (newttsList.length === 0 || !this.ttsSettings?.enabled)
          ? '如果被翻译的文字与目标语言一致，则返回原文即可'
          : `你还需要在翻译的同时，添加对应的音色标签。如果被翻译的文字与目标语言一致，则只需要添加对应的音色标签。注意！不要使用<!--  -->这会导致部分文字不可见！你可以使用以下音色：\n${newttsList.join(', ')}\n，当你生成回答时，将不同的旁白或角色的文字用<音色名></音色名>括起来，以表示这些话是使用这个音色，以控制不同TTS转换成对应音色。对于没有对应音色的部分，可以不括。即使音色名称不为英文，还是可以照样使用<音色名>使用该音色的文本</音色名>来启用对应音色。注意！如果是你扮演的角色的名字在音色列表里，你必须用这个音色标签将你扮演的角色说话的部分括起来！只要是非人物说话的部分，都视为旁白！角色音色应该标记在人物说话的前后！例如：<Narrator>现在是下午三点，她说道：</Narrator><角色名>”天气真好哇！“</角色名><Narrator>说完她伸了个懒腰。</Narrator>\n\n`;

        // 3. 发起流式请求
        const response = await fetch('/simple_chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: this.mainAgent,
            messages: [
              {
                role: 'system',
                content: `你是一位专业翻译，请将用户提供的任何内容严格翻译为${this.target_lang}，保持原有格式（如Markdown、换行等），不要添加任何额外内容。只需返回翻译结果。${ttsMsg}`
              },
              {
                role: 'user',
                content: `请翻译以下内容到${this.target_lang}：\n\n${originalContent}`
              }
            ],
            stream: true,
            temperature: 0.1
          }),
          signal: abortController.signal
        });

        if (!response.ok) throw new Error('Translation failed');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';      // 残余半截行
        let translated = '';  // 累积结果

        // 4. 逐块读
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // 最后一行可能不完整，留到下一轮

          for (const line of lines) {
            if (!line) continue;          // 空行跳过
            try {
              const chunk = JSON.parse(line);
              const delta = chunk.choices?.[0]?.delta?.content ?? '';
              if (delta) {
                translated += delta;
                this.messages[index].content = translated; // 实时渲染
              }
            } catch (e) {
              // 忽略解析失败
            }
          }
        }

        // 5. 翻译完成
        this.messages[index].isTranslating = false;
        this.messages[index].translated = true;

      } catch (error) {
        if (error.name === 'AbortError') {
          // 用户中断，恢复原文
          this.messages[index] = { ...msg, content: originalContent, isTranslating: false };
        } else {
          this.messages[index].content = `Translation error: ${error.message}`;
          this.messages[index].isTranslating = false;
        }
      } finally {
        this.abortController = null;
      }
    },
    stopGenerate() {
      if (this.abortController) {
        this.abortController.abort();
        // 保留已生成的内容，仅标记为完成状态
        if (this.messages.length > 0) {
          const lastMessage = this.messages[this.messages.length - 1];
          if (lastMessage.role === 'assistant') {
            let end_token = '<div class="highlight-block">'+this.t('message.stopGenerate') + '</div>';
            // 可选：添加截断标记
            if (lastMessage.content && !lastMessage.content.endsWith(end_token)) {
              lastMessage.content += '\n\n'+end_token;
            }
          }
        }
      }
      this.isThinkOpen = false;
      this.isSending = false;
      this.isTyping = false;
      this.abortController = null;
    },
    async autoSaveSettings() {
      return new Promise((resolve, reject) => {
        // 同步 MoreButtonDict 的修改到对应的字典中
        if (this.isMobile) {
          this.smallMoreButtonDict = this.smallMoreButtonDict.map(existingButton => {
            const currentButton = this.MoreButtonDict.find(button => button.name === existingButton.name);
            if (currentButton) {
              return { ...existingButton, enabled: currentButton.enabled };
            }
            return existingButton;
          });
        } else {
          this.largeMoreButtonDict = this.largeMoreButtonDict.map(existingButton => {
            const currentButton = this.MoreButtonDict.find(button => button.name === existingButton.name);
            if (currentButton) {
              return { ...existingButton, enabled: currentButton.enabled };
            }
            return existingButton;
          });
        }

        // 构造 payload（保持原有逻辑）
        const payload = {
          ...this.settings,
          system_prompt: this.system_prompt,
          SystemPromptsList: this.SystemPromptsList,
          agents: this.agents,
          mainAgent: this.mainAgent,
          qqBotConfig : this.qqBotConfig,
          feishuBotConfig: this.feishuBotConfig,
          discordBotConfig: this.discordBotConfig,
          telegramBotConfig: this.telegramBotConfig,
          targetLangSelected: this.targetLangSelected,
          allBriefly: this.allBriefly,
          BotConfig: this.BotConfig,
          liveConfig: this.liveConfig,
          WXBotConfig: this.WXBotConfig,
          stickerPacks: this.stickerPacks,
          tools: this.toolsSettings,
          llmTools: this.llmTools,
          conversationId: this.conversationId,
          reasoner: this.reasonerSettings,
          isBtnCollapse: this.isBtnCollapse,
          vision: this.visionSettings,
          webSearch: this.webSearchSettings, 
          codeSettings: this.codeSettings,
          CLISettings: this.CLISettings,
          ccSettings: this.ccSettings,
          qcSettings: this.qcSettings,
          HASettings: this.HASettings,
          chromeMCPSettings: this.chromeMCPSettings,
          sqlSettings: this.sqlSettings,
          KBSettings: this.KBSettings,
          textFiles: this.textFiles,
          imageFiles: this.imageFiles,
          videoFiles: this.videoFiles,
          knowledgeBases: this.knowledgeBases,
          modelProviders: this.modelProviders,
          systemSettings: this.systemSettings,
          largeMoreButtonDict: this.largeMoreButtonDict,
          smallMoreButtonDict: this.smallMoreButtonDict,
          currentLanguage: this.currentLanguage,
          mcpServers: this.mcpServers,
          a2aServers: this.a2aServers,
          isdocker: this.isdocker,
          memories: this.memories,
          memorySettings: this.memorySettings,
          text2imgSettings: this.text2imgSettings,
          asrSettings: this.asrSettings,
          ttsSettings: this.ttsSettings,
          behaviorSettings: this.behaviorSettings,
          VRMConfig: this.VRMConfig,
          comfyuiServers: this.comfyuiServers,
          comfyuiAPIkey: this.comfyuiAPIkey,
          workflows: this.workflows,
          custom_http: this.customHttpTools,
        };
        const correlationId = uuid.v4();
        // 发送保存请求
        this.ws.send(JSON.stringify({
          type: 'save_settings',
          data: payload,
          correlationId: correlationId // 添加唯一请求 ID
        }));
        // 设置响应监听器
        const handler = (event) => {
          const response = JSON.parse(event.data);
          
          // 匹配对应请求的确认消息
          if (response.type === 'settings_saved' && 
              response.correlationId === correlationId) {
            this.ws.removeEventListener('message', handler);
            resolve();
          }
          
          // 错误处理（根据后端实现）
          if (response.type === 'save_error') {
            this.ws.removeEventListener('message', handler);
            reject(new Error('保存失败'));
          }
        };
        // 设置 10 秒超时
        const timeout = setTimeout(() => {
          this.ws.removeEventListener('message', handler);
          reject(new Error('保存超时'));
        }, 10000);
        this.ws.addEventListener('message', handler);
      });
    },
    async saveConversations() {
      return new Promise((resolve, reject) => {
        // 构造 payload（保持原有逻辑）
        const payload = {
          conversations: this.conversations
        };
        const correlationId = uuid.v4();
        // 发送保存请求
        this.ws.send(JSON.stringify({
          type: 'save_conversations',
          data: payload,
          correlationId: correlationId // 添加唯一请求 ID
        }));
        // 设置响应监听器
        const handler = (event) => {
          const response = JSON.parse(event.data);
          
          // 匹配对应请求的确认消息
          if (response.type === 'conversations_saved' && 
              response.correlationId === correlationId) {
            this.ws.removeEventListener('message', handler);
            resolve();
          }
          
          // 错误处理（根据后端实现）
          if (response.type === 'save_error') {
            this.ws.removeEventListener('message', handler);
            reject(new Error('保存失败'));
          }
        };
        // 设置 10 秒超时
        const timeout = setTimeout(() => {
          this.ws.removeEventListener('message', handler);
          reject(new Error('保存超时'));
        }, 10000);
        this.ws.addEventListener('message', handler);
      });
    },

    // 修改后的fetchModels方法
    async fetchModels() {
      this.modelsLoading = true;
      try {
        const response = await fetch(`/v1/models`);
        const result = await response.json();
        
        // 双重解构获取数据
        const { data } = result;
        
        this.models = data.map(item => ({
          id: item.id,
          created: new Date(item.created * 1000).toLocaleDateString(),
        }));
        
      } catch (error) {
        console.error('获取模型数据失败:', error);
        this.modelsError = error.message;
        this.models = []; // 确保清空数据
      } finally {
        this.modelsLoading = false;
      }
    },

    // 修改copyEndpoint方法
    copyEndpoint() {
      navigator.clipboard.writeText(`${this.partyURL}/v1`)
        .then(() => {
          showNotification(this.t('copy_success'), 'success');
        })
        .catch(() => {
          showNotification(this.t('copy_fail'), 'error');
        });
    },

    copyMCPEndpoint(){
      navigator.clipboard.writeText(`${this.partyURL}/mcp`)
        .then(() => {
          showNotification(this.t('copy_success'), 'success');
        })
        .catch(() => {
          showNotification(this.t('copy_fail'), 'error');
        });
    },
    copyVrmEndpoint(){
      navigator.clipboard.writeText(`${this.partyURL}/vrm.html`)
        .then(() => {
          showNotification(this.t('copy_success'), 'success');
        })
        .catch(() => {
          showNotification(this.t('copy_fail'), 'error');
        });
    },
    copyURL(url) {
      navigator.clipboard.writeText(url)
        .then(() => {
          showNotification(this.t('copy_success'), 'success');
        })
        .catch(() => {
          showNotification(this.t('copy_fail'), 'error');
        });
    },
    copyModel() {
      navigator.clipboard.writeText('super-model')
        .then(() => {
          showNotification(this.t('copy_success'));
        })
        .catch(() => {
          showNotification(this.t('copy_fail'), 'error');
        });
    },

    toggleSection(section) {
      this.expandedSections[section] = !this.expandedSections[section]
      this.autoSaveSettings()
    },
    
    // 新增点击头部的处理
    handleHeaderClick(section) {
      this.toggleSection(section)
    },
    async clearMessages() {
      this.stopGenerate();
      this.messages = [{ role: 'system', content: this.system_prompt }];
      this.conversationId = null;
      this.fileLinks = [];
      this.isThinkOpen = false; // 重置思考模式状态
      this.asyncToolsID = [];
      this.inAutoMode = false; // 重置自动模式状态
      this.randomGreetings(); // 重新生成随机问候语
      this.scrollToBottom();    // 触发界面更新
      this.autoSaveSettings();
      this.sendMessagesToExtension(); // 发送消息到插件
    },
    async sendFiles() {
      this.showUploadDialog = true;
      // 设置文件上传专用处理
      this.currentUploadType = 'file';
    },
    async sendImages() {
      this.showUploadDialog = true;
      // 设置图片上传专用处理
      this.currentUploadType = 'image';
    },
    browseFiles() {
      if (this.currentUploadType === 'image') {
        this.browseImages();
      } else {
        this.browseDocuments();
      }
    },
    // 专门处理图片选择
    async browseImages() {
      if (!this.isElectron) {
        const input = document.createElement('input')
        input.type = 'file'
        input.multiple = true
        input.accept = ALLOWED_IMAGE_EXTENSIONS.map(ext => `.${ext}`).join(',')
        
        input.onchange = (e) => {
          const files = Array.from(e.target.files)
          const validFiles = files.filter(this.isValidImageType)
          this.handleFiles(validFiles)
        }
        input.click()
      } else {
        const result = await window.electronAPI.openImageDialog();
        if (!result.canceled) {
          // 转换Electron文件路径为File对象
          const files = await Promise.all(
            result.filePaths
              .filter(path => {
                const ext = path.split('.').pop()?.toLowerCase() || '';
                return ALLOWED_IMAGE_EXTENSIONS.includes(ext);
              })
              .map(async path => {
                // 读取文件内容并转换为File对象
                const buffer = await window.electronAPI.readFile(path);
                const blob = new Blob([buffer]);
                return new File([blob], path.split(/[\\/]/).pop());
              })
          );
          this.handleFiles(files);
        }
      }
    },

    // 文件选择处理方法
    async browseDocuments() {
      if (!this.isElectron) {
        const input = document.createElement('input')
        input.type = 'file'
        input.multiple = true
        input.accept = ALLOWED_EXTENSIONS.map(ext => `.${ext}`).join(',')
        
        input.onchange = (e) => {
          const files = Array.from(e.target.files)
          const validFiles = files.filter(this.isValidFileType)
          this.handleFiles(validFiles)
        }
        input.click()
      } else {
        const result = await window.electronAPI.openFileDialog();
        if (!result.canceled) {
          // 转换Electron文件路径为File对象
          const files = await Promise.all(
            result.filePaths
              .filter(path => {
                const ext = path.split('.').pop()?.toLowerCase() || '';
                return ALLOWED_EXTENSIONS.includes(ext);
              })
              .map(async path => {
                // 读取文件内容并转换为File对象
                const buffer = await window.electronAPI.readFile(path);
                const blob = new Blob([buffer]);
                return new File([blob], path.split(/[\\/]/).pop());
              })
          );
          this.handleFiles(files);
        }
      }
    },
    // 文件选择处理方法
    async browseReadFiles() {
      if (!this.isElectron) {
        const input = document.createElement('input')
        input.type = 'file'
        input.multiple = true
        input.accept = ALLOWED_EXTENSIONS.map(ext => `.${ext}`).join(',')
        
        input.onchange = (e) => {
          const files = Array.from(e.target.files)
          const validFiles = files.filter(this.isValidFileType)
          this.handleReadFiles(validFiles)
        }
        input.click()
      } else {
        const result = await window.electronAPI.openFileDialog();
        if (!result.canceled) {
          // 转换Electron文件路径为File对象
          const files = await Promise.all(
            result.filePaths
              .filter(path => {
                const ext = path.split('.').pop()?.toLowerCase() || '';
                return ALLOWED_EXTENSIONS.includes(ext);
              })
              .map(async path => {
                // 读取文件内容并转换为File对象
                const buffer = await window.electronAPI.readFile(path);
                const blob = new Blob([buffer]);
                return new File([blob], path.split(/[\\/]/).pop());
              })
          );
          this.handleReadFiles(files);
        }
      }
    },

    // 文件验证方法
    isValidFileType(file) {
      if (this.currentUploadType === 'image') {
        return this.isValidImageType(file);
      }
      const ext = (file.name.split('.').pop() || '').toLowerCase()
      return ALLOWED_EXTENSIONS.includes(ext) || MIME_WHITELIST.some(mime => file.type.includes(mime))
    },
    isValidImageType(file) {
      const ext = (file.name.split('.').pop() || '').toLowerCase()
      return ALLOWED_IMAGE_EXTENSIONS.includes(ext) || IMAGE_MIME_WHITELIST.some(mime => file.type.includes(mime))
    },
    // 统一处理文件
    async handleFiles(files) {
      const allowedExtensions = this.currentUploadType === 'image' ? ALLOWED_IMAGE_EXTENSIONS : ALLOWED_EXTENSIONS;
      
      const validFiles = files.filter(file => {
        try {
          // 安全获取文件扩展名
          const filename = file.name || (file.path && file.path.split(/[\\/]/).pop()) || '';
          const ext = filename.split('.').pop()?.toLowerCase() || '';
          return allowedExtensions.includes(ext);
        } catch (e) {
          console.error('文件处理错误:', e);
          return false;
        }
      });
      if (validFiles.length > 0) {
        this.addFiles(validFiles, this.currentUploadType);
      } else {
        this.showErrorAlert(this.currentUploadType);
      }
    },
    // 统一处理文件
    async handleReadFiles(files) {
      this.showFileDialog = false;
      const allowedExtensions = this.currentUploadType === 'image' ? ALLOWED_IMAGE_EXTENSIONS : ALLOWED_EXTENSIONS;

      const validFiles = files.filter(file => {
        try {
          // 安全获取文件扩展名
          const filename = file.name || (file.path && file.path.split(/[\\/]/).pop()) || '';
          const ext = filename.split('.').pop()?.toLowerCase() || '';
          return allowedExtensions.includes(ext);
        } catch (e) {
          console.error('文件处理错误:', e);
          return false;
        }
      });

      if (validFiles.length > 0) {
        const formData = new FormData();

        for (const file of validFiles) {
          formData.append('files', file, file.name);
        }

        try {
          console.log('Uploading files...');
          const response = await fetch(`/load_file`, {
            method: 'POST',
            body: formData
          });

          if (!response.ok) {
            const errorText = await response.text();
            console.error('Server responded with an error:', errorText);
            showNotification(this.t('file_upload_failed'), 'error');
            return;
          }

          const data = await response.json();
          if (data.success) {      
            // 将新的文件信息添加到 this.textFiles
            this.textFiles = [...data.textFiles,...this.textFiles];
            this.selectedFile = data.textFiles[0].unique_filename;
            this.autoSaveSettings();
            this.parseSelectedFile();
          } else {
            showNotification(this.t('file_upload_failed'), 'error');
          }
        } catch (error) {
          console.error('Error during file upload:', error);
          showNotification(this.t('file_upload_failed'), 'error');
        }
      } else {
        this.showErrorAlert(this.currentUploadType);
      }
    },
    clearLongText() {
      this.selectedFile = null;
      this.readConfig.longTextList = [];
      this.longTextListIndex = 0;
      this.readConfig.longText = '';
    },
    removeItem(index, type) {
      if (type === 'file') {
        this.files.splice(index, 1);
      } else {
        // 如果是图片，则从图片列表中删除，考虑this.files长度
        index = index - this.files.length;
        this.images.splice(index, 1);
      }
    },
    // 错误提示
    showErrorAlert(type = 'file') {
      const fileTypes = {
        file: this.t('file_type_error'),
        image: this.t('image_type_error')
      };
      showNotification(fileTypes[type], 'error');
    },
    // 拖放处理
    handleDrop(event) {
      event.preventDefault()
      const files = Array.from(event.dataTransfer.files)
        .filter(this.isValidFileType)
      this.handleFiles(files)
    },
        // 拖放处理
    handleReadDrop(event) {
      event.preventDefault()
      const files = Array.from(event.dataTransfer.files)
        .filter(this.isValidFileType)
      this.handleReadFiles(files)
    },
    switchToApiBox() {
      // 切换到 API 钥匙箱界面
      this.activeMenu = 'model-config';
      this.subMenu = 'service';
    },

    // 添加文件到列表
    addFiles(files, type = 'file') {
      const targetArray = type === 'image' ? this.images : this.files;
  
      const newFiles = files.map(file => ({
        path: URL.createObjectURL(file),
        name: file.name,
        file: file,
      }));
      targetArray.push(...newFiles);
      this.showUploadDialog = false;
    },
    highlightCode() {
      this.$nextTick(() => {
        document.querySelectorAll('pre code').forEach(block => {
          hljs.highlightElement(block);
        });
        this.initCopyButtons();
      });
    },
    async addProvider() {
      this.modelProviders.push({
        id: Date.now(),
        vendor: this.newProviderTemp.vendor,
        url: this.newProviderTemp.url,
        apiKey: '',
        modelId: '',
        isNew: true
      });
      this.newProviderTemp = { vendor: '', url: '', apiKey: '', modelId: '' };
      await this.autoSaveSettings();
    },
    async fetchModelsForProvider(provider) {
      try {
        const response = await fetch(`/v1/providers/models`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url: provider.url,
            api_key: provider.apiKey
          })
        });
        if (!response.ok) {
          throw new Error('Failed to fetch models');
        }
        const data = await response.json();
        provider.models = data.data;
      } catch (error) {
        showNotification(this.t('fetch_models_failed'), 'error');
      }
    },
    // 找到原有的 removeProvider 方法，替换为以下代码
    async removeProvider(index) {
      // 获取被删除的供应商信息
      const removedProvider = this.modelProviders[index];
      
      // 从供应商列表中移除
      this.modelProviders.splice(index, 1);

      // 清理所有相关配置中的引用
      const providerId = removedProvider.id;
      
      // 主模型配置清理
      if (this.settings.selectedProvider === providerId) {
        this.settings.selectedProvider = null;
        this.settings.model = '';
        this.settings.base_url = '';
        this.settings.api_key = '';
      }

      // 推理模型配置清理
      if (this.reasonerSettings.selectedProvider === providerId) {
        this.reasonerSettings.selectedProvider = null;
        this.reasonerSettings.model = '';
        this.reasonerSettings.base_url = '';
        this.reasonerSettings.api_key = '';
      }

      // 触发自动保存
      await this.autoSaveSettings();
    },
    confirmAddProvider() {
      if (!this.newProviderTemp.vendor) {
        showNotification(this.t('vendor_required'), 'warning')
        return
      }
      
      const newProvider = {
        id: Date.now(),
        vendor: this.newProviderTemp.vendor,
        url: this.newProviderTemp.url,
        apiKey: this.newProviderTemp.apiKey || '',
        modelId: this.newProviderTemp.modelId || '',
        models: []
      }
      
      this.modelProviders.push(newProvider)
      this.showAddDialog = false
      this.newProviderTemp = { vendor: '', url: '', apiKey: '', modelId: '' }
      this.autoSaveSettings()
    },
    handleVendorChange(value) {
      const defaultUrls = {
        'OpenAI': 'https://api.openai.com/v1',
        'Deepseek': 'https://api.deepseek.com/v1',
        'aliyun': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'ZhipuAI': 'https://open.bigmodel.cn/api/paas/v4',
        'Volcano': 'https://ark.cn-beijing.volces.com/api/v3',
        'moonshot': 'https://api.moonshot.cn/v1',
        'minimax': 'https://api.minimaxi.com/v1',
        'Ollama': this.isdocker ? 'http://host.docker.internal:11434/v1' : 'http://127.0.0.1:11434/v1',
        'Vllm': this.isdocker ? 'http://host.docker.internal:8000/v1' :'http://127.0.0.1:8000/v1',
        'LMstudio': this.isdocker ? 'http://host.docker.internal:1234/v1' :'http://127.0.0.1:1234/v1',
        'xinference': this.isdocker ? 'http://host.docker.internal:9997/v1' :'http://127.0.0.1:9997/v1',
        'Dify': this.isdocker ? 'http://host.docker.internal/v1' :'http://127.0.0.1/v1',
        'Gemini': 'https://generativelanguage.googleapis.com/v1beta/openai',
        'Anthropic': 'https://api.anthropic.com/v1',
        'Grok': 'https://api.groq.com/openai/v1',
        'mistral': 'https://api.mistral.ai/v1',
        'lingyi': 'https://api.lingyiwanwu.com/v1',
        'baichuan': 'https://api.baichuan-ai.com/v1',
        'qianfan': 'https://qianfan.baidubce.com/v2',
        'hunyuan': 'https://api.hunyuan.cloud.tencent.com/v1',
        'siliconflow': 'https://api.siliconflow.cn/v1',
        '302.AI': 'https://api.302ai.cn/v1',
        'stepfun': 'https://api.stepfun.com/v1',
        'o3': 'https://api.o3.fan/v1',
        'aihubmix': 'https://aihubmix.com/v1',
        'ocoolai': 'https://api.ocoolai.com/v1',
        'Github': 'https://models.github.ai/inference',
        'dmxapi': 'https://www.dmxapi.cn/v1',
        'openrouter': 'https://openrouter.ai/api/v1',
        'together': 'https://api.together.xyz/v1',
        'fireworks': 'https://api.fireworks.ai/inference/v1',
        '360': 'https://api.360.cn/v1',
        'Nvidia': 'https://integrate.api.nvidia.com/v1',
        'hyperbolic': 'https://api.hyperbolic.xyz/v1',
        'jina': 'https://api.jina.ai/v1',
        'gitee': 'https://ai.gitee.com/v1',
        'ppinfra': 'https://api.ppinfra.com/v3/openai/v1',
        'perplexity': 'https://api.perplexity.ai',
        'infini': 'https://cloud.infini-ai.com/maas/v1',
        'modelscope': 'https://api-inference.modelscope.cn/v1',
        'tencent': 'https://api.lkeap.cloud.tencent.com/v1',
      }
      
      if (value !== 'custom') {
        this.newProviderTemp.url = defaultUrls[value] || ''
      }
      if (value === 'Ollama') {
        this.newProviderTemp.apiKey = 'ollama'
      }
      if (value === 'Vllm') {
        this.newProviderTemp.apiKey = 'Vllm'
      }
      if (value === 'LMstudio') {
        this.newProviderTemp.apiKey = 'LMstudio'
      }
      if (value === 'xinference') {
        this.newProviderTemp.apiKey = 'xinference'
      }
      if (value === 'Dify') {
        this.newProviderTemp.modelId = 'dify'
      }
    },
    // rerank供应商
    async selectRankProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.KBSettings.model = provider.modelId;
        this.KBSettings.base_url = provider.url;
        this.KBSettings.api_key = provider.apiKey;
        await this.autoSaveSettings();
      }
    },

    // 主模型供应商选择
    async selectMainProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      console.log(provider)
      if (provider) {
        console.log("provider")
        this.settings.model = provider.modelId;
        this.settings.base_url = provider.url;
        this.settings.api_key = provider.apiKey;
        await this.autoSaveSettings();
      }
    },

    // Claude code 供应商选择
    async selectCCProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      let vendor_list = {
        "Anthropic": "https://api.anthropic.com",
        "Deepseek": "https://api.deepseek.com/anthropic",
        "siliconflow": "https://api.siliconflow.cn",
        "ZhipuAI":"https://open.bigmodel.cn/api/anthropic",
        "moonshot":"https://api.moonshot.cn/anthropic",
        "aliyun": "https://dashscope.aliyuncs.com/apps/anthropic",
        "modelscope":"https://api-inference.modelscope.cn",
        "302.AI":"https://api.302.ai/cc"
      };

      let cc_url = vendor_list[provider.vendor] || provider.url;

      if (provider) {
        this.ccSettings.model = provider.modelId;
        this.ccSettings.base_url = cc_url;
        this.ccSettings.api_key = provider.apiKey;
        await this.autoSaveSettings();
      }
    },
    async selectQCProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.qcSettings.model = provider.modelId;
        this.qcSettings.base_url = provider.url;
        this.qcSettings.api_key = provider.apiKey;
        await this.autoSaveSettings();
      }
    },
    // 推理模型供应商选择
    async selectReasonerProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.reasonerSettings.model = provider.modelId;
        this.reasonerSettings.base_url = provider.url;
        this.reasonerSettings.api_key = provider.apiKey;
        await this.autoSaveSettings();
      }
    },
    async selectVisionProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.visionSettings.model = provider.modelId;
        this.visionSettings.base_url = provider.url;
        this.visionSettings.api_key = provider.apiKey;
        await this.autoSaveSettings();
      }
    },
    async selectText2imgProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.text2imgSettings.model = provider.modelId;
        this.text2imgSettings.base_url = provider.url;
        this.text2imgSettings.api_key = provider.apiKey;
        this.text2imgSettings.vendor = provider.vendor;
        if (this.text2imgSettings.vendor === 'siliconflow') {
          this.text2imgSettings.size = '1024x1024';
        }
        else {
          this.text2imgSettings.size = 'auto';
        }
        await this.autoSaveSettings();
      }
    },
    async selectAsrProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.asrSettings.model = provider.modelId;
        this.asrSettings.base_url = provider.url;
        this.asrSettings.api_key = provider.apiKey;
        this.asrSettings.vendor = provider.vendor;
        await this.autoSaveSettings();
      }
    },
    async selectTTSProvider(providerId) {
      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.ttsSettings.model = provider.modelId;
        this.ttsSettings.base_url = provider.url;
        this.ttsSettings.api_key = provider.apiKey;
        this.ttsSettings.vendor = provider.vendor;
        await this.autoSaveSettings();
      }
    },
    handleTTSProviderVisibleChange(visible) {
      if (!visible) {
        this.selectTTSProvider(this.ttsSettings.selectedProvider);
      }
    },
    handleAsrProviderVisibleChange(visible) {
      if (!visible) {
        this.selectAsrProvider(this.asrSettings.selectedProvider);
      }
    },
    handleText2imgProviderVisibleChange(visible) {
      if (!visible) {
        this.selectText2imgProvider(this.text2imgSettings.selectedProvider);
      }
    },

    handleRankProviderVisibleChange(visible) {
      if (!visible) {
        this.selectRankProvider(this.KBSettings.selectedProvider);
      }
    },

    // 在methods中添加
    handleMainProviderVisibleChange(visible) {
      if (!visible) {
        this.selectMainProvider(this.settings.selectedProvider);
      }
    },
    handleCCProviderVisibleChange(visible) {
      if (!visible) {
        this.selectCCProvider(this.ccSettings.selectedProvider);
      }
    },
    handleQCProviderVisibleChange(visible) {
      if (!visible) {
        this.selectQCProvider(this.qcSettings.selectedProvider);
      }
    },
    handleReasonerProviderVisibleChange(visible) {
      if (!visible) {
        this.selectReasonerProvider(this.reasonerSettings.selectedProvider);
      }
    },
    handleVisionProviderVisibleChange(visible) {
      if (!visible) {
        this.selectVisionProvider(this.visionSettings.selectedProvider);
      }
    },
    // 创建知识库
    async createKnowledgeBase() {
      try {
        // 上传文件
        let uploadedFiles = [];
        if (this.newKbFiles.length > 0) {
          if (!this.isElectron) {
            // 浏览器环境：通过 FormData 上传
            const formData = new FormData();
            for (const file of this.newKbFiles) {
              if (file.file instanceof Blob) {
                formData.append('files', file.file, file.name);
              } else {
                console.error("Invalid file object:", file);
                showNotification(this.t('invalid_file'), 'error');
                return;
              }
            }
  
            try {
              console.log('Uploading files...');
              const response = await fetch(`/load_file`, {
                method: 'POST',
                body: formData
              });
  
              if (!response.ok) {
                const errorText = await response.text();
                console.error('Server responded with an error:', errorText);
                showNotification(this.t('file_upload_failed'), 'error');
                return;
              }
  
              const data = await response.json();
              if (data.success) {
                uploadedFiles = data.fileLinks; // 获取上传后的文件链接
                // data.textFiles 添加到 this.textFiles
                this.textFiles = [...this.textFiles, ...data.textFiles];
                await this.autoSaveSettings();
              } else {
                showNotification(this.t('file_upload_failed'), 'error');
                return;
              }
            } catch (error) {
              console.error('Error during file upload:', error);
              showNotification(this.t('file_upload_failed'), 'error');
              return;
            }
          } else {
            // Electron 环境：通过 JSON 上传
            try {
              console.log('Uploading Electron files...');
              const response = await fetch(`/load_file`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  files: this.newKbFiles.map(file => ({
                    path: file.path,
                    name: file.name
                  }))
                })
              });
  
              if (!response.ok) {
                const errorText = await response.text();
                console.error('Server error:', errorText);
                showNotification(this.t('file_upload_failed'), 'error');
                return;
              }
  
              const data = await response.json();
              if (data.success) {
                uploadedFiles = data.fileLinks; // 获取上传后的文件链接
                // data.textFiles 添加到 this.textFiles
                this.textFiles = [...this.textFiles, ...data.textFiles];
                await this.autoSaveSettings();
              } else {
                showNotification(this.t('file_upload_failed'), 'error');
                return;
              }
            } catch (error) {
              console.error('上传错误:', error);
              showNotification(this.t('file_upload_failed'), 'error');
              return;
            }
          }
        }
  
        // 生成唯一的 ID
        const kbId = uuid.v4();
  
        // 构建新的知识库对象，使用上传后的文件链接
        const newKb = {
          id: kbId,
          name: this.newKb.name,
          introduction: this.newKb.introduction,
          providerId: this.newKb.providerId,
          model: this.newKb.model,
          base_url: this.newKb.base_url,
          api_key: this.newKb.api_key,
          enabled: true, // 默认启用
          chunk_size: this.newKb.chunk_size,
          chunk_overlap: this.newKb.chunk_overlap,
          chunk_k: this.newKb.chunk_k,
          weight: this.newKb.weight,
          files: uploadedFiles.map(file => ({ // 使用服务器返回的文件链接
            name: file.name,
            path: file.path,
          })),
          processingStatus: 'processing', // 设置处理状态为 processing
        };
  
        // 更新 settings 中的 knowledgeBases
        this.knowledgeBases = [...(this.knowledgeBases || []), newKb];
        //手动触发modelProviders更新，从而能够实时与后端同步
        this.modelProviders = this.modelProviders
        // 保存 settings
        await this.autoSaveSettings();
        // post kbId to 后端的create_kb端口
        try {
          // 1. 触发任务
          const startResponse = await fetch(`/create_kb`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kbId }),
          });
          
          if (!startResponse.ok) throw new Error('启动失败');
          // 2. 轮询状态
          const checkStatus = async () => {
            try {
              const statusResponse = await fetch(`/kb_status/${kbId}`);
              
              // 处理 HTTP 错误状态
              if (!statusResponse.ok) {
                console.error('状态检查失败:', statusResponse.status);
                return 'failed'; // 返回明确的失败状态
              }
              const data = await statusResponse.json();
              return data.status || 'unknown'; // 防止 undefined
            } catch (error) {
              console.error('状态检查异常:', error);
              return 'failed';
            }
          };
          // 修改轮询逻辑
          const interval = setInterval(async () => {
            try {
              const status = await checkStatus() || ''; // 确保有默认值
              
              const targetKb = this.knowledgeBases.find(k => k.id === kbId);
              if (!targetKb) {
                clearInterval(interval);
                return;
              }
              // 安全的状态判断
              if (status === 'completed') {
                clearInterval(interval);
                targetKb.processingStatus = 'completed';
                showNotification(this.t('kb_created_successfully'), 'success');
                await this.autoSaveSettings();
              } else if (typeof status === 'string' && status.startsWith('failed')) { // 安全判断
                clearInterval(interval);
                this.knowledgeBases = this.knowledgeBases.filter(k => k.id !== kbId);
                showNotification(this.t('kb_creation_failed'), 'error');
                await this.autoSaveSettings();
              }
            } catch (error) {
              console.error('轮询异常:', error);
              clearInterval(interval);
            }
          }, 2000);
        } catch (error) {
          console.error('知识库创建失败:', error);
          showNotification(this.t('kb_creation_failed'), 'error');
        }      
        this.showAddKbDialog = false;
        this.newKb = { 
          name: '', 
          introduction: '',
          providerId: null, 
          model: '', 
          base_url: '', 
          api_key: '',
          chunk_size: 1024,
          chunk_overlap: 256,
          chunk_k: 5,
          weight: 0.5,
        };
        this.newKbFiles = [];
      } catch (error) {
        console.error('知识库创建失败:', error);
        showNotification(this.t('kb_creation_failed'), 'error');
      }
    },

    // 删除知识库
    async removeKnowledgeBase(kb) {
      try {
        // 从 settings 中过滤掉要删除的 knowledgeBase
        this.knowledgeBases = this.knowledgeBases.filter(
          item => item.id !== kb.id
        );
        let kbId = kb.id
        //手动触发modelProviders更新，从而能够实时与后端同步
        this.modelProviders = this.modelProviders
        const Response = await fetch(`/remove_kb`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kbId }),
        });

        if (!Response.ok) throw new Error('删除失败');

        // 保存 settings
        await this.autoSaveSettings();

        showNotification(this.t('kb_deleted_successfully'), 'success');
      } catch (error) {
        console.error('知识库删除失败:', error);
        showNotification(this.t('kb_deletion_failed'), 'error');
      }
    },

    // 切换知识库启用状态
    async toggleKbEnabled(kb) {
      try {
        // 更新 knowledgeBase 的 enabled 状态
        const kbToUpdateIndex = this.knowledgeBases.findIndex(
          item => item.id === kb.id
        );

        if (kbToUpdateIndex !== -1) {
          this.knowledgeBases[kbToUpdateIndex].enabled = kb.enabled;
          //手动触发modelProviders更新，从而能够实时与后端同步
          this.modelProviders = this.modelProviders
          // 保存 settings
          await this.autoSaveSettings();
          showNotification(this.t('kb')+` ${kb.name} ${kb.enabled ? this.t('enabled')  : this.t('disabled')}`, 'success');
        }
      } catch (error) {
        console.error('切换知识库状态失败:', error);
        showNotification(this.t('kb_status_change_failed'), 'error');
      }
    },
    // 选择供应商
    selectKbProvider(providerId) {
      if (providerId == 'paraphrase-multilingual-MiniLM-L12-v2'){
        this.newKb.model = providerId;
        this.newKb.base_url = `${backendURL}/minilm`
        this.newKb.api_key = 'MiniLM';
        return;
      }

      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.newKb.model = provider.modelId;
        this.newKb.base_url = provider.url;
        this.newKb.api_key = provider.apiKey;
      }
    },

    // 文件上传相关方法
    async browseKbFiles() {
        if (!this.isElectron) {
          const input = document.createElement('input')
          input.type = 'file'
          input.multiple = true
          input.accept = ALLOWED_EXTENSIONS.map(ext => `.${ext}`).join(',')
          
          input.onchange = (e) => {
            const files = Array.from(e.target.files)
            const validFiles = files.filter(this.isValidFileType)
            this.handleKbFiles(validFiles)
          }
          input.click()
        } else {
          const result = await window.electronAPI.openFileDialog();
          if (!result.canceled) {
            const validPaths = result.filePaths
              .filter(path => {
                const ext = path.split('.').pop()?.toLowerCase() || ''
                return ALLOWED_EXTENSIONS.includes(ext)
              })
            this.handleKbFiles(validPaths)
          }
        }
    },

    handleKbFiles(files) {
        if (files.length > 0) {
          this.addKbFiles(files)
        } else {
          this.showErrorAlert()
        }
    },
      // 添加文件到列表
    addKbFiles(files) {
      const newFiles = files.map(file => {
        if (typeof file === 'string') { // Electron路径
          return {
            path: file,
            name: file.split(/[\\/]/).pop()
          }
        }
        return { // 浏览器File对象
          path: URL.createObjectURL(file),// 生成临时URL
          name: file.name,
          file: file
        }
      });
      
      this.newKbFiles = [...this.newKbFiles, ...newFiles];
    },
    async handleKbDrop(event) {
      event.preventDefault();
      const files = Array.from(event.dataTransfer.files)
        .filter(this.isValidFileType);
      this.handleKbFiles(files);
    },
    removeKbFile(index) {
      this.newKbFiles.splice(index, 1);
    },
    switchToKnowledgePage() {
      this.activeMenu = 'toolkit';  // 根据你的菜单项配置的实际值设置
      this.subMenu = 'document';   // 根据你的子菜单项配置的实际值设置
    },
    switchToKnowledgeConfig(){
      this.activeMenu = 'toolkit';  // 根据你的菜单项配置的实际值设置
      this.subMenu = 'document';   // 根据你的子菜单项配置的实际值设置
      this.activeKbTab='settings';
      this.showAddKbDialog=false;
    },
    switchToMemoryConfig(){
      this.activeMenu = 'role';  // 根据你的菜单项配置的实际值设置
      this.subMenu = 'memory';   // 根据你的子菜单项配置的实际值设置
      this.activeMemoryTab='config';
      this.showAddMemoryDialog=false;
    },
    switchToMemory(){
      this.activeMenu = 'role';
      this.subMenu = 'memory'; 
    },
    // 在 methods 中添加
    t(key) {
      return this.translations[this.currentLanguage][key] || key;
    },
    async handleSystemLanguageChange(val) {
      this.systemSettings.language = val;
      if (val === 'auto') {
        // 获取系统设置，默认是'en-US'，如果系统语言是中文，则设置为'zh-CN'
        const systemLanguage = navigator.language || navigator.userLanguage || 'en-US';
        val = systemLanguage.startsWith('zh') ? 'zh-CN' : 'en-US';
      }
      this.currentLanguage = val; // 更新当前语言
      await this.autoSaveSettings();
      this.$forceUpdate();
    },
    // renderer.js 增强方法
    async handleThemeChange(val) {
      // 更新根属性
      document.documentElement.setAttribute('data-theme', val);
      
      this.systemSettings.theme = val;

      await this.autoSaveSettings();
    },
    async handleNetworkChange(val) {
      this.systemSettings.network = val;
      await window.electronAPI.setNetworkVisibility(val);
      this.showRestartDialog = true;
      await this.autoSaveSettings();
    },

    restartApp() {
      window.electronAPI.restartApp();
    },

    // 方法替换为：
    launchBrowserMode() {
      this.isBrowserOpening = true;
      
      setTimeout(() => {
        const url = this.partyURL;
        if (isElectron) {
          window.electronAPI.openExternal(url);
        } else {
          window.open(url, '_blank');
        }
        
        // 2秒后恢复状态
        setTimeout(() => {
          this.isBrowserOpening = false;
        }, 2000);
      }, 500);
    },
    launchAPIKeyManager() {
      this.isBrowserOpening = true;
      
      setTimeout(() => {
        const url = this.partyURL + '/token.html';
        if (isElectron) {
          window.electronAPI.openExternal(url);
        } else {
          window.open(url, '_blank');
        }
        
        // 2秒后恢复状态
        setTimeout(() => {
          this.isBrowserOpening = false;
        }, 2000);
      }, 500);
    },

    async getInternalIP() {
        try {
            const response = await fetch('/api/ip'); // 假设接口在同域名下
            const data = await response.json();
            return data.ip;
        } catch (error) {
            console.error("Failed to fetch internal IP:", error);
            return "127.0.0.1";
        }
    },
    async generateQRCode() {
      // 确保 partyURL 存在且 DOM 已渲染
      if (!this.partyURL) return;
      // 获取内网 IP
      const internalIP = await this.getInternalIP();

      // 替换 URL 中的 127.0.0.1 或 localhost，保留端口和路径
      const url = new URL(this.partyURL);
      if (url.hostname === '127.0.0.1' || url.hostname === 'localhost') {
        url.hostname = internalIP;
      }
      let qr_url = url.toString();
      const canvas = document.getElementById('qrcode');

      // 生成二维码
      QRCode.toCanvas(canvas, qr_url, function(error) {
            if (error) {
                console.error(error);
            } else {
                console.log("QR Code successfully generated!");
            }
        });
    },

    // 在methods中添加
    async addMCPServer() {
      try {
        let mcpId = "mcp";
        if (this.mcpInputType === 'json') {
          const input = this.newMCPJson.trim();
          const parsed = JSON.parse(input.startsWith('{') ? input : `{${input}}`);
          const servers = parsed.mcpServers || parsed;
          
          // 将服务器name作为ID
          mcpId = Object.keys(servers)[0];
          
          // 添加临时状态
          this.mcpServers = {
            ...this.mcpServers,
            [mcpId]: {
              ...servers[Object.keys(servers)[0]],
              processingStatus: 'initializing', // 新增状态字段
              disabled:true,
              type: this.newMCPType,
              input: input
            }
          };
        }
        else {
          mcpId = this.newMCPFormData.name;
          let servers = {};
          if (this.newMCPType === 'stdio'){
            servers = {
              "command": this.newMCPFormData.command,
            };
            // 处理args和env
            let args = this.newMCPFormData.args;
            let env = this.newMCPFormData.env;
            if (args) {
              // 按回车符分离成列表
              args = args.split('\n').map(arg => arg.trim()).filter(arg => arg);
              servers['args'] = args;
            }
            if (env) {
              // 按回车符分离成字典, 等号分离成键值对
              env = env.split('\n').map(env => env.trim()).filter(env => env).reduce((acc, cur) => {
                const [key, value] = cur.split('=').map(part => part.trim());
                acc[key] = value;
              })
              servers['env'] = env;
            }
          } 
          else {
            servers = {
              "url": this.newMCPFormData.url,
            };
            let ContentType = 'application/json';
            if (this.newMCPType== 'sse'){
              ContentType = 'text/event-stream';
            }else if (this.newMCPType== 'ws'){
              ContentType = 'text/plain';
            }else if (this.newMCPType== 'streamablehttp'){
              ContentType = 'application/json';
            }
            if (this.newMCPFormData.apiKey && this.newMCPFormData.apiKey.trim()!= '') {
              servers['headers'] = {
                "Authorization": `Bearer ${this.newMCPFormData.apiKey.trim()}`,
                "Content-Type": ContentType
              }
            }
          }
          let input = {
            "mcpServers": {
            }
          }
          input.mcpServers[mcpId] = servers;
          input = JSON.stringify(input, null, 2);
          // 添加临时状态
          this.mcpServers = {
            ...this.mcpServers,
            [mcpId]: {
              ...servers,
              processingStatus: 'initializing', // 新增状态字段
              disabled:true,
              type: this.newMCPType,
              input: input
            }
          };
        }
        
        this.showAddMCPDialog = false;
        this.newMCPJson = '';
        this.newMCPFormData = {
          name: 'mcp',
          command: '',
          args:'',
          env: '',
          url: '',
          apiKey: '',
        },
        await this.autoSaveSettings();
        // 触发后台任务
        const response = await fetch(`/create_mcp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mcpId })
        });
        
        // 启动状态轮询
        const checkStatus = async () => {
          const statusRes = await fetch(`/mcp_status/${mcpId}`);
          return statusRes.json();
        };
        
        const interval = setInterval(async () => {
          const { status,tools } = await checkStatus();
          
          if (status === 'ready') {
            clearInterval(interval);
            // 一次性写入，保证响应式
            this.mcpServers[mcpId] = {
              ...this.mcpServers[mcpId],
              processingStatus: 'ready',
              disabled: false,
              tools:JSON.parse(tools)    
            };
            console.log('tool:'+JSON.parse(tools));
            await this.autoSaveSettings();
            showNotification(this.t('mcpAdded'), 'success');
          } else if (status.startsWith('failed')) {
            clearInterval(interval);
            this.mcpServers[mcpId].processingStatus = 'server_error';
            this.mcpServers[mcpId].disabled = true;
            await this.autoSaveSettings();
            showNotification(this.t('mcpCreationFailed'), 'error');
          }
        }, 2000);
        
        await this.autoSaveSettings();
      } catch (error) {
        console.error('MCP服务器添加失败:', error);
        showNotification(error.message, 'error');
      }
      await this.autoSaveSettings();
    },

    async editMCPServer(name) {
      this.newMCPJson =  this.mcpServers[name].input
      this.newMCPType = this.mcpServers[name].type
      this.newMCPFormData = {
        name: name,
        command: this.mcpServers[name]?.command || '',
        args:this.mcpServers[name]?.args?.join('\n') || '',
        env: this.mcpServers[name]?.env ? Object.entries(this.mcpServers[name]?.env).map(env => `${env[0]}=${env[1]}`).join('\n') : '',
        url: this.mcpServers[name]?.url || '',
        apiKey: this.mcpServers[name]?.headers?.Authorization?.split(' ')[1] || '',
      }
      this.showAddMCPDialog = true
    },
    async restartMCPServer(name) {
      try {
        let mcpId = name
        this.mcpServers[name].processingStatus = 'initializing'
        this.mcpServers[name].disabled = true
        await this.autoSaveSettings();
        const response = await fetch(`/create_mcp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mcpId })
        });
        
          // 启动状态轮询
          const checkStatus = async () => {
            const statusRes = await fetch(`/mcp_status/${mcpId}`);
            return statusRes.json();
          };
          
          const interval = setInterval(async () => {
            const { status,tools } = await checkStatus();
            if (status === 'ready') {
              clearInterval(interval);
              this.mcpServers[mcpId] = {
                ...this.mcpServers[mcpId],
                processingStatus: 'ready',
                disabled: false,
                tools:JSON.parse(tools)    
              };
              await this.autoSaveSettings();
              showNotification(this.t('mcpAdded'), 'success');
            } else if (status.startsWith('failed')) {
              clearInterval(interval);
              this.mcpServers[mcpId].processingStatus = 'server_error';
              this.mcpServers[mcpId].disabled = true;
              await this.autoSaveSettings();
              showNotification(this.t('mcpCreationFailed'), 'error');
            }
          }, 2000);
          
          await this.autoSaveSettings();
        } catch (error) {
          console.error('MCP服务器添加失败:', error);
          showNotification(error.message, 'error');
        }
        await this.autoSaveSettings();

    },
    async removeMCPServer(name) {
      this.deletingMCPName = name
      this.showMCPConfirm = true
    },
    // 新增确认方法
    async confirmDeleteMCP() {
      try {
        const response = await fetch(`/remove_mcp`, {
          method: 'DELETE',
          headers: {
              'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            serverName: this.deletingMCPName
          })
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || '删除失败');
        }
        const name = this.deletingMCPName
        const newServers = { ...this.mcpServers }
        delete newServers[name]
        this.mcpServers = newServers
        
        this.$nextTick(async () => {
          await this.autoSaveSettings();
        })
        
        showNotification(this.t('mcpDeleted'), 'success')
      } catch (error) {
        console.error('Error:', error.message)
        showNotification(this.t('mcpDeleteFailed'), 'error')
      } finally {
        this.showMCPConfirm = false
      }
    },
      // 保存智能体
    truncatePrompt(text) {
      return text.length > 100 ? text.substring(0, 100) + '...' : text;
    },
    async saveAgent() {
      const payload = {
        type: 'save_agent',
        data: {
          name: this.newAgent.name,
          system_prompt: this.newAgent.system_prompt
        }
      };
      this.ws.send(JSON.stringify(payload));
      this.showAgentForm = false;
      this.newAgent = {
        id: '',
        name: '',
        system_prompt: ''
      };
    },
    copyAgentId(id) {
      navigator.clipboard.writeText(id)
      showNotification(`Agent ID: ${id} copyed`, 'success');
    },
    copyAgentName(name) {
      navigator.clipboard.writeText(name)
      showNotification(`Agent Name: ${name} copyed`, 'success');
    },
    async removeAgent(id) {
      if (this.agents.hasOwnProperty(id)) {
        delete this.agents[id]
        this.agents = { ...this.agents }
        try {
          // 向/delete_file发送请求
          const response = await fetch(`/remove_agent`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agentId: id })
          });
          // 处理响应
          if (response.ok) {
            console.log('Agent deleted successfully');
            showNotification(this.t('AgentDeleted'), 'success');
          }
        } catch (error) {
          console.error('Error:', error);
          showNotification(this.t('AgentDeleteFailed'), 'error');
        }
      }
      await this.autoSaveSettings();
    },
    isValidUrl(url) {
      try {
        new URL(url);
        return true;
      } catch {
        return false;
      }
    },
    async addA2AServer() {
      try {
        this.showAddA2ADialog = false;
        const newurl = this.newA2AUrl;
        this.newA2AUrl = '';
        this.a2aServers = {
          ...this.a2aServers,
          [newurl]: {
            status: 'initializing',
          }
        };
        await this.autoSaveSettings();
        const response = await fetch(`/a2a`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: newurl })
        });
        
        const data = await response.json();
        this.a2aServers[newurl] = {
          ...this.a2aServers[newurl],
          ...data
        }

        await this.autoSaveSettings();
      } catch (error) {
        console.error('A2A初始化失败:', error);
        this.a2aServers = Object.fromEntries(Object.entries(this.a2aServers).filter(([k]) => k !== newurl));
        await this.autoSaveSettings();
        showNotification(this.t('a2aInitFailed'), 'error');
      }
    },
    async removeA2AServer(url) {
      this.a2aServers = Object.fromEntries(Object.entries(this.a2aServers).filter(([k]) => k !== url));
      await this.autoSaveSettings();
    },
    formatDate(date) {
      // 时间戳转日期
      return new Date(date).toLocaleString();
    },
    async deleteFile(file) {
      console.log('deleteFile:', file);
      this.textFiles = this.textFiles.filter(f => f !== file);
      await this.autoSaveSettings();
      fileName = file.unique_filename
      try {
        // 向/delete_file发送请求
        const response = await fetch(`/delete_file`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fileName: fileName })
        });
        // 处理响应
        if (response.ok) {
          console.log('File deleted successfully');
          showNotification(this.t('fileDeleted'), 'success');
        }
      } catch (error) {
        console.error('Error:', error);
        showNotification(this.t('fileDeleteFailed'), 'error');
      }
    },
    // 顶部“全选 / 取消全选”
    toggleAll(checked) {
      this.selectedFiles = checked
        ? this.textFiles.map(f => f.unique_filename)
        : [];
    },
    async batchDeleteFiles() {
      if (this.selectedFiles.length === 0) return;

      try {
        const res = await fetch('/delete_files', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fileNames: this.selectedFiles })
        });
        const data = await res.json();

        // 只要后端说“有成功”就提示成功
        if (data.success && data.successFiles?.length) {
          // 把后端返回已成功删除的文件干掉
          this.textFiles = this.textFiles.filter(
            f => !data.successFiles.includes(f.unique_filename)
          );
          this.selectedFiles = [];          // 清空选中
          showNotification(this.t('batchDeleteSuccess'), 'success');
          await this.autoSaveSettings();
        } else {
          console.log('batchDeleteFiles error:', data);
          showNotification(this.t('batchDeleteFailed'), 'error');
        }
      } catch (e) {
        console.log('batchDeleteFiles error:', data);
        showNotification(this.t('batchDeleteFailed'), 'error');
      }
    },

    // 图片全选切换
    toggleAllImages(checked) {
      this.selectedImages = checked
        ? this.imageFiles.map(i => i.unique_filename)
        : []
    },
    
    // 视频全选切换
    toggleAllVideos(checked) {
      this.selectedVideos = checked
        ? this.videoFiles.map(v => v.unique_filename)
        : []
    },
    
    // 图片批量删除
    async batchDeleteImages() {
      if(!this.selectedImages.length) return
      
      try {
        const res = await fetch('/delete_files', {
          method: 'DELETE',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({fileNames: this.selectedImages})
        })
        
        if(res.ok) {
          // 更新前端列表
          this.imageFiles = this.imageFiles.filter(
            img => !this.selectedImages.includes(img.unique_filename)
          )
          this.selectedImages = []
          showNotification(this.t('batchDeleteSuccess'), 'success')
          await this.autoSaveSettings();
        }
      } catch(e) {
        showNotification(this.t('batchDeleteFailed'), 'error')
      }
    },
    
    // 视频批量删除（复用同一API）
    async batchDeleteVideos() {
      if(!this.selectedVideos.length) return
      try {
        const res = await fetch('/delete_files', {
          method: 'DELETE',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({fileNames: this.selectedVideos})
        })
        
        if(res.ok) {
          // 更新前端列表
          this.videoFiles = this.videoFiles.filter(
            img => !this.selectedVideos.includes(img.unique_filename)
          )
          this.selectedVideos = []
          showNotification(this.t('batchDeleteSuccess'), 'success')
          await this.autoSaveSettings();
        }
      } catch(e) {
        showNotification(this.t('batchDeleteFailed'), 'error')
      }
    },
    async deleteImage(img) {
      this.imageFiles = this.imageFiles.filter(i => i !== img);
      await this.autoSaveSettings();
      fileName = img.unique_filename
      try {
        // 向/delete_file发送请求
        const response = await fetch(`/delete_file`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fileName: fileName })
        });
        // 处理响应
        if (response.ok) {
          console.log('File deleted successfully');
          showNotification(this.t('fileDeleted'), 'success');
        }
      } catch (error) {
        console.error('Error:', error);
        showNotification(this.t('fileDeleteFailed'), 'error');
      }
    },
    getVendorLogo(vendor) {
      return this.vendorLogoList[vendor] || "source/providers/logo.png";
    },
    getMCPVendorLogo(vendor) {
      return this.MCPvendorLogoList[vendor] || "source/providers/logo.png";
    },
    getPromptVendorLogo(vendor) {
      return this.promptLogoList[vendor] || "source/providers/logo.png";
    },
    getCardVendorLogo(vendor) {
      return this.cardLogoList[vendor] || "source/providers/logo.png";
    },
    handleSelectVendor(vendor) {
      this.newProviderTemp.vendor = vendor;
      this.handleVendorChange(vendor);
    },

    selectMemoryProvider(providerId) {
      if (providerId == 'paraphrase-multilingual-MiniLM-L12-v2'){
        this.newMemory.model = providerId;
        this.newMemory.base_url = `${backendURL}/minilm`
        this.newMemory.api_key = 'MiniLM';
        return;
      }

      const provider = this.modelProviders.find(p => p.id === providerId);
      if (provider) {
        this.newMemory.model = provider.modelId;
        this.newMemory.base_url = provider.url;
        this.newMemory.api_key = provider.apiKey;
      }
    },

    // 世界书条目清空
    clearBook(idx) {
      this.newMemory.characterBook[idx].keysRaw = '';
      this.newMemory.characterBook[idx].content = '';
    },
    /* 世界书 */
    addBook() {
      this.newMemory.characterBook.push({ keysRaw: '', content: '' });
    },
    removeBook(idx) {
      this.newMemory.characterBook.splice(idx, 1);
    },
    clearGreeting(idx) {
      this.newMemory.alternateGreetings[idx] = '';
    },
    clearFirstMes() {
      this.newMemory.firstMes = '';
    },
    /* 删除 alternate greeting */
    removeGreeting(idx) {
      this.newMemory.alternateGreetings.splice(idx, 1);
    },
    /* 新增 alternate greeting */
    addGreeting() {
      this.newMemory.alternateGreetings.push('');
    },
    async addMemory() {
      this.selectMemoryProvider(this.newMemory.providerId);

      /* ---- 0. 备份旧数据（更新场景用） ---- */
      const oldMemory = this.newMemory.id
        ? this.memories.find(m => m.id === this.newMemory.id)
        : 1024;

      /* ---- 1. 立即生成内存对象（用户可瞬间看到） ---- */
      const build = (dims = 1024) => ({
        id: this.newMemory.id || uuid.v4(),
        name: this.newMemory.name,
        providerId: this.newMemory.providerId,
        model: this.newMemory.model,
        api_key: this.newMemory.api_key,
        base_url: this.newMemory.base_url,
        embedding_dims: dims,
        vendor: this.newMemory.providerId
          ? this.modelProviders.find(p => p.id === this.newMemory.providerId)?.vendor || ''
          : '',
        description: this.newMemory.description,
        avatar: this.newMemory.avatar,
        personality: this.newMemory.personality,
        mesExample: this.newMemory.mesExample,
        systemPrompt: this.newMemory.systemPrompt,
        firstMes: this.newMemory.firstMes,
        alternateGreetings: this.newMemory.alternateGreetings.filter(Boolean),
        characterBook: this.newMemory.characterBook.filter(e => e.keysRaw.trim() || e.content.trim())
      });

      let memory;
      let insertIdx = -1;          // 用于更新场景
      if (this.newMemory.id === null) {
        memory = build();
        this.memories.push(memory);
        if (this.memorySettings.selectedMemory === null) {
          this.memorySettings.selectedMemory = memory.id;
        }
      } else {
        insertIdx = this.memories.findIndex(m => m.id === this.newMemory.id);
        if (insertIdx === -1) return;
        memory = build(oldMemory?.embedding_dims ?? 1024);
        this.memories.splice(insertIdx, 1, memory);
      }
      this.showAddMemoryDialog = false;
      if (this.newMemory.providerId != null){
        /* ---- 2. 异步探测维度（失败则回滚） ---- */
        try {
          const resp = await fetch('/api/embedding_dims', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              api_key:  this.newMemory.api_key,
              base_url: this.newMemory.base_url,
              model:    this.newMemory.model
            })
          });

          // ******** 关键点 ********
          if (!resp.ok) {                           // 4xx/5xx 都进这里
            const txt = await resp.text();
            throw new Error(`Embedding 接口异常 ${resp.status}: ${txt}`);
          }

          const { dims } = await resp.json();
          memory.embedding_dims = dims;
          await this.autoSaveSettings();          // 真正落盘
        } catch (e) {
          /* ---- 3. 回滚 & 提示 ---- */
          if (this.newMemory.id === null) {
            // 新增：直接 pop
            this.memories.pop();
            if (this.memorySettings.selectedMemory === memory.id) {
              this.memorySettings.selectedMemory = null;
            }
          } else {
            // 更新：把旧记忆写回去
            if (oldMemory) this.memories.splice(insertIdx, 1, oldMemory);
          }
          // 保证能拿到 t 函数
          showNotification(this.t('EmbeddingFailed'), 'error');
          console.error('[addMemory] 探测维度失败', e);
          return;   // 不再继续
        }
      }

      /* ---- 4. 收尾 ---- */
      this.resetNewMemory();
      this.changeMemory();
    },
    
    async removeMemory(id) {
      this.memories = this.memories.filter(m => m.id !== id);
      if (this.memorySettings.selectedMemory === id){
        this.memorySettings.selectedMemory = null;
      }
      try {
        // 向/delete_file发送请求
        const response = await fetch(`/remove_memory`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ memoryId: id })
        });
        // 处理响应
        if (response.ok) {
          console.log('memory deleted successfully');
          showNotification(this.t('memoryDeleted'), 'success');
        }
      } catch (error) {
        console.error('Error:', error);
        showNotification(this.t('memoryDeleteFailed'), 'error');
      }
      await this.autoSaveSettings();
    },
    editMemory(id) {
      const memory = this.memories.find(m => m.id === id);
      if (memory) {
        this.newMemory = { ...memory };
        if (this.newMemory.characterBook.length === 0){
          this.newMemory.characterBook = [{ keysRaw: '', content: '' }];
        }
        this.showAddMemoryDialog = true;
      }
    },

    
    getVendorName(providerId) {
      if (providerId == 'paraphrase-multilingual-MiniLM-L12-v2'){
        return `${this.t("model")}:${providerId}`;
      }
      const provider = this.modelProviders.find(p => p.id === providerId);
      return provider ? `${this.t("model")}:${provider.modelId}` : this.t("NoLongTermMemory");
    },
    async saveCustomHttpTool() {
      const toolData = { ...this.newCustomHttpTool };
      
      if (this.editingCustomHttpTool) {
        // 更新现有工具
        const index = this.customHttpTools.findIndex(tool => tool.id === toolData.id);
        if (index !== -1) {
          this.customHttpTools.splice(index, 1, toolData);
        }
      } else {
        // 添加新工具
        toolData.id = uuid.v4();
        this.customHttpTools.push(toolData);
      }
      
      // 与后端同步数据
      await this.autoSaveSettings();
      
      // 重置表单
      this.newCustomHttpTool = {
        enabled: true,
        name: '',
        description: '',
        url: '',
        method: 'GET',
        headers: '',
        body: ''
      };
      this.showCustomHttpToolForm = false;
      this.editingCustomHttpTool = false;
    },
    editCustomHttpTool(id) {
      const tool = this.customHttpTools.find(tool => tool.id === id);
      if (tool) {
        this.newCustomHttpTool = { ...tool };
        this.showCustomHttpToolForm = true;
        this.editingCustomHttpTool = true;
      }
    },
    async removeCustomHttpTool(id) {
      this.customHttpTools = this.customHttpTools.filter(tool => tool.id !== id);
      await this.autoSaveSettings();
    },
  // 启动QQ机器人
  async startQQBot() {
    this.isStarting = true;
    
    try {
      // 显示连接中的提示
      showNotification('正在连接QQ机器人...', 'info');
      
      const response = await fetch(`/start_qq_bot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.qqBotConfig)
      });

      const result = await response.json();
      
      if (result.success) {
        this.isQQBotRunning = true;
        showNotification('QQ机器人已成功启动并就绪', 'success');
      } else {
        // 显示具体错误信息
        const errorMessage = result.message || '启动失败，请检查配置';
        showNotification(`启动失败: ${errorMessage}`, 'error');
        
        // 如果是超时错误，给出更具体的提示
        if (errorMessage.includes('超时')) {
          showNotification('提示：请检查网络连接和机器人配置是否正确', 'warning');
        }
      }
    } catch (error) {
      console.error('启动QQ机器人时出错:', error);
      showNotification('启动QQ机器人失败: 网络错误或服务器未响应', 'error');
    } finally {
      this.isStarting = false;
    }
  },

  // 停止QQ机器人
  async stopQQBot() {
    this.isStopping = true;
    
    try {
      const response = await fetch(`/stop_qq_bot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const result = await response.json();
      
      if (result.success) {
        this.isQQBotRunning = false;
        showNotification('QQ机器人已成功停止', 'success');
      } else {
        const errorMessage = result.message || '停止失败';
        showNotification(`停止失败: ${errorMessage}`, 'error');
      }
    } catch (error) {
      console.error('停止QQ机器人时出错:', error);
      showNotification('停止QQ机器人失败: 网络错误或服务器未响应', 'error');
    } finally {
      this.isStopping = false;
    }
  },

  // 重载QQ机器人配置
  async reloadQQBotConfig() {
    this.isReloading = true;
    
    try {
      const response = await fetch(`/reload_qq_bot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.qqBotConfig)
      });

      const result = await response.json();
      
      if (result.success) {
        if (result.config_changed) {
          showNotification('QQ机器人配置已重载并重新启动', 'success');
        } else {
          showNotification('QQ机器人配置已更新', 'success');
        }
      } else {
        const errorMessage = result.message || '重载失败';
        showNotification(`重载失败: ${errorMessage}`, 'error');
      }
    } catch (error) {
      console.error('重载QQ机器人配置时出错:', error);
      showNotification('重载QQ机器人配置失败: 网络错误或服务器未响应', 'error');
    } finally {
      this.isReloading = false;
    }
  },
  
  // 添加状态检查方法
  async checkQQBotStatus() {
    try {
      const response = await fetch(`/qq_bot_status`);
      const status = await response.json();
      
      // 更新机器人运行状态
      this.isQQBotRunning = status.is_running;
      
      // 如果机器人正在运行但前端状态不一致，更新状态
      if (status.is_running && !this.isQQBotRunning) {
        this.isQQBotRunning = true;
      }
    } catch (error) {
      console.error('检查机器人状态失败:', error);
    }
  },

    // 新增的方法：供主进程请求关闭机器人
    async requestStopQQBotIfRunning() {
      try {
        const response = await fetch(`/qq_bot_status`)
        const status = await response.json()

        if (status.is_running) {
          // 调用 stopQQBot 来关闭机器人
          await this.stopQQBot()
          console.log('机器人已关闭')
        }
      } catch (error) {
        console.error('检查或停止机器人失败:', error)
      }
    },

 async requestFeishuBotStopIfRunning(){
      try {
        const response = await fetch(`/feishu_bot_status`)
        const status = await response.json()

        if (status.is_running) {
          // 调用 stopQQBot 来关闭机器人
          await this.stopFeishuBot()
          console.log('机器人已关闭')
        }
      } catch (error) {
        console.error('检查或停止机器人失败:', error)
      }
 },

async startFeishuBot() {
  this.isFeishuStarting = true;
  try {
    showNotification('正在连接飞书机器人...', 'info');
    const res = await fetch('/start_feishu_bot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.feishuBotConfig),
    });
    const json = await res.json();
    if (json.success) {
      this.isFeishuBotRunning = true;
      showNotification('飞书机器人启动成功', 'success');
    } else {
      showNotification(`启动失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isFeishuStarting = false;
  }
},
async stopFeishuBot() {
  this.isFeishuStopping = true;
  try {
    const res = await fetch('/stop_feishu_bot', { method: 'POST' });
    const json = await res.json();
    if (json.success) {
      this.isFeishuBotRunning = false;
      showNotification('飞书机器人已停止', 'success');
    } else {
      showNotification(`停止失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isFeishuStopping = false;
  }
},
async reloadfeishuBotConfig() {
  this.isFeishuReloading = true;
  try {
    const res = await fetch('/reload_feishu_bot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.feishuBotConfig),
    });
    const json = await res.json();
    if (json.success) {
      showNotification('飞书机器人已重载', 'success');
    } else {
      showNotification(`重载失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isFeishuReloading = false;
  }
},
async checkFeishuBotStatus() {
  try {
    const res = await fetch('/feishu_bot_status');
    const st = await res.json();
    this.isFeishuBotRunning = st.is_running;
  } catch (e) {
    console.error('检查飞书机器人状态失败', e);
  }
},
handleCreateFeishuSeparator(val) {
  this.feishuBotConfig.separators.push(val);
},

async requestTelegramBotStopIfRunning() {
  try {
    const res = await fetch('/telegram_bot_status');
    const st = await res.json();
    if (st.is_running) await this.stopTelegramBot();
  } catch (e) {
    console.error('检查或停止 Telegram 机器人失败:', e);
  }
},
async startTelegramBot() {
  this.isTelegramStarting = true;
  try {
    showNotification('正在连接 Telegram 机器人...', 'info');
    const res = await fetch('/start_telegram_bot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.telegramBotConfig)
    });
    const json = await res.json();
    if (json.success) {
      this.isTelegramBotRunning = true;
      showNotification('Telegram 机器人启动成功', 'success');
    } else {
      showNotification(`启动失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isTelegramStarting = false;
  }
},
async stopTelegramBot() {
  this.isTelegramStopping = true;
  try {
    const res = await fetch('/stop_telegram_bot', { method: 'POST' });
    const json = await res.json();
    if (json.success) {
      this.isTelegramBotRunning = false;
      showNotification('Telegram 机器人已停止', 'success');
    } else {
      showNotification(`停止失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isTelegramStopping = false;
  }
},
async reloadTelegramBotConfig() {
  this.isTelegramReloading = true;
  try {
    const res = await fetch('/reload_telegram_bot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.telegramBotConfig)
    });
    const json = await res.json();
    if (json.success) {
      showNotification('Telegram 机器人已重载', 'success');
    } else {
      showNotification(`重载失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isTelegramReloading = false;
  }
},
async checkTelegramBotStatus() {
  try {
    const res = await fetch('/telegram_bot_status');
    const st = await res.json();
    this.isTelegramBotRunning = st.is_running;
  } catch (e) {
    console.error('检查 Telegram 机器人状态失败', e);
  }
},
handleCreateTelegramSeparator(val) {
  this.telegramBotConfig.separators.push(val);
},

/* ------- Discord 机器人 ------- */
async startDiscordBot() {
  this.isDiscordStarting = true;
  try {
    showNotification('正在连接 Discord 机器人...', 'info');
    const res = await fetch('/start_discord_bot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.discordBotConfig),
    });
    const json = await res.json();
    if (json.success) {
      this.isDiscordBotRunning = true;
      showNotification('Discord 机器人启动成功', 'success');
    } else {
      showNotification(`启动失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isDiscordStarting = false;
  }
},
async stopDiscordBot() {
  this.isDiscordStopping = true;
  try {
    const res = await fetch('/stop_discord_bot', { method: 'POST' });
    const json = await res.json();
    if (json.success) {
      this.isDiscordBotRunning = false;
      showNotification('Discord 机器人已停止', 'success');
    } else {
      showNotification(`停止失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isDiscordStopping = false;
  }
},
async reloadDiscordBot() {
  this.isDiscordReloading = true;
  try {
    const res = await fetch('/reload_discord_bot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.discordBotConfig),
    });
    const json = await res.json();
    if (json.success) {
      showNotification('Discord 机器人已重载', 'success');
    } else {
      showNotification(`重载失败：${json.message}`, 'error');
    }
  } catch (e) {
    showNotification('网络错误或服务器未响应', 'error');
  } finally {
    this.isDiscordReloading = false;
  }
},
async checkDiscordBotStatus() {
  try {
    const res = await fetch('/discord_bot_status');
    const st = await res.json();
    this.isDiscordBotRunning = st.is_running;
  } catch (e) {
    console.error('检查 Discord 机器人状态失败', e);
  }
},
handleCreateDiscordSeparator(val) {
  this.discordBotConfig.separators.push(val);
},

    // // 启动微信机器人
    // async startWXBot() {
    //   this.isWXStarting = true;

    //   try {
    //     // 显示连接中的提示
    //     showNotification('正在连接微信机器人...', 'info');

    //     const response = await fetch(`/start_wx_bot`, {
    //       method: 'POST',
    //       headers: { 'Content-Type': 'application/json' },
    //       body: JSON.stringify(this.WXBotConfig)
    //     });

    //     const result = await response.json();

    //     if (result.success) {
    //       this.isWXBotRunning = true;
    //       showNotification('微信机器人已成功启动并就绪', 'success');
    //     } else {
    //       // 显示具体错误信息
    //       const errorMessage = result.message || '启动失败，请检查配置';
    //       showNotification(`启动失败: ${errorMessage}`, 'error');

    //       // 如果是超时错误，给出更具体的提示
    //       if (errorMessage.includes('超时')) {
    //         showNotification('提示：请检查网络连接和机器人配置是否正确', 'warning');
    //       }
    //     }
    //   } catch (error) {
    //     console.error('启动微信机器人时出错:', error);
    //     showNotification('启动微信机器人失败: 网络错误或服务器未响应', 'error');
    //   } finally {
    //     this.isWXStarting = false;
    //   }
    // },

    // // 停止微信机器人
    // async stopWXBot() {
    //   this.isWXStopping = true;

    //   try {
    //     const response = await fetch(`/stop_wx_bot`, {
    //       method: 'POST',
    //       headers: { 'Content-Type': 'application/json' }
    //     });

    //     const result = await response.json();

    //     if (result.success) {
    //       this.isWXBotRunning = false;
    //       showNotification('微信机器人已成功停止', 'success');
    //     } else {
    //       const errorMessage = result.message || '停止失败';
    //       showNotification(`停止失败: ${errorMessage}`, 'error');
    //     }
    //   } catch (error) {
    //     console.error('停止微信机器人时出错:', error);
    //     showNotification('停止微信机器人失败: 网络错误或服务器未响应', 'error');
    //   } finally {
    //     this.isWXStopping = false;
    //   }
    // },

    // // 重载微信机器人配置
    // async reloadWXBotConfig() {
    //   this.isWXReloading = true;

    //   try {
    //     const response = await fetch(`/reload_wx_bot`, {
    //       method: 'POST',
    //       headers: { 'Content-Type': 'application/json' },
    //       body: JSON.stringify(this.WXBotConfig)
    //     });

    //     const result = await response.json();

    //     if (result.success) {
    //       if (result.config_changed) {
    //         showNotification('微信机器人配置已重载并重新启动', 'success');
    //       } else {
    //         showNotification('微信机器人配置已更新', 'success');
    //       }
    //     } else {
    //       const errorMessage = result.message || '重载失败';
    //       showNotification(`重载失败: ${errorMessage}`, 'error');
    //     }
    //   } catch (error) {
    //     console.error('重载微信机器人配置时出错:', error);
    //     showNotification('重载微信机器人配置失败: 网络错误或服务器未响应', 'error');
    //   } finally {
    //     this.isWXReloading = false;
    //   }
    // },

    // // 检查微信机器人状态
    // async checkWXBotStatus() {
    //   try {
    //     const response = await fetch(`/wx_bot_status`);
    //     const status = await response.json();

    //     // 更新机器人运行状态
    //     this.isWXBotRunning = status.is_running;

    //     // 如果机器人正在运行但前端状态不一致，更新状态
    //     if (status.is_running && !this.isWXBotRunning) {
    //       this.isWXBotRunning = true;
    //     }
    //   } catch (error) {
    //     console.error('检查机器人状态失败:', error);
    //   }
    // },

    // // 新增的方法：供主进程请求关闭机器人
    // async requestStopWXBotIfRunning() {
    //   try {
    //     const response = await fetch(`/wx_bot_status`)
    //     const status = await response.json()

    //     if (status.is_running) {
    //       // 调用 stopWXBot 来关闭机器人
    //       await this.stopWXBot()
    //       console.log('机器人已关闭')
    //     }
    //   } catch (error) {
    //     console.error('检查或停止机器人失败:', error)
    //   }
    // },

    async handleSeparatorChange(val) {
      this.qqBotConfig.separators = val.map(s => 
        s.replace(/\\n/g, '\n').replace(/\\t/g, '\t')
      );
      await this.autoSaveSettings();
    },
    formatSeparator(s) {
      return s.replace(/\n/g, '\\n')
              .replace(/\t/g, '\\t')
              .replace(/\r/g, '\\r');
    },
    // 新增创建分隔符处理方法
    async handleCreateSeparator(newSeparator) {
      const processed = this.escapeSeparator(newSeparator)
      if (!this.qqBotConfig.separators.includes(processed)) {
        this.qqBotConfig.separators.push(processed)
        await this.autoSaveSettings()
      }
    },

    // 处理回车键冲突
    handleEnter(e) {
      if (e.target.value) {
        e.stopPropagation()
      }
    },

    escapeSeparator(s) {
      return s.replace(/\\n/g, '\n').replace(/\\t/g, '\t')
    },

    // 一键重置
    resetNewMemory() {
      this.newMemory = {
        id: null,
        name: '',
        providerId: null,
        model: '',
        base_url: '',
        api_key: '',
        vendor: '',
        description: '',
        avatar: '',
        personality: '',
        mesExample: '',
        systemPrompt: '',
        firstMes: '',
        alternateGreetings: [],
        characterBook: [{ keysRaw: '', content: '' }]
      };
    },
    copyExistingMemoryData(selectedId) {
      const src = this.memories.find(m => m.id === selectedId);
      if (src) {
        /* 把旧字段映射到新字段，没有的就给默认值 */
        this.newMemory = {
          id: null,
          name: src.name || '',
          providerId: src.providerId || null,
          model: src.model || '',
          base_url: src.base_url || '',
          api_key: src.api_key || '',
          vendor: src.vendor || '',

          /* 旧→新 */
          description: src.basic_character || src.description || '',
          avatar: src.avatar || '',
          personality: src.personality || '',
          mesExample: src.mesExample || '',
          systemPrompt: src.systemPrompt || '',
          firstMes: src.firstMes || (Array.isArray(src.random) ? src.random[0]?.value : ''),
          alternateGreetings:
            Array.isArray(src.alternateGreetings)
              ? src.alternateGreetings
              : (src.random || []).slice(1).map(r => r.value),
          characterBook:
            Array.isArray(src.characterBook)
              ? src.characterBook
              : (src.lorebook || []).map(l => ({
                  keysRaw: l.name,
                  content: l.value
                }))  
        };
           if (this.newMemory.characterBook.length == 0 ){
              this.newMemory.characterBook = [{ keysRaw: '', content: '' }]
           }   
      } else {
        /* 新建：直接给空模板 */
        this.resetNewMemory();
      }
    },
    colorBlend(color1, color2, ratio) {
        // 确保ratio在0-1范围内
        ratio = Math.max(0, Math.min(1, ratio));
        
        // 解析十六进制颜色值
        const parseHex = (hex) => {
          hex = hex.replace(/^#/, '');
          // 处理3位简写格式
          if (hex.length === 3) {
            hex = hex.split('').map(char => char + char).join('');
          }
          return {
            r: parseInt(hex.substring(0, 2), 16),
            g: parseInt(hex.substring(2, 4), 16),
            b: parseInt(hex.substring(4, 6), 16)
          };
        };

        // 转换为两位十六进制字符串
        const toHex = (value) => {
          const hex = Math.round(value).toString(16);
          return hex.length === 1 ? '0' + hex : hex;
        };

        const rgb1 = parseHex(color1);
        const rgb2 = parseHex(color2);

        // 计算混合后的RGB值
        const r = rgb1.r * ratio + rgb2.r * (1 - ratio);
        const g = rgb1.g * ratio + rgb2.g * (1 - ratio);
        const b = rgb1.b * ratio + rgb2.b * (1 - ratio);

        // 组合成十六进制颜色
        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
      },
      toggleInputExpand() {
        this.isInputExpanded = !this.isInputExpanded
    },
    checkMobile() {
      this.isMobile = window.innerWidth <= 768;
      this.isAssistantMode = window.innerWidth <= 350 && window.innerHeight <= 680;
      this.isCapsuleMode = window.innerWidth <= 230 && window.innerHeight <= 100;
      if (this.isMobile) {
        this.MoreButtonDict = this.smallMoreButtonDict;
      }
      else{
        this.MoreButtonDict = this.largeMoreButtonDict;
      }
      if (this.isAssistantMode){
        if(!this.isFixedWindow){
          this.isFixedWindow = true;
          if (isElectron){
            window.electronAPI.setAlwaysOnTop(this.isFixedWindow);
          }
        }
        
      }else{
        if(this.isFixedWindow){
          this.isFixedWindow = false;
          if (isElectron){
            window.electronAPI.setAlwaysOnTop(this.isFixedWindow);
          }
        }
      }
      if(this.isMobile) this.sidebarVisible = false;
    },
    // 添加ComfyUI服务器
    addComfyUIServer() {
      this.comfyuiServers.push('http://localhost:8188')
      this.autoSaveSettings()
    },

    // 移除服务器
    removeComfyUIServer(index) {
      if (this.comfyuiServers.length > 1) {
        this.comfyuiServers.splice(index, 1)
        this.autoSaveSettings()
      }
    },

    // 连接服务器
    async connectComfyUI(index) {
      this.isConnecting = true
      try {
        const url = this.comfyuiServers[index]
        const response = await fetch(`${url}/history`, {
          method: 'HEAD',
          mode: 'cors'
        })
        if (response.ok) {
          this.activeComfyUIUrl = url
          showNotification('服务器连接成功')
        }
      } catch (e) {
        showNotification('无法连接ComfyUI服务器', 'error')
      }
      this.isConnecting = false
    },
    // 浏览文件
    browseWorkflowFile() {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';
      input.onchange = (event) => {
        const files = event.target.files;
        if (files.length > 0) {
          this.workflowFile = files[0];
          this.loadWorkflowFile(this.workflowFile); // 确保在文件已选择后调用
        }
      };
      input.click();
    },
    // 移除文件
    removeWorkflowFile() {
      this.workflowFile = null;
    },
    // 删除工作流
    async deleteWorkflow(filename) {
      try {
        const response = await fetch(`/delete_workflow/${filename}`, {
          method: 'DELETE',
        });
        const data = await response.json();
        if (data.success) {
          this.workflows = this.workflows.filter(file => file.unique_filename !== filename);
          await this.autoSaveSettings();
          showNotification('删除成功');
        } else {
          this.workflows = this.workflows.filter(file => file.unique_filename !== filename);
          await this.autoSaveSettings();
          showNotification('删除失败', 'error');
        }
      } catch (error) {
        console.error('删除失败:', error);
       showNotification('删除失败', 'error');
      }
    },
      // 处理文件拖拽
  handleWorkflowDrop(event) {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      this.workflowFile = files[0];
      this.loadWorkflowFile(this.workflowFile); // 加载工作流文件以生成选择项
    }
  },
  
  // 加载工作流文件
  async loadWorkflowFile(file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      const workflowJson = JSON.parse(event.target.result);
      this.populateInputOptions(workflowJson);
    };
    reader.readAsText(file);
  },

  // 填充输入选择项
  populateInputOptions(workflowJson) {
    this.textInputOptions = [];
    this.imageInputOptions = [];
    this.seedInputOptions = [];
    
    for (const nodeId in workflowJson) {
      const node = workflowJson[nodeId];
      if (!node.inputs) continue;
      
      // 查找所有包含text/value/prompt的文本输入字段
      const textInputKeys = Object.keys(node.inputs).filter(key => 
        (key.includes('text') || key.includes('value') || key.includes('prompt')) &&
        typeof node.inputs[key] === 'string' // 确保值是字符串类型
      );
      
      // 为每个符合条件的字段创建选项
      textInputKeys.forEach(key => {
        this.textInputOptions.push({
          label: `${node._meta.title} - ${key} (ID: ${nodeId})`,
          value: { nodeId, inputField: key, id : `${nodeId}-${key}` },
        });
      });
      
      // 查找图片输入字段
      if (node.class_type === 'LoadImage') {
        const imageKeys = Object.keys(node.inputs).filter(key => 
          key.includes('image') && 
          typeof node.inputs[key] === 'string' // 确保值是字符串类型
        );
        
        imageKeys.forEach(key => {
          this.imageInputOptions.push({
            label: `${node._meta.title} - ${key} (ID: ${nodeId})`,
            value: { nodeId, inputField: key, id : `${nodeId}-${key}` },
          });
        });
      }

      // 查找所有包含seed的种子输入字段
      const seedInputKeys = Object.keys(node.inputs).filter(
        key => key.includes('seed') && typeof node.inputs[key] === 'number' // 确保值是数字类型
      )
      seedInputKeys.forEach(key => {
        this.seedInputOptions.push({
          label: `${node._meta.title} - ${key} (ID: ${nodeId})`,
          value: { nodeId, inputField: key, id : `${nodeId}-${key}` },
        });
      })
    }
  },

    // 上传文件
    async uploadWorkflow() {
      if (!this.workflowFile) return;

      const formData = new FormData();
      formData.append('file', this.workflowFile);

      // 记录所选的输入位置
      const workflowData = {
        textInput: this.selectedTextInput,
        textInput2: this.selectedTextInput2,
        imageInput: this.selectedImageInput,
        imageInput2: this.selectedImageInput2,
        seedInput: this.selectedSeedInput,
        seedInput2: this.selectedSeedInput2,
        description: this.workflowDescription,
      };

      // 发送 JSON 字符串作为普通字段
      formData.append('workflow_data', JSON.stringify(workflowData));

      try {
        const response = await fetch(`/add_workflow`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) { // 检查响应状态
          const errorText = await response.text(); // 获取错误文本
          console.error("Server error:", errorText); // 输出错误信息
          throw new Error("Server error");
        }

        const data = await response.json();
        if (data.success) {
          this.workflows.push(data.file);
          this.showWorkflowUploadDialog = false;
          this.workflowFile = null;
          this.selectedTextInput = null; // 重置选中
          this.selectedImageInput = null; // 重置选中
          this.selectedTextInput2 = null; // 重置选中
          this.selectedImageInput2 = null; // 重置选中
          this.selectedSeedInput = null; // 重置选中
          this.selectedSeedInput2 = null; // 重置选中
          this.workflowDescription = ''; // 清空描述
          await this.autoSaveSettings();
          showNotification('上传成功');
        } else {
          showNotification('上传失败', 'error');
        }
      } catch (error) {
        console.error('上传失败:', error);
        showNotification('上传失败', 'error');
      }
    },
    cancelWorkflowUpload() {
      this.showWorkflowUploadDialog = false;
      this.workflowFile = null;
      this.selectedTextInput = null; // 重置选中
      this.selectedImageInput = null; // 重置选中
      this.selectedTextInput2 = null; // 重置选中
      this.selectedImageInput2 = null; // 重置选中
      this.selectedSeedInput = null; // 重置选中
      this.selectedSeedInput2 = null; // 重置选中
      this.workflowDescription = ''; // 清空描述
    },
    async deleteVideo(video) {
      this.videoFiles = this.videoFiles.filter(i => i !== video);
      await this.autoSaveSettings();
      fileName = video.unique_filename
      try {
        // 向/delete_file发送请求
        const response = await fetch(`/delete_file`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fileName: fileName })
        });
        // 处理响应
        if (response.ok) {
          console.log('File deleted successfully');
          showNotification(this.t('fileDeleted'), 'success');
        }
      } catch (error) {
        console.error('Error:', error);
        showNotification(this.t('fileDeleteFailed'), 'error');
      }
    },

    goToURL(provider) {
        if (provider.vendor === 'custom') {
          url = provider.url;
          // 移除url尾部的/v1
          if (url.endsWith('/v1')) {
            url = url.slice(0, -3);
          }
        }
        else {
          url = this.vendorAPIpage[provider.vendor];
        }
        if (isElectron) {
          window.electronAPI.openExternal(url);
        } else {
          window.open(url, '_blank');
        }
    },
    goToMCPURL(value) {
        url = this.MCPpage[value]
        if (isElectron) {
          window.electronAPI.openExternal(url);
        } else {
          window.open(url, '_blank');
        }
    },
    goToPromptURL(value) {
        url = this.promptPage[value]
        if (isElectron) {
          window.electronAPI.openExternal(url);
        } else {
          window.open(url, '_blank');
        }
    },
    goToCardURL(value) {
        url = this.cardPage[value]
        if (isElectron) {
          window.electronAPI.openExternal(url);
        } else {
          window.open(url, '_blank');
        }
    },
    handleBeforeUpload(file) {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => {
        this.uploadedStickers.push({
          uid: file.uid,
          url: reader.result,
          description: "",
          file: file
        })
      }
      return false // 阻止自动上传
    },

    handleStickerRemove(file) {
      this.uploadedStickers = this.uploadedStickers.filter(f => f.uid !== file.uid)
    },

    async createStickerPack() {
      try {
        // 验证输入
        if (!this.newStickerPack.name || this.uploadedStickers.length === 0) {
          showNotification(this.t('fillAllFields'), 'warning');
          return;
        }
        

        // 创建FormData对象
        const formData = new FormData();
        
        // 添加表情包名称
        formData.append('pack_name', this.newStickerPack.name);
        
        // 添加所有表情描述
        this.uploadedStickers.forEach(sticker => {
          formData.append('descriptions', sticker.description);
        });
        
        // 添加所有表情文件
        this.uploadedStickers.forEach(sticker => {
          formData.append('files', sticker.file);
        });

        // 发送请求
        const response = await fetch(`/create_sticker_pack`, {
          method: 'POST',
          body: formData
        });
        
        // 处理响应
        if (!response.ok) {
          const errorData = await response.json();
          console.error("服务器错误详情:", errorData);
          
          let errorMsg = this.t('uploadFailed');
          if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
              errorMsg = errorData.detail;
            } else if (errorData.detail[0]?.msg) {
              errorMsg = errorData.detail[0].msg;
            }
          }
          
          throw new Error(errorMsg);
        }

        const data = await response.json();
        if (data.success) {
          // 更新前端状态
          this.stickerPacks.push({
            id: data.id,
            name: data.name,
            stickers: data.stickers,
            cover: data.cover,
            enabled: true
          });
          
          this.imageFiles = [...this.imageFiles, ...data.imageFiles];
          this.resetStickerForm();
          await this.autoSaveSettings();
          
          showNotification(this.t('stickerPackCreated'));
          this.showStickerDialog = false;
        } else {
          showNotification(data.message || this.t('createFailed'), 'error');
          this.showStickerDialog = false;
        }
      } catch (error) {
        console.error('创建失败:', error);
        showNotification(
          error.message || this.t('createFailed'), 
          'error'
        );
        this.showStickerDialog = false;
      }
    },

    deleteStickerPack(stickerPack) {
      this.stickerPacks = this.stickerPacks.filter(pack => pack.id !== stickerPack.id);
      this.autoSaveSettings();
      showNotification(this.t('stickerPackDeleted'));
    },
    cancelStickerUpload() {
      this.showStickerDialog = false;
      this.resetStickerForm();
    },

    resetStickerForm() {
      this.newStickerPack = {
        name: '',
        stickers: [],
      };
      this.uploadedStickers = [];
    },
    handlePictureCardPreview(file) {
      this.imageUrl = file.url || URL.createObjectURL(file.raw)
      this.dialogVisible = true
    },
    downloadMemory(memory) {
      // 仅导出酒馆 V3 所需字段，敏感信息全部剔除
      const card = {
        spec: 'chara_card_v3',
        spec_version: '3.0',
        name: memory.name,
        description: memory.description || '',
        avatar: memory.avatar || '',
        personality: memory.personality || '',
        mes_example: memory.mesExample || '',
        first_mes: memory.firstMes || '',
        system_prompt: memory.systemPrompt || '',
        alternate_greetings: Array.isArray(memory.alternateGreetings)
          ? memory.alternateGreetings.filter(Boolean)
          : [],
        character_book: {
          name: memory.name,
          entries: Array.isArray(memory.characterBook)
            ? memory.characterBook
                .filter(e => e.keysRaw?.trim() && e.content?.trim())
                .map((e, idx) => ({
                  id: idx,
                  keys: e.keysRaw
                    .split(/\r?\n/)
                    .map(k => k.trim())
                    .filter(Boolean),
                  secondary_keys: [],
                  content: e.content,
                  comment: '',
                  constant: false,
                  selective: true,
                  insertion_order: 100,
                  enabled: true,
                  position: 'before_char',
                  use_regex: true,
                  extensions: {}
                }))
            : []
        }
        // 其余字段如 avatar、tags、scenario…按需补空
      };

      const blob = new Blob([JSON.stringify(card, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${memory.name}_v3.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    changeMemory() {
      if (this.memorySettings.is_memory){
        // 根据selectedMemory获取当前的memories中的对应的记忆
        let curMemory = this.memories.find(memory => memory.id === this.memorySettings.selectedMemory);
        this.firstMes = curMemory.firstMes;
        this.alternateGreetings= curMemory.alternateGreetings;
      }
      else{
        this.firstMes = '';
        this.alternateGreetings = [];
      }
      this.randomGreetings();
      this.autoSaveSettings(); // 保存设置
    },
    randomGreetings() {
      let greetings = [this.firstMes, ...this.alternateGreetings];
      // 过滤掉空字符串
      greetings = greetings.filter(greeting => greeting.trim() !== '');
      // 替换掉开场白中的所有的{{user}}为this.memorySettings.userName
      greetings = greetings.map(greeting => greeting.replace(/{{user}}/g, this.memorySettings.userName));
      // 根据selectedMemory获取当前的memories中的对应的记忆
      let curMemory = this.memories.find(memory => memory.id === this.memorySettings.selectedMemory);
      // 替换掉开场白中的所有的{{char}}为curMemory.name
      greetings = greetings.map(greeting => greeting.replace(/{{char}}/g, curMemory.name));
      if (greetings.length > 0) {
        let randomIndex = Math.floor(Math.random() * greetings.length);
        // 将随机的开场白立刻加入的this.messages中
        // 如果this.messages中第二个元素是开场白，则替换，否则在第一个元素之后插入
        if (this.messages.length > 1 && this.messages[1].role === 'assistant') {
          this.messages[1].content = greetings[randomIndex];
          this.messages[1].pure_content = greetings[randomIndex];
        } else {
          this.messages.splice(1, 0, {
            role: 'assistant',
            content: greetings[randomIndex],
            pure_content: greetings[randomIndex],
          });
        }
      } 
      else{
        // 如果this.messages中第二个元素是开场白，则移除
        if (this.messages.length > 1 && this.messages[1].role === 'assistant') {
          this.messages.splice(1, 1);
        }
      }
    },
    browseJsonFile() {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json,.png';          // 关键：多给一个 png
      input.onchange = (event) => {
        const file = event.target.files[0];
        if (!file) return;
        if (file.name.toLowerCase().endsWith('.png')) {
          this.handlePngAsJson(file);        // 新增分支
        } else {
          this.handleFileUpload(file);       // 原 JSON 分支
        }
      };
      input.click();
    },

    handleJsonDrop(event) {
      const file = event.dataTransfer.files[0];
      if (!file) return;
      const isPng = file.type === 'image/png' ||
                    file.name.toLowerCase().endsWith('.png');
      const isJson = file.type === 'application/json' ||
                    file.name.toLowerCase().endsWith('.json');

      if (isPng) {
        this.handlePngAsJson(file);
      } else if (isJson) {
        this.handleFileUpload(file);
      } else {
        showNotification('Please upload a valid JSON or PNG character card.', 'error');
      }
    },

    async handlePngAsJson(file) {
      // 1. 把 PNG 当成普通图片先上传，拿外链
      const formData = new FormData();
      formData.append('files', file);   // 字段名跟 /load_file 接口保持一致

      let imageUrl;
      try {
        const up = await fetch('/load_file', { method: 'POST', body: formData });
        if (!up.ok) throw new Error('upload failed');
        const res = await up.json();
        if (!res.success || !res.fileLinks || !res.fileLinks[0])
          throw new Error('no url returned');
        imageUrl = res.fileLinks[0].path;          // 后端返回的完整 URL
        // 可选：把这张图片也塞进 imageFiles 列表，保持界面同步
        this.imageFiles = [...this.imageFiles, ...res.imageFiles];
      } catch (e) {
        console.error(e);
        showNotification('PNG upload failed', 'error');
        return;
      }

      // 2. 拆包拿 JSON
      const jsonText = await this.extractJsonFromPng(file);
      if (!jsonText) return;   // 通知已在内部弹过

      // 3. 把 avatar 换成刚上传的 URL
      let jsonData;
      try {
        jsonData = JSON.parse(jsonText);
      } catch {
        showNotification('Invalid JSON inside PNG', 'error');
        return;
      }
      // 兼容 V2/V3
      const target = jsonData.data || jsonData;
      target.avatar = imageUrl;   // 直接覆盖

      // 4. 走现有逻辑回填表单
      this.importMemoryData(jsonData);
      this.jsonFile = file;       // 保留文件对象，方便移除按钮
      showNotification('Character card imported from PNG', 'success');
    },

    async extractJsonFromPng(file) {
      const buffer = await file.arrayBuffer();
      const png = new Uint8Array(buffer);
      const sign = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
      if (!sign.every((b, i) => b === png[i])) {
        showNotification('Not a valid PNG file', 'error');
        return null;
      }

      let pos = 8;
      const view = new DataView(buffer);
      let jsonText = null;

      while (pos < png.length) {
        const len  = view.getUint32(pos);
        const type = String.fromCharCode(...png.slice(pos + 4, pos + 8));
        const start = pos + 8;
        const end   = start + len;

        if (type === 'tEXt') {
          const data = png.slice(start, end);
          const zero = data.indexOf(0);
          if (zero > 0) {
            const key = new TextDecoder().decode(data.slice(0, zero)).toLowerCase();
            if (key === 'chara' || key === 'ccv3') {
              const b64 = new TextDecoder().decode(data.slice(zero + 1));
              try {
                jsonText = new TextDecoder().decode(
                  Uint8Array.from(atob(b64), c => c.charCodeAt(0))
                );
                if (key === 'ccv3') break;
              } catch {}
            }
          }
        }
        if (type === 'IEND') break;
        pos = end + 4; // 跳过 CRC
      }

      if (!jsonText) showNotification('No character data found in PNG', 'error');
      return jsonText;
    },


    handleFileUpload(file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const jsonData = JSON.parse(event.target.result); // 解析 JSON 数据
          this.importMemoryData(jsonData); // 调用导入方法
          this.jsonFile = file; // 保存文件信息
        } catch (error) {
          showNotification('Invalid JSON file.', 'error'); // 错误提示
        }
      };

      reader.readAsText(file); // 读取文件内容
    },

    importMemoryData(jsonData) {
      // 兼容 V2/V3：统一抽出 data
      const data = jsonData.data || jsonData;

      this.newMemory = {
        ...this.newMemory,                      // 保持 providerId 等旧字段
        name: data.name || '',
        description: data.description || '',
        avatar: data.avatar || '',
        personality: data.personality || '',
        mesExample: data.mes_example || '',
        systemPrompt: data.system_prompt || '',
        firstMes: data.first_mes || '',
        alternateGreetings: Array.isArray(data.alternate_greetings)
          ? data.alternate_greetings
          : [''],
        characterBook:
          Array.isArray(data.character_book?.entries) &&
          data.character_book.entries.length
            ? data.character_book.entries.map(e => ({
                keysRaw: (e.keys || []).join('\n'),
                content: e.content || ''
              }))
            : [{ keysRaw: '', content: '' }]
      };
    },

    removeJsonFile() {
      this.jsonFile = null; // 清空文件
    },
    // 初始化ASR WebSocket连接（修改版本，支持Web Speech API）
    async initASRWebSocket() {
      // 如果选择了Web Speech API，不需要WebSocket连接
      if (this.asrSettings.engine === 'webSpeech') {
        return;
      }
      
      const http_protocol = window.location.protocol;
      const ws_protocol = http_protocol === 'https:' ? 'wss:' : 'ws:';
      const ws_url = `${ws_protocol}//${window.location.host}/ws/asr`;

      this.asrWs = new WebSocket(ws_url);
      
      // WebSocket 打开事件
      this.asrWs.onopen = () => {
        console.log('ASR WebSocket connection established');
        // 发送初始化消息，包含当前使用的模型信息
        this.asrWs.send(JSON.stringify({
          type: 'init',
        }));
      };

      // 接收消息
      this.asrWs.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch (e) {
          console.error('Invalid JSON from ASR server:', event.data);
          return;
        }
        
        this.handleASRResult(data);
      };

      // WebSocket 关闭事件
      this.asrWs.onclose = (event) => {
        console.log('ASR WebSocket connection closed:', event.reason);
        if (this.asrSettings.enabled) {
          // 如果ASR仍处于启用状态，尝试重新连接
          setTimeout(() => this.initASRWebSocket(), 3000);
        }
      };

      // WebSocket 错误事件
      this.asrWs.onerror = (error) => {
        console.error('ASR WebSocket error:', error);
      };
    },

    // 修改：初始化Web Speech API（不自动启动）
    initWebSpeechAPI() {
      if(isElectron){
        showNotification(this.t('webSpeechNotSupportedInElectron'), 'error');
        const url = this.partyURL;
        window.electronAPI.openExternal(url);
        this.asrSettings.enabled = false;
        return false;
      }

      // 检查浏览器是否支持Web Speech API
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showNotification(this.t('webSpeechNotSupported'), 'error');
        this.asrSettings.enabled = false;
        return false;
      }

      // 创建语音识别对象
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      this.recognition = new SpeechRecognition();

      // 配置语音识别参数
      this.recognition.continuous = true; // 改为非持续识别，由VAD控制
      this.recognition.interimResults = true;
      if (this.asrSettings.webSpeechLanguage != 'auto'){
        this.recognition.lang = this.asrSettings.webSpeechLanguage;
      }
      // 识别结果处理
      this.recognition.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        // 处理中间结果
        if (interimTranscript) {
          this.handleASRResult({
            type: 'transcription',
            text: interimTranscript,
            is_final: false
          });
        }

        // 处理最终结果
        if (finalTranscript) {
          this.handleASRResult({
            type: 'transcription',
            text: finalTranscript,
            is_final: true
          });
        }
      };

      // 错误处理
      this.recognition.onerror = (event) => {
        console.error('Web Speech API error:', event.error);
        let errorMessage = null;
        
        switch (event.error) {
          case 'no-speech':
            errorMessage = null;
            break;
          case 'audio-capture':
            errorMessage = this.t('microphoneError');
            break;
          case 'not-allowed':
            errorMessage = this.t('micPermissionDenied');
            break;
          case 'network':
            errorMessage = this.t('networkError');
            break;
        }
        if (errorMessage) {
          showNotification(errorMessage, 'error');
        }
        
        // 重置识别状态
        this.isWebSpeechRecognizing = false;
      };

      // 识别结束处理
      this.recognition.onend = () => {
        console.log('Web Speech API recognition ended');
        this.isWebSpeechRecognizing = false;
        // 不再自动重启，由VAD控制
      };

      // 识别开始处理
      this.recognition.onstart = () => {
        console.log('Web Speech API recognition started');
        this.isWebSpeechRecognizing = true;
      };

      return true;
    },
    openWakeWindow() {
      this.withinWakeWindow = true;
      this.wakeWindowTimer = setTimeout(() => {
        this.withinWakeWindow = false;
      }, 30_000);
    },

    /* 刷新 30s 窗口（每次成功交互后调用） */
    resetWakeWindow() {
      clearTimeout(this.wakeWindowTimer);
      this.openWakeWindow();
    },

    /* 清理计时器，可在组件销毁时调用 */
    clearWakeWindow() {
      clearTimeout(this.wakeWindowTimer);
      this.withinWakeWindow = false;
    },

    // 修改：统一的ASR结果处理函数
    handleASRResult(data) {
      if (data.type === 'transcription') {
        const lastMessage = this.messages[this.messages.length - 1];
        if (!this.ttsSettings.enabledInterruption && this.ttsSettings.enabled) {
          // 如果TTS正在运行，并且不允许中断，则不处理ASR结果
          if(this.TTSrunning){
            if ((!lastMessage || (lastMessage?.currentChunk ?? 0) >= (lastMessage?.ttsChunks?.length ?? 0)) && !this.isTyping) {
              console.log('All audio chunks played');
              lastMessage.currentChunk = 0;
              this.TTSrunning = false;
              this.cur_audioDatas = [];
              // 通知VRM所有音频播放完成
              this.sendTTSStatusToVRM('allChunksCompleted', {});
            }
            else{
              console.log('Audio chunks still playing');
              return;
            }
          }
        }
        else if (this.ttsSettings.enabledInterruption && this.ttsSettings.enabled) {
            console.log('All audio chunks played');
            lastMessage.currentChunk = 0;
            this.TTSrunning = false;
            this.cur_audioDatas = [];
            // 通知VRM所有音频播放完成
            this.sendTTSStatusToVRM('allChunksCompleted', {});
        }
        if (data.is_final) {
          // 最终结果
          if (this.userInputBuffer.length > 0) {
            // 用data.text替换this.userInput中最后一个this.userInputBuffer
            this.userInput = this.userInput.slice(0, -this.userInputBuffer.length) + data.text;
            this.userInputBuffer = '';
          } else {
            // 如果没有临时结果，直接添加到userInput
            this.userInput += data.text;
            this.userInputBuffer = '';
          }
          
          // 根据交互方式处理
          if (this.asrSettings.interactionMethod == "auto") {
            if (this.ttsSettings.enabledInterruption) {
              this.sendMessage();
            } else if (!this.TTSrunning ||  !this.ttsSettings.enabled) {
              this.sendMessage();
            }
          }
          
          if (this.asrSettings.interactionMethod == "wakeWord") {
            const lowerInput = this.userInput.toLowerCase();
            const hasWakeWord = lowerInput.includes(this.asrSettings.wakeWord.toLowerCase());

            /* 1. 如果在 30s 免唤醒窗口，直接发送 */
            if (this.withinWakeWindow) {
              this.sendMessage();
              this.resetWakeWindow();          // 刷新 30s
              return;
            }

            /* 2. 否则必须检测唤醒词 */
            if (hasWakeWord) {
              this.sendMessage();
              this.openWakeWindow();           // 进入 30s 免唤醒
            } else {
              this.userInput = '';             // 未唤醒，清空输入
            }
          }
          
          if (this.asrSettings.interactionMethod == "wakeWordAndEndWord") {
            const userInputLower = this.userInput.toLowerCase();
            const wakeWordLower = this.asrSettings.wakeWord.toLowerCase();
            const endWordLower = this.asrSettings.endWord.toLowerCase();
            
            // 检查是否包含结束词
            if (userInputLower.includes(endWordLower)) {
              this.inAutoMode = false;
              console.log('End word detected, exiting auto mode');
              showNotification(this.t('endWordDetected'));
              // 可以选择发送包含结束词的消息，或者清空不发送
              this.userInput = '';
            }
            // 检查是否包含唤醒词
            else if (userInputLower.includes(wakeWordLower)) {
              this.inAutoMode = true;
              console.log('ake word detected, entering auto mode');
              // 发送包含唤醒词的消息
              if (this.ttsSettings.enabledInterruption) {
                this.sendMessage();
              } else if (!this.TTSrunning ||  !this.ttsSettings.enabled) {
                this.sendMessage();
              }
            }
            // 如果在自动模式下，所有消息都自动发送
            else if (this.inAutoMode) {
              if (this.ttsSettings.enabledInterruption) {
                this.sendMessage();
              } else if (!this.TTSrunning ||  !this.ttsSettings.enabled) {
                this.sendMessage();
              }
            }
            else{
              this.userInput = '';             // 未唤醒，清空输入
            }
          }
        } else {
          if (this.asrSettings.engine === 'webSpeech'){
            this.userInput = data.text;
            this.userInputBuffer = data.text;
          }else {
            // 临时结果
            this.userInput += data.text;
            this.userInputBuffer += data.text;
          }

        }
      } else if (data.type === 'error') {
        console.error('ASR error:', data.message);
        showNotification(this.t('transcriptionFailed'), 'error');
      } else if (data.type === 'init_response') {
        if (data.status === 'ready') {
          
        }
      }
    },

    // 修改：开关ASR功能
    async toggleASR() {
      this.asrSettings.enabled = !this.asrSettings.enabled;
      this.autoSaveSettings();
      
      if (this.asrSettings.enabled) {
        await this.startASR();
      } else {
        this.stopASR();
      }
    },

    // 修改：处理ASR设置变化
    async handleASRchange() {
      if (this.asrSettings.enabled) {
        await this.startASR();
      } else {
        this.stopASR();
      }
    },

    // 修改：启动ASR
    async startASR() {
      // 无论哪种模式都需要VAD
      if (this.vad == null) {
        await this.initVAD();
      }

      if (this.asrSettings.engine === 'webSpeech') {
        // 使用Web Speech API + VAD控制
        if (this.initWebSpeechAPI()) {
          // 初始化识别状态标志
          this.isWebSpeechRecognizing = false;
          
          // 开始录音和VAD检测
          await this.startRecording();
          
          showNotification(this.t('webSpeechStarted'), 'success');
        }
      } else {
        // 使用WebSocket方式
        // 初始化ASR WebSocket
        await this.initASRWebSocket();
        
        // 开始录音
        await this.startRecording();
      }
    },

    // 修改：停止ASR
    stopASR() {
      if (this.asrSettings.engine === 'webSpeech') {
        // 停止Web Speech API
        if (this.recognition && this.isWebSpeechRecognizing) {
          this.recognition.stop();
        }
        this.recognition = null;
        this.isWebSpeechRecognizing = false;
      } else {
        // 关闭ASR WebSocket
        if (this.asrWs) {
          this.asrWs.close();
          this.asrWs = null;
        }
      }
      
      // 停止录音和VAD（两种模式都需要）
      this.stopRecording();
    },


    // 修改：初始化VAD（Web Speech模式也使用VAD）
    async initVAD() {
      let min_probabilities = 0.2;
      if (this.asrSettings.engine === 'webSpeech') {
        min_probabilities = 0.7;
      }
      // 初始化VAD
      this.vad = await vad.MicVAD.new({
        preSpeechPadFrames: 10,
        onSpeechStart: () => {
          this.ASRrunning = true;
          // 语音开始时的处理
          this.handleSpeechStart();
        },
        onFrameProcessed: (probabilities, frame) => {
          // 处理每一帧
          if (probabilities["isSpeech"] > min_probabilities) {
            if (this.ttsSettings.enabledInterruption) {
              // 关闭正在播放的音频
              if (this.currentAudio) {
                this.currentAudio.pause();
                this.currentAudio = null;
                this.stopGenerate();
              }
            }
            if (!this.currentAudio || this.currentAudio.paused) {
              if (this.asrSettings.engine === 'webSpeech') {
                // Web Speech API模式：不处理音频帧，只是检测到语音
                this.handleWebSpeechFrameProcessed();
              } else {
                // WebSocket模式：处理音频帧
                this.handleFrameProcessed(frame);
              }
            }
          }
        },
        onSpeechEnd: (audio) => {
          this.ASRrunning = false;
          // 语音结束时的处理
          if (this.asrSettings.engine === 'webSpeech') {
            this.handleWebSpeechEnd();
          } else {
            this.handleSpeechEnd(audio);
          }
        },
      });
    },

    // 新增：Web Speech模式的语音开始处理
    handleWebSpeechSpeechStart() {
      console.log('VAD detected speech start for Web Speech API');
      // 如果Web Speech API没有在识别，则启动它
      if (!this.isWebSpeechRecognizing && this.recognition) {
        try {
          this.recognition.start();
        } catch (error) {
          console.error('Failed to start Web Speech API:', error);
        }
      }
    },

    // 新增：Web Speech模式的帧处理
    handleWebSpeechFrameProcessed() {
      // 在Web Speech模式下，我们不需要处理具体的音频帧
      // 只需要确保Web Speech API正在运行
      if (!this.isWebSpeechRecognizing && this.recognition) {
        try {
          this.recognition.start();
        } catch (error) {
          // 可能已经在运行中，忽略错误
          console.log('Web Speech API already running or failed to start:', error.message);
        }
      }
    },

    // 新增：Web Speech模式的语音结束处理
    handleWebSpeechEnd() {
      console.log('VAD detected speech end for Web Speech API');
      // 停止Web Speech API识别
      if (this.isWebSpeechRecognizing && this.recognition) {
        try {
          this.recognition.stop();
        } catch (error) {
          console.error('Failed to stop Web Speech API:', error);
        }
      }
    },


    // 修改：开始录音（两种模式都需要）
    async startRecording() {
      try {
        // 请求麦克风权限
        this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // 初始化音频上下文
        this.audioContext = new AudioContext();
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        
        // 设置VAD参数
        this.vad.start();
        
        this.isRecording = true;
      } catch (error) {
        console.error('Error starting recording:', error);
        this.asrSettings.enabled = false;
        showNotification(this.t('micPermissionDenied'), 'error');
      }
    },

    // 修改：停止录音（两种模式都需要）
    stopRecording() {
      if (this.vad) {
        this.vad.pause();
      }
      
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }
      
      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
      }
      
      this.isRecording = false;
    },
    // 修改：统一的语音开始处理
    async handleSpeechStart() {
      if (this.asrSettings.engine === 'webSpeech') {
        this.handleWebSpeechSpeechStart();
      } else {
        // WebSocket模式的处理
        this.currentTranscriptionId = uuid.v4();
        this.frame_buffer = [];
        this.asrWs.send(JSON.stringify({
          type: 'audio_start',
          id: this.currentTranscriptionId,
        }));
      }
    },

    async handleFrameProcessed(frame) {
      // 新增检查：确保 frame 存在且是 Float32Array
      if (!frame || !(frame instanceof Float32Array)) {
        console.error('Invalid audio frame:', frame);
        return;
      }

      if (!this.asrWs || this.asrWs.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket not ready');
        return;
      }

      try {
        // 转换和处理逻辑...
        const int16Pcm = new Int16Array(frame.length);
        for (let i = 0; i < frame.length; i++) {
          int16Pcm[i] = Math.max(-32768, Math.min(32767, frame[i] * 32767));
        }

        const base64Audio = btoa(
          String.fromCharCode(...new Uint8Array(int16Pcm.buffer))
        );

        this.asrWs.send(JSON.stringify({
          type: 'audio_stream',
          id: this.currentTranscriptionId,
          audio: base64Audio,
          format: 'pcm',
          sample_rate: 16000 // 明确采样率
        }));

      } catch (e) {
        console.error('Frame processing error:', e);
      }
    },
    async handleSpeechEnd(audio) {
      // 语音结束时的处理
      if (!this.asrWs || this.asrWs.readyState !== WebSocket.OPEN) return;
      
        // 非流式模式，发送完整音频数据
        // 将音频数据转换为WAV格式
        const wavFile = await this.audioToWav(audio);
        
        // 将WAV文件转换为base64编码
        const reader = new FileReader();
        reader.readAsDataURL(wavFile);
        reader.onloadend = () => {
          const base64data = reader.result.split(',')[1]; // 移除前缀
          
          // 发送完整音频数据
          this.asrWs.send(JSON.stringify({
            type: 'audio_complete',
            id: this.currentTranscriptionId,
            audio: base64data,
            format: 'wav'
          }));
        };
    },

    // WAV转换函数保持不变
    async audioToWav(audioData) {
      try {
        // 音频参数配置
        const sampleRate = 16000; // 采样率 16kHz，适合语音识别
        const numChannels = 1;    // 单声道
        const bitsPerSample = 16; // 16位采样深度
        
        // 将Float32Array转换为Int16Array (16位PCM)
        const int16Array = new Int16Array(audioData.length);
        for (let i = 0; i < audioData.length; i++) {
          // 将[-1.0, 1.0]范围的浮点数转换为[-32768, 32767]范围的整数
          const sample = Math.max(-1, Math.min(1, audioData[i])); // 限制范围
          int16Array[i] = sample < 0 ? sample * 32768 : sample * 32767;
        }
        
        // 计算文件大小
        const byteLength = int16Array.length * 2; // 每个样本2字节
        const buffer = new ArrayBuffer(44 + byteLength); // WAV头部44字节 + 音频数据
        const view = new DataView(buffer);
        
        // 写入WAV文件头
        const writeString = (offset, string) => {
          for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
          }
        };
        
        // RIFF chunk descriptor
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + byteLength, true); // 文件大小-8
        writeString(8, 'WAVE');
        
        // fmt sub-chunk
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true); // fmt chunk大小
        view.setUint16(20, 1, true);  // 音频格式 (PCM)
        view.setUint16(22, numChannels, true); // 声道数
        view.setUint32(24, sampleRate, true);  // 采样率
        view.setUint32(28, sampleRate * numChannels * bitsPerSample / 8, true); // 字节率
        view.setUint16(32, numChannels * bitsPerSample / 8, true); // 块对齐
        view.setUint16(34, bitsPerSample, true); // 位深度
        
        // data sub-chunk
        writeString(36, 'data');
        view.setUint32(40, byteLength, true); // 数据大小
        
        // 写入音频数据
        const offset = 44;
        for (let i = 0; i < int16Array.length; i++) {
          view.setInt16(offset + i * 2, int16Array[i], true);
        }
        
        // 创建Blob并返回File对象
        const blob = new Blob([buffer], { type: 'audio/wav' });
        const file = new File([blob], 'audio.wav', { type: 'audio/wav' });
        
        return file;
        
      } catch (error) {
        console.error('Audio conversion error:', error);
        throw new Error('Failed to convert audio to WAV format');
      }
    },

    async changeTTSstatus() {
      if (!this.ttsSettings.enabled) {
        this.TTSrunning = false;
      }
      await this.autoSaveSettings();
    },
    /**
     * 按分隔符 + <voice> 标签 拆分 buffer
     * @returns {
     *   chunks: string[]        // 纯文本块（已去标签、已清理）
     *   chunks_voice: string[]  // 与 chunks 一一对应的声音 key
     *   remaining: string       // 未完结文本
     *   remaining_voice: string // remaining 对应的 voice key
     * }
     */
    splitTTSBuffer(buffer) {
      // 0. 清理
      buffer = buffer
        // 移除标题标记（#、##、###等）
        .replace(/#{1,6}\s/gm, '')  // 匹配行首的1-6个#后跟空格
        // 移除单个Markdown格式字符（*_~`），但改为全局匹配连续出现（例如***）
        .replace(/[*_~`]+/g, '')  // 使用"+"匹配连续出现的字符
        // 移除列表项标记（如"- "或"* "）
        .replace(/^\s*[-*]\s/gm, '')
        .replace(/[\u{2600}-\u{27BF}\u{2700}-\u{27BF}\u{1F300}-\u{1F9FF}]/gu, '')   // 移除所有Unicode代理对（如表情符号）
        // 移除所有Unicode代理对（如表情符号）
        .replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, '')
        // 移除图片标记（![alt](url)）
        .replace(/!\[.*?\]\(.*?\)/g, '')
        // 移除链接标记（[text](url)）
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        // 移除首尾空格
        .trim();

      if (!buffer || buffer.trim() === '') {
        return {
          chunks: [],
          chunks_voice: [],
          remaining: '',
          remaining_voice: this.cur_voice || 'default'
        };
      }

      // 1. 还原分隔符里的转义
      const separators = (this.ttsSettings.separators || [])
        .map(s => s.replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\r/g, '\r'));

      // 2. 构造正则：确保至少有一个合法捕获组
      const voiceKeys = ['default', 'silence', ...Object.keys(this.ttsSettings.newtts || {})]
        .filter(Boolean);
      const openTagRe = new RegExp(`<(${voiceKeys.join('|')})>`, 'gi');
      const closeTagRe = /<\/\w+>/gi;
      
      // 修复分隔符正则表达式
      const sepRe = separators.length
        ? new RegExp(separators.map(s => {
            // 对正则特殊字符进行转义
            return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          }).join('|'), 'g')
        : /$^/;

      // 3. 扫描 token
      const tokens = [];
      const pushToken = (type, value, index) => tokens.push({ type, value, index });

      let m;
      openTagRe.lastIndex = 0;
      while ((m = openTagRe.exec(buffer)) !== null) pushToken('open', m[1], m.index);

      closeTagRe.lastIndex = 0;
      while ((m = closeTagRe.exec(buffer)) !== null) pushToken('close', m[0], m.index);

      sepRe.lastIndex = 0;
      while ((m = sepRe.exec(buffer)) !== null) pushToken('sep', m[0], m.index);

      tokens.sort((a, b) => a.index - b.index);

      // 4. 逐段切分
      const chunks = [];
      const chunks_voice = [];
      let currentVoice = (this.cur_voice || 'default')
      let segmentStart = 0;

      const emitText = (endIdx, voice) => {
        const text = buffer.slice(segmentStart, endIdx);
        const cleaned = text.replace(/\s+/g, ' ').trim();
        if (cleaned && !/^[\s\p{P}]*$/u.test(cleaned)) {
          chunks.push(cleaned);
          chunks_voice.push(voice);
        }
      };

      for (const tok of tokens) {
        switch (tok.type) {
          case 'open':
            emitText(tok.index, currentVoice);
            segmentStart = tok.index + `<${tok.value}>`.length;
            currentVoice = tok.value
            break;
          case 'close':
            emitText(tok.index, currentVoice);
            segmentStart = tok.index + tok.value.length;
            currentVoice = 'default';
            break;
          case 'sep':
            emitText(tok.index, currentVoice); // 修改为在分隔符之前结束
            segmentStart = tok.index + tok.value.length;
            break;
        }
      }

      // 5. 剩余
      const remaining = buffer.slice(segmentStart);
      const remaining_voice = currentVoice || this.cur_voice || 'default';

      return { chunks, chunks_voice, remaining, remaining_voice };
    },

    // TTS处理进程 - 使用流式响应
    // 修改 TTS 处理开始时的通知
    async startTTSProcess() {
      if (!this.ttsSettings.enabled) return;
      this.TTSrunning = true;
      this.cur_audioDatas = [];
      // 通知VRM准备开始TTS
      this.sendTTSStatusToVRM('ttsStarted', {
        totalChunks: this.messages[this.messages.length - 1].ttsChunks.length
      });
      
      // 现有的 TTS 处理逻辑...
      const lastMessage = this.messages[this.messages.length - 1];
      lastMessage.audioChunks = lastMessage.audioChunks || [];
      lastMessage.ttsQueue = lastMessage.ttsQueue || new Set();
      
      let max_concurrency = 1;
      let nextIndex = 0;
      while (this.TTSrunning) {
        if (nextIndex == 0){
          let remainingText = lastMessage.ttsChunks?.[0] || '';
          // 遍历this.ttsSettings.newtts，获取所有包含enabled: true的key,放到newttsList中
          let newttsList = [];
          if (remainingText && this.ttsSettings.newtts){
            for (const key in this.ttsSettings.newtts) {
              if (this.ttsSettings.newtts[key].enabled) {
                newttsList.push(key);
              }
            }
          }
          
          if (remainingText && this.ttsSettings.bufferWordList.length > 0  && newttsList == []){
            for (const exp of this.expressionMap) {
              const regex = new RegExp(exp, 'g');
              if (remainingText.includes(exp)) {
                remainingText = remainingText.replace(regex, '').trim(); // 移除表情标签
              }
            }
            // 移除HTML标签
            remainingText = remainingText.replace(/<[^>]+>/g, '');
            // 检查remainingText是否包含中文字符
            const hasChinese = /[\u4e00-\u9fa5]/.test(remainingText);

            if ((hasChinese && remainingText?.length > 5) || 
                (!hasChinese && remainingText?.length > 10)) {
                // 在lastMessage.ttsChunks开头第一个元素前插入内容
                if (this.ttsSettings.bufferWordList.length > 0) {
                    // 随机选择this.ttsSettings.bufferWordList中的一个单词
                    const bufferWord = this.ttsSettings.bufferWordList[
                        Math.floor(Math.random() * this.ttsSettings.bufferWordList.length)
                    ];
                    lastMessage.ttsChunks.unshift(bufferWord);
                }
            }
          }
        }

        max_concurrency = this.ttsSettings.maxConcurrency || 1; // 最大并发数
        while (lastMessage.ttsQueue.size < max_concurrency && 
              nextIndex < lastMessage.ttsChunks.length) {
          if (!this.TTSrunning) break;
          const index = nextIndex++;
          lastMessage.ttsQueue.add(index);
          
          this.processTTSChunk(lastMessage, index).finally(() => {
            lastMessage.ttsQueue.delete(index);
          });
          if (index == 0){
            // 结束计时并打印时间
            this.stopTimer();
            console.log(`TTS chunk 0 start in ${this.elapsedTime}ms`);
            // 延迟0.8秒，让TTS首包更快
            await new Promise(resolve => setTimeout(resolve, 800));
          }
        }
        
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      console.log('TTS queue processing completed');
    },
    startTimer() {
      this.startTime = Date.now();
    },
    stopTimer() {
      this.elapsedTime = Date.now() - this.startTime;
    },
    async processTTSChunk(message, index) {
      const chunk = message.ttsChunks[index];
      const voice = message.chunks_voice[index];
      let remainingText = chunk;
      let chunk_text = remainingText;
      let chunk_expressions = [];
      if (chunk.indexOf('<') !== -1){
        const tagReg = /<[^>]+>/g;
        chunk_expressions = (chunk.match(tagReg) || []).map(t => t.slice(1, -1)); 
        chunk_text = chunk.replace(tagReg, '').trim();
      }
      console.log(`Processing TTS chunk ${index}:`, chunk_text ,"\nvoice:" ,voice);
      
      try {
        if (voice=='silence'){
          console.log(`TTS chunk ${index} is silence`);
          message.audioChunks[index] = { 
            url: null, 
            expressions: chunk_expressions, // 添加表情
            text: chunk_text,
            index
          };
          this.cur_audioDatas[index]= null;
          this.checkAudioPlayback();
        }else{
          const response = await fetch(`/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ttsSettings: this.ttsSettings,text: chunk_text, index, voice})
          });

          if (response.ok) {
            const audioBlob = await response.blob();
            
            // 本地播放 blob URL
            const audioUrl = URL.createObjectURL(audioBlob);
            
            message.audioChunks[index] = { 
              url: audioUrl, 
              expressions: chunk_expressions, // 添加表情
              text: chunk_text,
              index 
            };
            if (index == 0){
              // 结束计时并打印时间
              this.stopTimer();
              console.log(`TTS chunk ${index} processed in ${this.elapsedTime}ms`);
            }
            // 转换为 Base64
            const base64 = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onload  = () => resolve(reader.result.split(',')[1]); // 去掉 data:*
              reader.onerror = reject;
              reader.readAsDataURL(audioBlob);
            });
            const audioDataUrl = `data:${audioBlob.type};base64,${base64}`;
            this.cur_audioDatas[index]= audioDataUrl;
            console.log(`TTS chunk ${index} processed`);
            this.checkAudioPlayback();
          } else {
            console.error(`TTS failed for chunk ${index}`);
            message.audioChunks[index] = { 
              url: null, 
              expressions: chunk_expressions, // 添加表情
              text: chunk_text,
              index
            };
            this.cur_audioDatas[index]= null;
            this.checkAudioPlayback();
          }
        }

      } catch (error) {
        console.error(`Error processing TTS chunk ${index}:`, error);
        this.TTSrunning= false;
      }
    },

    // 音频播放进程
    async startAudioPlayProcess() {
      if (!this.ttsSettings.enabled) return;
      
      const lastMessage = this.messages[this.messages.length - 1];
      lastMessage.currentChunk = lastMessage.currentChunk || 0;
      lastMessage.isPlaying = false;
      
      // 只需初始化一次
      this.audioPlayQueue = [];
      
      console.log('Audio playback monitor started');
    },

    // 修改现有的音频播放方法
    async checkAudioPlayback() {
      const lastMessage = this.messages[this.messages.length - 1];
      if (!lastMessage || lastMessage.isPlaying) return;
      if ((!lastMessage || (lastMessage?.currentChunk ?? 0) >= (lastMessage?.ttsChunks?.length ?? 0)) && !this.isTyping) {
        console.log('All audio chunks played');
          this.stopTimer();
          lastMessage.TTSelapsedTime = this.elapsedTime/1000;
        lastMessage.currentChunk = 0;
        this.TTSrunning = false;
        this.cur_audioDatas = [];
        if(this.isReadInterruption){
          setTimeout(() => {
            if (this.isReadPaused){
              this.resumeRead();
            }else{
              this.toggleContinuousPlay();
            }
          }, this.readSettings.delay);
        }
        // 通知VRM所有音频播放完成
        this.sendTTSStatusToVRM('allChunksCompleted', {});
        return;
      }
      const currentIndex = lastMessage.currentChunk;
      const audioChunk = lastMessage.audioChunks[currentIndex];
      if (!this.ttsSettings.enabled) {
        lastMessage.isPlaying = false;
        lastMessage.currentChunk = 0;
        if (this.currentAudio) {
          this.currentAudio.pause();
          this.currentAudio = null;
        }
        // 通知VRM停止说话动画
        this.sendTTSStatusToVRM('stopSpeaking', {});
        return;
      }
      
      if (audioChunk && !lastMessage.isPlaying) {
        lastMessage.isPlaying = true;
        console.log(`Playing audio chunk ${currentIndex}`);
        if (currentIndex == 0){
          this.stopTimer();
          lastMessage.first_sentence_latency = this.elapsedTime;
        }
            
        try {
          this.currentAudio = new Audio(audioChunk.url);
          this.currentAudio.volume = this.vrmOnline ? 0.0000001 : 1;
          // 发送 Base64 数据到 VRM
          this.sendTTSStatusToVRM('startSpeaking', {
            audioDataUrl: this.cur_audioDatas[currentIndex],
            chunkIndex: currentIndex,
            totalChunks: lastMessage.ttsChunks.length,
            text: audioChunk.text,
            expressions: audioChunk.expressions,
            voice: lastMessage.chunks_voice[currentIndex]
          });
          console.log(audioChunk.expressions);
          await new Promise((resolve) => {
            this.currentAudio.onended = () => {
              // 通知VRM当前chunk播放结束
              this.sendTTSStatusToVRM('chunkEnded', { 
                chunkIndex: currentIndex 
              });
              resolve();
            };
            this.currentAudio.onerror = resolve;
            this.currentAudio.play().catch(e => console.error('Play error:', e));
          });
          
          console.log(`Audio chunk ${currentIndex} finished`);
        } catch (error) {
          console.error(`Playback error: ${error}`);
        } finally {
          lastMessage.currentChunk++;
          lastMessage.isPlaying = false;
          this.stopTimer();
          lastMessage.TTSelapsedTime = this.elapsedTime / 1000; // 更新TTSelapsedTime
          setTimeout(() => {
            this.checkAudioPlayback();
          }, 0);
          this.autoSaveSettings();
        }
      }
    },
    pollVRMStatus() {
      this.vrmPollTimer = setInterval(async () => {
        try {
          const r = await fetch('/tts/status').then(r => r.json())
          this.vrmOnline = r.vrm_connections > 0
        } catch (e) {
          this.vrmOnline = false
        }
      }, 3000)
    },
    // 停止音频播放（用于停止生成时）
    stopAudioPlayback() {
      // 这里可以添加停止当前播放音频的逻辑
      const lastMessage = this.messages[this.messages.length - 1];
      if (lastMessage) {
        lastMessage.isPlaying = false;
      }
    },
    toggleTTS(message) {
      if (message.isPlaying) {
        // 如果正在播放，则暂停
        message.isPlaying = false;
        if (this.currentAudio) {
          this.currentAudio.pause();
          this.currentAudio = null;
        }
        // 发送停止说话信号到VRM
        this.sendTTSStatusToVRM('stopSpeaking', {});
      } else {
        // 如果没有播放，则开始播放，先停止其他播放
        this.stopAllAudioPlayback();
        message.isPlaying = true;
        this.playAudioChunk(message);
      }
    },
    // 停止所有正在播放的音频
    stopAllAudioPlayback() {
      // 停止当前正在播放的音频
      if (this.currentAudio) {
        this.currentAudio.pause();
        this.currentAudio = null;
      }

      // 停止阅读音频
      if (this.currentReadAudio) {
        this.currentReadAudio.pause();
        this.currentReadAudio = null;
      }

      // 停止所有消息的播放状态
      this.messages.forEach(message => {
        message.isPlaying = false;
      });

      // 发送停止信号到VRM
      this.sendTTSStatusToVRM('stopSpeaking', {});
    },

    async playAudioChunk(message) {
      if (!this.ttsSettings.enabled){
        message.isPlaying = false; // 如果没有音频块，停止播放
        message.currentChunk = 0; // 重置索引
        return;
      }

      // 初始化 cur_audioDatas 对象（如果不存在）
      if (!this.cur_audioDatas) {
        this.cur_audioDatas = {};
      }

      // 为每个消息创建唯一的键，使用消息ID
      const base64Key = `msg_${message.id}_chunk_${message.currentChunk}`;

      const audioChunk = message.audioChunks[message.currentChunk];
      if (audioChunk) {
        // 检查是否有音频URL可以播放
        if (!audioChunk.url) {
          console.log(`Audio chunk ${message.currentChunk} has no URL, skipping`);
          message.currentChunk++;
          this.playAudioChunk(message);
          return;
        }

        const audio = new Audio(audioChunk.url);
        this.currentAudio = audio; // 保存当前音频对象

        // 设置音量：VRM在线时静音，让VRM播放；不在线时正常播放
        audio.volume = this.vrmOnline ? 0.0000001 : 1;

        // 如果没有base64数据，尝试从blob URL生成
        if (!this.cur_audioDatas[base64Key] && audioChunk.url) {
          try {
            const response = await fetch(audioChunk.url);
            const blob = await response.blob();
            const base64 = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () => resolve(reader.result.split(',')[1]);
              reader.onerror = reject;
              reader.readAsDataURL(blob);
            });
            this.cur_audioDatas[base64Key] = `data:${blob.type};base64,${base64}`;
            console.log(`Generated base64 for ${base64Key}, length: ${this.cur_audioDatas[base64Key].length}`);
          } catch (error) {
            console.warn(`Failed to generate base64 for ${base64Key}:`, error);
            this.cur_audioDatas[base64Key] = '';
          }
        }

        // 发送 startSpeaking 状态到 VRM（每个块都需要发送）
        // 确保有base64数据才发送startSpeaking
        const audioDataUrl = this.cur_audioDatas[base64Key];
        if (audioDataUrl && audioDataUrl.length > 0) {
          console.log(`Sending startSpeaking with base64 data for ${base64Key}`);
          this.sendTTSStatusToVRM('startSpeaking', {
            audioDataUrl: audioDataUrl,
            chunkIndex: message.currentChunk,
            totalChunks: message.audioChunks.length,
            text: audioChunk.text || '',
            expressions: audioChunk.expressions || [],
            voice: message.chunks_voice ? message.chunks_voice[message.currentChunk] || 'default' : 'default',
          });
        } else {
          console.warn(`No base64 data available for ${base64Key}, skipping startSpeaking`);
        }

        try {
          await audio.play();
          audio.onended = () => {
            // 发送 chunkEnded 状态到 VRM
            this.sendTTSStatusToVRM('chunkEnded', {
              chunkIndex: message.currentChunk
            });

            message.currentChunk++; // 播放结束后，索引加一
            this.playAudioChunk(message); // 递归调用播放下一个音频块
          };
          audio.onerror = (error) => {
            console.error(`Error playing audio chunk ${message.currentChunk}:`, error);
            message.isPlaying = false; // 出错时停止播放
          };
        } catch (error) {
          console.error(`Error playing audio chunk ${message.currentChunk}:`, error);
          message.currentChunk++; // 播放结束后，索引加一
          this.playAudioChunk(message); // 递归调用播放下一个音频块
        }
      } else {
        message.isPlaying = false; // 如果没有音频块，停止播放
        message.currentChunk = 0; // 重置索引
        // 发送所有块播放完成状态到 VRM
        this.sendTTSStatusToVRM('allChunksCompleted', {});
      }
    },
    backwardTTS(message) {
      if (message.currentChunk > 0) {
        message.currentChunk--; // 当前索引减一
      }
    },

    forwardTTS(message) {
      if (message.currentChunk < message.audioChunks.length - 1) {
        message.currentChunk++; // 当前索引加一
      }
    },

    updateLanguages() {
      // 更新 ttsSettings 中的语言
      this.ttsSettings.edgettsLanguage = this.edgettsLanguage;
      
      // 更新性别和语音
      this.updateGenders(); 
      this.autoSaveSettings();
    },
    // 当语言改变时更新性别和语音
    updateGenders() {
      // 更新 ttsSettings 中的性别
      this.ttsSettings.edgettsGender = this.edgettsGender;
      // 更新到第一个语音
      this.ttsSettings.edgettsVoice = this.filteredVoices[0].name;

      // 更新语音
      this.updateVoices();
      this.autoSaveSettings();
    },


    // 当性别改变时更新语音
    updateVoices() {
      this.autoSaveSettings();
    },

    updateNewLanguages() {
      // 更新 ttsSettings 中的语言
      this.newTTSConfig.edgettsVoice = this.filteredNewVoices[0].name;
    },
    // 当语言改变时更新性别和语音
    updateNewGenders() {
      // 更新 ttsSettings 中的性别
      this.newTTSConfig.edgettsVoice = this.filteredNewVoices[0].name;
    },
      // 浏览参考音频文件
  browseGsvRefAudioFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'audio/*';
    input.onchange = (event) => {
      const files = event.target.files;
      if (files.length > 0) {
        this.newGsvAudio.name = files[0].name;
        this.newGsvAudio.file = files[0]; // 存储文件对象
      }
    };
    input.click();
  },
  
  // 处理参考音频拖拽
  handleGsvRefAudioDrop(event) {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      this.newGsvAudio.name = files[0].name;
      this.newGsvAudio.file = files[0]; // 存储文件对象
    }
  },
  
  // 移除已选择的参考音频
  removeNewGsvAudio() {
    this.newGsvAudio.name = '';
    this.newGsvAudio.file = null;
  },
  
  // 取消上传
  cancelGsvAudioUpload() {
    this.showGsvRefAudioPathDialog = false;
    this.newGsvAudio.name = '';
    this.newGsvAudio.text = '';
    this.newGsvAudio.file = null;
  },
  
  // 上传参考音频
  async uploadGsvAudio() {
    if (!this.newGsvAudio.file && !this.newGsvAudio.path) {
      showNotification('请先选择音频文件', 'error');
      return;
    }
    if (!this.newGsvAudio.file) {
        // 添加新音频到选项列表
        const newAudioOption = {
          path: this.newGsvAudio.path,
          name: this.newGsvAudio.name,
          text: this.newGsvAudio.text
        };
        
        this.ttsSettings.gsvAudioOptions.push(newAudioOption);
        
        // 关闭对话框并重置状态
        this.cancelGsvAudioUpload();
        
        // 自动保存设置
        await this.autoSaveSettings();
        
        showNotification('参考音频上传成功');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', this.newGsvAudio.file);
    formData.append('prompt_text', this.newGsvAudio.text);
    
    try {
      const response = await fetch(`/upload_gsv_ref_audio`, {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 添加新音频到选项列表
        const newAudioOption = {
          path: result.file.unique_filename,
          name: result.file.name,
          text: this.newGsvAudio.text
        };
        
        this.ttsSettings.gsvAudioOptions.push(newAudioOption);
        
        // 关闭对话框并重置状态
        this.cancelGsvAudioUpload();
        
        // 自动保存设置
        await this.autoSaveSettings();
        
        showNotification('参考音频上传成功');
      } else {
        showNotification(`上传失败: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('上传参考音频失败:', error);
      showNotification('上传失败，请检查网络连接', 'error');
    }
  },
  
  // 处理参考音频路径改变
  handleRefAudioPathChange(value) {
    // 当选择新的参考音频时，更新对应的提示文本
    const selectedAudio = this.ttsSettings.gsvAudioOptions.find(
      audio => audio.path === value
    );
    
    if (selectedAudio && selectedAudio.text) {
      this.ttsSettings.gsvPromptText = selectedAudio.text;
    }
    
    // 自动保存设置
    this.autoSaveSettings();
  },

    // 删除音频选项
  async deleteAudioOption(path) {
    try {
      // 查找要删除的音频选项
      const audioIndex = this.ttsSettings.gsvAudioOptions.findIndex(
        audio => audio.path === path
      );
      
      if (audioIndex === -1) return;
      if (this.ttsSettings.gsvAudioOptions[audioIndex].path == this.ttsSettings.gsvAudioOptions[audioIndex].name){
        // 为路径上传的音频，直接从选项中移除
        this.ttsSettings.gsvAudioOptions.splice(audioIndex, 1);
        showNotification('音频已删除');
        return;
      }
      // 获取文件名用于后端删除
      const uniqueFilename = this.ttsSettings.gsvAudioOptions[audioIndex].path
        .split('/')
        .pop();
      
      // 调用后端API删除文件
      const response = await fetch(`/delete_audio/${uniqueFilename}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 从选项中移除
        this.ttsSettings.gsvAudioOptions.splice(audioIndex, 1);
        
        // 如果当前选中的音频被删除，则重置选择
        if (this.ttsSettings.gsvRefAudioPath === path) {
          this.ttsSettings.gsvRefAudioPath = '';
          this.ttsSettings.gsvPromptText = '';
        }
        
        // 自动保存设置
        await this.autoSaveSettings();
        
        showNotification('音频已删除');
      } else {
        showNotification(`删除失败: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('删除音频失败:', error);
      showNotification('删除失败，请稍后再试', 'error');
    }
  },
    async startVRM() {
    if (this.isElectron) {
      this.VRMConfig.name = 'default';
      await this.autoSaveSettings();
      // Electron 环境
      try {
        this.isVRMStarting = true;
        const windowConfig = {
          width: this.VRMConfig.windowWidth,
          height: this.VRMConfig.windowHeight,
        };
        await window.electronAPI.startVRMWindow(windowConfig);
      } catch (error) {
        console.error('启动失败:', error);
      } finally {
        this.isVRMStarting = false;
      }
    } else {
      // 浏览器环境
      window.open(`${this.partyURL}/vrm.html`, '_blank');
    }
  },
    async startNewVRM(name) {
    try {
      this.isVRMStarting = true;
      this.VRMConfig.name = name;
      this.VRMConfig.selectedNewModelId = this.VRMConfig.newVRM[name].selectedModelId;
      this.VRMConfig.selectedNewMotionIds = this.VRMConfig.newVRM[name].selectedMotionIds;
      await this.autoSaveSettings();
    if (this.isElectron) {
      // Electron 环境
        const windowConfig = {
          width: this.VRMConfig.newVRM[name].windowWidth,
          height: this.VRMConfig.newVRM[name].windowHeight,
        };
        await window.electronAPI.startVRMWindow(windowConfig);
    } else {
      // 浏览器环境
      window.open(`${this.partyURL}/vrm.html`, '_blank');
    }      
  } catch (error) {
    console.error('启动失败:', error);
  } finally {
    this.isVRMStarting = false;
  }
  },
  async startVRMweb() {
    if (this.isElectron) {
      window.electronAPI.openExternal(`${this.partyURL}/vrm.html`);
    }else {
      // 浏览器环境
      window.open(`${this.partyURL}/vrm.html`, '_blank');
    }
  },
    async checkServerPort() {
      try {
        // 方式1：使用专门的方法
        const serverInfo = await window.electronAPI.getServerInfo()
        
        
        if (!serverInfo.isDefaultPort) {
          const message = `默认端口 ${serverInfo.defaultPort} 被占用，已自动切换到端口 ${serverInfo.port}`
          showNotification(message, 'warning')
        }
      } catch (error) {
        console.error('获取服务器信息失败:', error)
      }
    },
    // 初始化 WebSocket 连接
    initTTSWebSocket() {
      const http_protocol = window.location.protocol;
      const ws_protocol = http_protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${ws_protocol}//${window.location.host}/ws/tts`;
      this.ttsWebSocket = new WebSocket(wsUrl);
      
      this.ttsWebSocket.onopen = () => {
        console.log('TTS WebSocket connected');
        this.wsConnected = true;
      };
      
      this.ttsWebSocket.onclose = () => {
        console.log('TTS WebSocket disconnected');
        this.wsConnected = false;
        // 自动重连
        setTimeout(() => {
          if (!this.wsConnected) {
            this.initTTSWebSocket();
          }
        }, 3000);
      };
      
      this.ttsWebSocket.onerror = (error) => {
        console.error('TTS WebSocket error:', error);
      };
    },
    
    // 发送 TTS 状态到 VRM
    async sendTTSStatusToVRM(type, data) {
      if (this.ttsWebSocket && this.wsConnected) {
        this.ttsWebSocket.send(JSON.stringify({
          type,
          data,
          timestamp: Date.now()
        }));
      }
    },
  // 浏览VRM模型文件
  browseVrmModelFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.vrm';
    input.onchange = (event) => {
      const files = event.target.files;
      if (files.length > 0) {
        const file = files[0];
        // 检查文件扩展名
        if (!file.name.toLowerCase().endsWith('.vrm')) {
          showNotification('只支持.vrm格式的文件', 'error');
          return;
        }
        this.newVrmModel.name = file.name;
        this.newVrmModel.file = file;
        // 自动设置显示名称（去掉扩展名）
        this.newVrmModel.displayName = file.name.replace(/\.vrm$/i, '');
      }
    };
    input.click();
  },
  
  // 处理VRM模型拖拽
  handleVrmModelDrop(event) {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      // 检查文件扩展名
      if (!file.name.toLowerCase().endsWith('.vrm')) {
        showNotification('只支持.vrm格式的文件', 'error');
        return;
      }
      this.newVrmModel.name = file.name;
      this.newVrmModel.file = file;
      // 自动设置显示名称（去掉扩展名）
      this.newVrmModel.displayName = file.name.replace(/\.vrm$/i, '');
    }
  },
  
  // 移除已选择的VRM模型
  removeNewVrmModel() {
    this.newVrmModel.name = '';
    this.newVrmModel.displayName = '';
    this.newVrmModel.file = null;
  },
  
  // 取消上传
  cancelVrmModelUpload() {
    this.showVrmModelDialog = false;
    this.newVrmModel.name = '';
    this.newVrmModel.displayName = '';
    this.newVrmModel.file = null;
  },
  
  
  // 处理模型选择改变
  handleModelChange(value) {
    // 自动保存设置
    this.autoSaveSettings();
  },
  
 
    // 加载默认模型列表
  async loadDefaultModels() {
    try {
      const response = await fetch(`/get_default_vrm_models`);
      const result = await response.json();
      
      if (result.success) {
        this.VRMConfig.defaultModels = result.models;
        console.log(this.VRMConfig.defaultModels);
        // 如果没有选中任何模型，默认选择第一个默认模型
        if (!this.VRMConfig.selectedModelId && result.models.length > 0) {
          this.VRMConfig.selectedModelId = result.models[0].id;
        }
        await this.autoSaveSettings();
      }
    } catch (error) {
      console.error('加载默认模型失败:', error);
    }
  },

  // 修改上传VRM模型方法
  async uploadVrmModel() {
    if (!this.newVrmModel.file) {
      showNotification('请先选择VRM模型文件', 'error');
      return;
    }
    
    if (!this.newVrmModel.displayName.trim()) {
      showNotification('请输入模型显示名称', 'error');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', this.newVrmModel.file);
    formData.append('display_name', this.newVrmModel.displayName.trim());
    
    try {
      const response = await fetch(`/upload_vrm_model`, {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 添加新模型到用户模型列表
        const newModelOption = {
          id: result.file.unique_filename,
          name: result.file.display_name,
          path: result.file.path,
          type: 'user' // 标记为用户上传的模型
        };
        
        this.VRMConfig.userModels.push(newModelOption);
        
        // 关闭对话框并重置状态
        this.cancelVrmModelUpload();
        
        // 自动保存设置
        await this.autoSaveSettings();
        
        showNotification('VRM模型上传成功');
      } else {
        showNotification(`上传失败: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('上传VRM模型失败:', error);
      showNotification('上传失败，请检查网络连接', 'error');
    }
  },
  
  // 修改删除模型选项方法（只能删除用户上传的模型）
  async deleteModelOption(modelId) {
    try {
      // 查找要删除的模型选项（只在用户模型中查找）
      const modelIndex = this.VRMConfig.userModels.findIndex(
        model => model.id === modelId
      );
      
      if (modelIndex === -1) {
        showNotification('无法删除默认模型', 'error');
        return;
      }
      
      // 调用后端API删除文件
      const response = await fetch(`/delete_vrm_model/${modelId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 从用户模型列表中移除
        this.VRMConfig.userModels.splice(modelIndex, 1);
        
        // 如果当前选中的模型被删除，则重置为默认模型
        if (this.VRMConfig.selectedModelId === modelId) {
          if (this.VRMConfig.defaultModels.length > 0) {
            this.VRMConfig.selectedModelId = this.VRMConfig.defaultModels[0].id;
          } else {
            this.VRMConfig.selectedModelId = '';
          }
        }
        
        // 自动保存设置
        await this.autoSaveSettings();
        
        showNotification('VRM模型已删除');
      } else {
        showNotification(`删除失败: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('删除VRM模型失败:', error);
      showNotification('删除失败，请稍后再试', 'error');
    }
  },
  
  // 获取当前选中的模型信息
  getCurrentSelectedModel() {
    // 先在默认模型中查找
    let selectedModel = this.VRMConfig.defaultModels.find(
      model => model.id === this.VRMConfig.selectedModelId
    );
    
    // 如果没找到，再在用户模型中查找
    if (!selectedModel) {
      selectedModel = this.VRMConfig.userModels.find(
        model => model.id === this.VRMConfig.selectedModelId
      );
    }
    
    return selectedModel;
  },
  // 启动直播监听
  async startLive() {
    if (!this.isLiveConfigValid || this.isLiveRunning || this.isLiveStarting) {
      return;
    }

    this.isLiveStarting = true;
    
    try {
      // 发送启动请求到FastAPI后端
      const response = await fetch('/api/live/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config: this.liveConfig
        })
      });

      const result = await response.json();
      
      if (result.success) {
        this.isLiveRunning = true;
        this.shouldReconnectWs = true; // 启动时允许重连
        this.connectLiveWebSocket();
        this.startDanmuProcessor(); // 启动弹幕处理器
        showNotification(result.message || this.t('live_started_successfully'));
      } else {
        showNotification(result.message || this.t('failed_to_start_live'), 'error');
      }
    } catch (error) {
      console.error('启动直播监听失败:', error);
      showNotification(this.t('failed_to_start_live'), 'error');
    } finally {
      this.isLiveStarting = false;
    }
  },

  // 停止直播监听
  async stopLive() {
    if (!this.isLiveRunning || this.isLiveStopping) {
      return;
    }

    this.isLiveStopping = true;
    
    try {
      // 先设置状态，阻止WebSocket重连
      this.shouldReconnectWs = false;
      this.isLiveRunning = false;
      
      // 停止弹幕处理器
      this.stopDanmuProcessor();
      
      // 关闭WebSocket连接
      this.disconnectLiveWebSocket();
      
      // 发送停止请求到FastAPI后端
      const response = await fetch('/api/live/stop', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const result = await response.json();
      
      if (result.success) {
        this.danmu = []; // 清空弹幕数据
        showNotification(result.message || this.t('live_stopped_successfully'));
      } else {
        showNotification(result.message || this.t('failed_to_stop_live'), 'error');
        // 如果后端停止失败，恢复状态
        this.isLiveRunning = true;
        this.shouldReconnectWs = true;
        this.startDanmuProcessor(); // 重新启动弹幕处理器
      }
    } catch (error) {
      console.error('停止直播监听失败:', error);
      showNotification(this.t('failed_to_stop_live'), 'error');
      // 如果出错，恢复状态
      this.isLiveRunning = true;
      this.shouldReconnectWs = true;
      this.startDanmuProcessor(); // 重新启动弹幕处理器
    } finally {
      this.isLiveStopping = false;
    }
  },

  // 重载直播配置
  async reloadLiveConfig() {
    if (!this.isLiveRunning || this.isLiveReloading) {
      return;
    }

    this.isLiveReloading = true;
    
    try {
      const response = await fetch('/api/live/reload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config: this.liveConfig
        })
      });

      const result = await response.json();
      
      if (result.success) {
        // 重新连接WebSocket
        this.shouldReconnectWs = false; // 先阻止重连
        this.disconnectLiveWebSocket();
        
        setTimeout(() => {
          this.shouldReconnectWs = true; // 重新允许重连
          this.connectLiveWebSocket();
        }, 1000);
        
        showNotification(result.message || this.t('live_config_reloaded_successfully'));
      } else {
        showNotification(result.message || this.t('failed_to_reload_live_config'), 'error');
      }
    } catch (error) {
      console.error('重载直播配置失败:', error);
      showNotification(this.t('failed_to_reload_live_config'), 'error');
    } finally {
      this.isLiveReloading = false;
    }
  },

  // 启动弹幕处理器
  startDanmuProcessor() {
    console.log('启动弹幕处理器');
    
    // 如果已经有定时器在运行，先清除
    if (this.danmuProcessTimer) {
      clearInterval(this.danmuProcessTimer);
    }
    
    // 每秒检查一次弹幕队列
    this.danmuProcessTimer = setInterval(async () => {
      await this.processDanmuQueue();
    }, 1000);
  },

  // 停止弹幕处理器
  stopDanmuProcessor() {
    console.log('停止弹幕处理器');
    
    if (this.danmuProcessTimer) {
      clearInterval(this.danmuProcessTimer);
      this.danmuProcessTimer = null;
    }
    
    this.isProcessingDanmu = false;
  },

  // 处理弹幕队列
  async processDanmuQueue() {
    try {
      console.log(this.danmu);
      const lastMessage = this.messages[this.messages.length - 1];
      if(this.TTSrunning && this.ttsSettings.enabled){
        if ((!lastMessage || (lastMessage?.currentChunk ?? 0) >= (lastMessage?.ttsChunks?.length ?? 0)) && !this.isTyping) {
          console.log('All audio chunks played');
          lastMessage.currentChunk = 0;
          this.TTSrunning = false;
          this.cur_audioDatas = [];
          // 通知VRM所有音频播放完成
          this.sendTTSStatusToVRM('allChunksCompleted', {});
        }
        else{
          console.log('Audio chunks still playing');
          return;
        }
      }

      // 检查所有条件
      if (!this.isLiveRunning || 
          this.danmu.length === 0 || 
          this.isTyping || 
          (this.TTSrunning && this.ttsSettings.enabled) || 
          this.isProcessingDanmu) {
        return;
      }
      console.log('弹幕队列处理中');
      // 设置处理标志，防止并发处理
      this.isProcessingDanmu = true;
      
      // 获取最老的弹幕（队列末尾）
      const oldestDanmu = this.danmu[this.danmu.length - 1];
      
      if (oldestDanmu && oldestDanmu.content) {
        console.log('处理弹幕:', oldestDanmu.content);
        
        // 将弹幕内容赋值到用户输入
        this.userInput = oldestDanmu.content;
        
        // 发送消息
        await this.sendMessage();
        
        // 删除已处理的弹幕
        this.danmu.pop(); // 删除最后一个元素（最老的）
        
        console.log('弹幕处理完成，剩余弹幕数量:', this.danmu.length);
      }
      
    } catch (error) {
      console.error('处理弹幕时出错:', error);
    } finally {
      // 重置处理标志
      this.isProcessingDanmu = false;
    }
  },

  // 连接WebSocket
  connectLiveWebSocket() {
    try {
      // 根据当前协议选择ws或wss
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/live/danmu`;
      
      this.bilibiliWs = new WebSocket(wsUrl);
      
      this.bilibiliWs.onopen = (event) => {
        console.log('WebSocket连接已建立');
      };
      
      this.bilibiliWs.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleDanmuMessage(data);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      };
      
      this.bilibiliWs.onclose = (event) => {
        console.log('WebSocket连接已关闭');
        
        // 只有在允许重连且直播还在运行时才重连
        if (this.shouldReconnectWs && this.isLiveRunning) {
          console.log('准备重连WebSocket...');
          setTimeout(() => {
            // 再次检查状态，确保仍然需要重连
            if (this.shouldReconnectWs && this.isLiveRunning) {
              console.log('开始重连WebSocket');
              this.connectLiveWebSocket();
            } else {
              console.log('取消重连WebSocket');
            }
          }, 3000);
        } else {
          console.log('不需要重连WebSocket');
        }
      };
      
      this.bilibiliWs.onerror = (error) => {
        console.error('WebSocket连接错误:', error);
      };
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
    }
  },

  // 断开WebSocket连接
  disconnectLiveWebSocket() {
    console.log('断开WebSocket连接');
    
    if (this.bilibiliWs) {
      // 先设置为null，避免onclose事件中的重连逻辑
      const ws = this.bilibiliWs;
      this.bilibiliWs = null;
      
      // 然后关闭连接
      ws.close();
    }
  },

  async checkLiveStatus() {
    try {
      const response = await fetch('/api/live/status');
      const result = await response.json();
      
      // 更新状态
      this.isLiveRunning = result.is_running;

      // 关键点：如果后台正在运行，前端刷新后需要重新挂载 WebSocket 和处理器
      if (this.isLiveRunning) {
        console.log('检测到后台直播监听正在运行，正在恢复连接...');
        this.shouldReconnectWs = true;
        
        // 重新连接 WebSocket 接收弹幕
        this.connectLiveWebSocket();
        
        // 重新启动弹幕队列处理定时器
        this.startDanmuProcessor();
      }
    } catch (error) {
      console.error('检查直播状态失败:', error);
    }
  },

  // 处理弹幕消息
  handleDanmuMessage(data) {
    // 如果是统一的消息格式
    if (data.type === 'message') {
      const danmuItem = {
        content: data.content,
        type: data.danmu_type,
        timestamp: new Date().toLocaleTimeString('zh-CN', {
          timeZone: 'Asia/Shanghai',
          hour12: false
        })
      };
      if (this.liveConfig.onlyDanmaku){
        if (danmuItem.type === "danmaku" || danmuItem.type === "super_chat") {
          if (this.liveConfig.wakeWord){
            if (data.content.includes(this.liveConfig.wakeWord)){
              this.danmu.unshift(danmuItem);
            }
          }
          else {
            this.danmu.unshift(danmuItem);
          }
        } 
      }else {
        if (danmuItem.type === "danmaku" || danmuItem.type === "super_chat") {
          if (this.liveConfig.wakeWord){
            if (data.content.includes(this.liveConfig.wakeWord)){
              this.danmu.unshift(danmuItem);
            }
          }
          else {
            this.danmu.unshift(danmuItem);
          }
        } else{
          this.danmu.unshift(danmuItem);
        }
      }
      
      
      // 保持数组长度不超过this.liveConfig.danmakuQueueLimit
      if (this.danmu.length > this.liveConfig.danmakuQueueLimit) {
        this.danmu = this.danmu.slice(0, this.liveConfig.danmakuQueueLimit);
      }
      
      console.log('收到新弹幕:', danmuItem.content, '当前队列长度:', this.danmu.length);
      
    } else if (data.type === 'error') {
      // 处理错误消息
      showNotification(data.message, 'error');
    }
  },
  toggleBriefly(index){
    if (this.messages[index].briefly){
      this.messages[index].briefly = !this.messages[index].briefly;
    }else{
      this.messages[index].briefly = true;
    }
  },
  async rewrite(index){
    if (index != 1){
      // 删除this.messages中从index起之后的所有元素，包括index
      this.messages.splice(index);
      this.userInput = this.messages[index-1].pure_content??this.messages[index-1].content;
      // 删除this.messages中最后一个元素
      this.messages.pop();
    }else{
      // 替换开场白
      this.randomGreetings();
    }

    await this.sendMessage();
  },
  async updateProxy(){
    await this.autoSaveSettings();
    const response = await fetch('/api/update_proxy',{
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (response.ok) {
      const data = await response.json();
      console.log(data);
    }else {
      console.error('更新代理失败');
    }
  },
  async openUserfile(){
    const response = await fetch('/api/get_userfile',{
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (response.ok) {
      // 拿到userfile
      const data = await response.json();
      let userfile = data.userfile;    // 打开文件夹
      if (this.isElectron){
        window.electronAPI.openPath(userfile);
      }
    }
  },
  async openLogfile(){
    const response = await fetch('/api/get_userfile',{
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (response.ok) {
      // 拿到userfile
      const data = await response.json();
      let userfile = data.userfile;    // 打开文件夹
      if (this.isElectron){
        window.electronAPI.openPath(userfile+'/logs');
      }
    }
  },
  async openExtfile(){
    const response = await fetch('/api/get_extfile',{
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    if (response.ok) {
      // 拿到Extfile
      const data = await response.json();
      let extfile = data.extfile;    // 打开文件夹
      if (this.isElectron){
        window.electronAPI.openPath(extfile);
      }
    }
  },
  async changeHAEnabled(){
    if (this.HASettings.enabled){
      const response = await fetch('/start_HA',{
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          data: this.HASettings
        })
      });
      if (response.ok) {
        const data = await response.json();
        console.log(data);
        showNotification(this.t('success_start_HA'));
      }else {
        this.HASettings.enabled = false;
        console.error('启动HA失败');
        showNotification(this.t('error_start_HA'), 'error');
      }
    }else{
      const response = await fetch('/stop_HA',{
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      if (response.ok) {
        const data = await response.json();
        console.log(data);
        showNotification(this.t('success_stop_HA'));
      }else {
        this.HASettings.enabled = true;
        console.error('停止HA失败');
        showNotification(this.t('error_stop_HA'), 'error');
      }
    }
    this.autoSaveSettings();
  },
  async changeChromeMCPEnabled(){
    if (this.chromeMCPSettings.enabled){
      const response = await fetch('/start_ChromeMCP',{
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          data: this.chromeMCPSettings
        })
      });
      if (response.ok){
        const data = await response.json();
        console.log(data);
        showNotification(this.t('success_start_browserControl'));
      }else {
        this.chromeMCPSettings.enabled = false;
        console.error('启动ChromeMCP失败');
        showNotification(this.t('error_start_browserControl'), 'error');
      }
    }else{
      const response = await fetch('/stop_ChromeMCP',{
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
      });
      if (response.ok){
        const data = await response.json();
        console.log(data);
        showNotification(this.t('success_stop_browserControl'));
      }else {
        this.chromeMCPSettings.enabled = true;
        console.error('停止ChromeMCP失败');
        showNotification(this.t('error_stop_browserControl'), 'error');
      }
    }
    this.autoSaveSettings();
  },

  async changeSqlEnabled(){
    if (this.sqlSettings.enabled){
      const response = await fetch('/start_sql',{
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          data: this.sqlSettings
        })
      });
      if (response.ok){
        const data = await response.json();
        console.log(data);
        showNotification(this.t('success_start_sqlControl'));
      }else {
        this.sqlSettings.enabled = false;
        console.error('启动sql失败');
        showNotification(this.t('error_start_sqlControl'), 'error');
      }
    }else{
      const response = await fetch('/stop_sql',{
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
      });
      if (response.ok){
        const data = await response.json();
        console.log(data);
        showNotification(this.t('success_stop_sqlControl'));
      }else {
        this.sqlSettings.enabled = true;
        console.error('停止sql失败');
        showNotification(this.t('error_stop_sqlControl'), 'error');
      }
    }
    this.autoSaveSettings();
  },
  
    // 加载默认动作列表
  async loadDefaultMotions() {
    try {
      const response = await fetch(`/get_default_vrma_motions`);
      const result = await response.json();
      
      if (result.success) {
        this.VRMConfig.defaultMotions = result.motions;
        console.log('默认动作列表:', this.VRMConfig.defaultMotions);
        await this.autoSaveSettings();
      }
    } catch (error) {
      console.error('加载默认动作失败:', error);
    }
  },

  // 处理动作选择改变
  handleMotionChange(value) {
    console.log('选中的动作:', value);
    // 自动保存设置
    this.autoSaveSettings();
  },

  // 浏览VRMA动作文件
  browseVrmaMotionFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.vrma';
    input.multiple = true; // 允许多选
    input.onchange = (event) => {
      const files = event.target.files;
      if (files.length > 0) {
        // 如果选择了多个文件，只处理第一个（或者你可以修改为支持批量上传）
        const file = files[0];
        // 检查文件扩展名
        if (!file.name.toLowerCase().endsWith('.vrma')) {
          showNotification('只支持.vrma格式的文件', 'error');
          return;
        }
        this.newVrmaMotion.name = file.name;
        this.newVrmaMotion.file = file;
        // 自动设置显示名称（去掉扩展名）
        this.newVrmaMotion.displayName = file.name.replace(/\.vrma$/i, '');
      }
    };
    input.click();
  },

  // 处理VRMA动作拖拽
  handleVrmaMotionDrop(event) {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      // 检查文件扩展名
      if (!file.name.toLowerCase().endsWith('.vrma')) {
        showNotification('只支持.vrma格式的文件', 'error');
        return;
      }
      this.newVrmaMotion.name = file.name;
      this.newVrmaMotion.file = file;
      // 自动设置显示名称（去掉扩展名）
      this.newVrmaMotion.displayName = file.name.replace(/\.vrma$/i, '');
    }
  },

  // 移除已选择的VRMA动作
  removeNewVrmaMotion() {
    this.newVrmaMotion.name = '';
    this.newVrmaMotion.displayName = '';
    this.newVrmaMotion.file = null;
  },

  // 取消VRMA动作上传
  cancelVrmaMotionUpload() {
    this.showVrmaMotionDialog = false;
    this.newVrmaMotion.name = '';
    this.newVrmaMotion.displayName = '';
    this.newVrmaMotion.file = null;
  },

  // 上传VRMA动作
  async uploadVrmaMotion() {
    if (!this.newVrmaMotion.file) {
      showNotification('请先选择VRMA动作文件', 'error');
      return;
    }
    
    if (!this.newVrmaMotion.displayName.trim()) {
      showNotification('请输入动作显示名称', 'error');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', this.newVrmaMotion.file);
    formData.append('display_name', this.newVrmaMotion.displayName.trim());
    
    try {
      const response = await fetch(`/upload_vrma_motion`, {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 添加新动作到用户动作列表
        const newMotionOption = {
          id: result.file.unique_filename,
          name: result.file.display_name,
          path: result.file.path,
          type: 'user' // 标记为用户上传的动作
        };
        
        this.VRMConfig.userMotions.push(newMotionOption);
        
        // 自动选中新上传的动作
        if (!this.VRMConfig.selectedMotionIds.includes(newMotionOption.id)) {
          this.VRMConfig.selectedMotionIds.push(newMotionOption.id);
        }
        
        // 关闭对话框并重置状态
        this.cancelVrmaMotionUpload();
        
        // 自动保存设置
        await this.autoSaveSettings();
        
        showNotification('VRMA动作上传成功');
      } else {
        showNotification(`上传失败: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('上传VRMA动作失败:', error);
      showNotification('上传失败，请检查网络连接', 'error');
    }
  },

  // 删除动作选项（只能删除用户上传的动作）
  async deleteMotionOption(motionId) {
    try {
      // 查找要删除的动作选项（只在用户动作中查找）
      const motionIndex = this.VRMConfig.userMotions.findIndex(
        motion => motion.id === motionId
      );
      
      // 调用后端API删除文件
      const response = await fetch(`/delete_vrma_motion/${motionId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        // 从用户动作列表中移除
        this.VRMConfig.userMotions.splice(motionIndex, 1);
        
        // 如果当前选中的动作中包含被删除的动作，则从选中列表中移除
        const selectedIndex = this.VRMConfig.selectedMotionIds.indexOf(motionId);
        if (selectedIndex > -1) {
          this.VRMConfig.selectedMotionIds.splice(selectedIndex, 1);
        }
        
        // 自动保存设置
        await this.autoSaveSettings();
        
        showNotification(this.t("VRMAactionDeleted"));
      } else {
        showNotification(`error: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('删除VRMA动作失败:', error);
      showNotification(error, 'error');
    }
  },

  // 获取当前选中的动作信息
  getCurrentSelectedMotions() {
    const selectedMotions = [];
    
    // 从默认动作中查找
    this.VRMConfig.defaultMotions.forEach(motion => {
      if (this.VRMConfig.selectedMotionIds.includes(motion.id)) {
        selectedMotions.push(motion);
      }
    });
    
    // 从用户动作中查找
    this.VRMConfig.userMotions.forEach(motion => {
      if (this.VRMConfig.selectedMotionIds.includes(motion.id)) {
        selectedMotions.push(motion);
      }
    });
    
    return selectedMotions;
  },

  // 获取所有可用的动作（默认 + 用户上传）
  getAllAvailableMotions() {
    return [...this.VRMConfig.defaultMotions, ...this.VRMConfig.userMotions];
  },

  // 根据ID获取动作信息
  getMotionById(motionId) {
    // 先在默认动作中查找
    let motion = this.VRMConfig.defaultMotions.find(m => m.id === motionId);
    
    // 如果没找到，再在用户动作中查找
    if (!motion) {
      motion = this.VRMConfig.userMotions.find(m => m.id === motionId);
    }
    
    return motion;
  },

/* 生命周期：读取场景列表 */
async loadGaussScenes() {
  const [def, user] = await Promise.all([
    fetch('/get_default_gauss_scenes').then(r => r.json()),
    fetch('/get_user_gauss_scenes').then(r => r.json())
  ]);
  this.VRMConfig.gaussDefaultScenes = def.scenes || [];
  this.VRMConfig.gaussUserScenes   = user.scenes || [];
  console.log("默认场景：",this.VRMConfig.gaussDefaultScenes);
  if (!this.VRMConfig.selectedGaussSceneId) {
    this.VRMConfig.selectedGaussSceneId = 'transparent';
  }
  this.autoSaveSettings();
},
/* 选择场景后实时切换背景 */
async handleGaussSceneChange(sceneId) {
  // 与 VRM 模型切换类似：把场景 id 写进 VRMConfig
  this.VRMConfig.selectedGaussSceneId = sceneId;

  this.autoSaveSettings();
},

/* 上传区域点击 */
browseGaussSceneFile() {
  const ipt = document.createElement('input');
  ipt.type = 'file';
  ipt.accept = '.ply,.spz,.splat,.ksplat,.sog';
  ipt.onchange = e => {
    const file = e.target.files[0];
    if (file) {
      this.newGaussScene.name = file.name;
      this.newGaussScene.file = file;   // 保存原始 File 对象
      this.newGaussScene.displayName = this.newGaussScene.displayName || this.newGaussScene.name;
    }
  };
  ipt.click();
},

/* 拖拽上传 */
handleGaussSceneDrop(e) {
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['ply','spz','splat','ksplat','sog'].includes(ext)) {
    return showNotification('不支持的文件类型', 'error');
  }
  this.newGaussScene.name = file.name;
  this.newGaussScene.file = file;
  this.newGaussScene.displayName = this.newGaussScene.displayName || this.newGaussScene.name;
},

/* 移除待上传文件 */
removeNewGaussScene() {
  this.newGaussScene = { name: '', displayName: '' };
},

/* 真正上传 */
async uploadGaussScene() {
  const fd = new FormData();
  fd.append('file', this.newGaussScene.file);
  fd.append('display_name', this.newGaussScene.displayName || this.newGaussScene.name);
  console.log("上传场景：",fd);
  const res = await fetch('/upload_gauss_scene', {
    method: 'POST',
    body: fd
  }).then(r => r.json());

  if (res.success) {
    showNotification('场景上传成功');
    this.showGaussSceneDialog = false;
    // 添加新动作到用户动作列表
    const newgaussScenes = {
      id: res.file.unique_filename,
      name: res.file.display_name,
      path: res.file.path,
      type: 'user' // 标记为用户上传的动作
    };
        
    this.VRMConfig.gaussUserScenes.push(newgaussScenes);
    // 自动选中新上传的场景
    if (newgaussScenes) this.handleGaussSceneChange(newgaussScenes.id);
  } else {
    showNotification(res.message || '上传失败', 'error');
  }
},

/* 取消上传 */
cancelGaussSceneUpload() {
  this.showGaussSceneDialog = false;
  this.removeNewGaussScene();
},

/* 删除用户场景 */
async deleteGaussSceneOption(sceneId) {
  const scene = this.VRMConfig.gaussUserScenes.find(s => s.id === sceneId);
  if (!scene) return;

  // 提取 uuid 文件名
  const filename = scene.path.split('/').pop();
  const res = await fetch(`/delete_gauss_scene/${filename}`, {
    method: 'DELETE'
  }).then(r => r.json());

  if (res.success) {
    showNotification('场景已删除');
    // 如果当前正在使用被删场景，切回第一个默认场景
    if (this.VRMConfig.selectedGaussSceneId === sceneId) {
      const firstDef = this.VRMConfig.gaussDefaultScenes[0];
      if (firstDef) this.handleGaussSceneChange(firstDef.id);
    }
    await this.loadGaussScenes();
  } else {
    showNotification(res.message || '删除失败', 'error');
  }
},


  async confirmClearAll() {
    try {
      await this.$confirm(this.t('confirmClearAllHistory'), this.t('warning'), {
        confirmButtonText: this.t('confirm'),
        cancelButtonText: this.t('cancel'),
        type: 'warning'
      });
      
      this.conversations = [];
      this.conversationId = null;
      await this.saveConversations();
    } catch (error) {
      // 用户取消操作
    }
  },

  async keepLastWeek() {
    try {
      await this.$confirm(this.t('confirmKeepLastWeek'), this.t('warning'), {
        confirmButtonText: this.t('confirm'),
        cancelButtonText: this.t('cancel'),
        type: 'warning'
      });

      const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
      this.conversations = this.conversations.filter(conv => 
        conv.timestamp && conv.timestamp >= oneWeekAgo
      );
      if (this.conversations == []){
        this.conversationId = null; // 清空当前对话ID
      }
      
      await this.saveConversations();
    } catch (error) {
      // 用户取消操作
    }
  },
  changeGsvAudioPath() {
    if (this.newGsvAudio.path) {
      this.newGsvAudio.name = this.newGsvAudio.path;
    }
  },
    /* ===============  朗读主流程  =============== */
toggleRead() {
  if (this.isReadRunning) {
    if (this.isReadPaused) {
      this.resumeRead();
    } else {
      this.pauseRead();
    }
  } else {
    this.startRead();
  }
},

// 修改后的startRead方法
async startRead() {
  if (!this.readConfig.longText.trim()) return;
  
  this.stopSegmentTTS();
  this.readState.currentChunk = 0;
  this.isReadStarting = true;
  this.isReadRunning  = true;
  this.isReadPaused   = false;  // 重置暂停状态
  this.isReadStopping = false;

  /* 清空上一次的残留 */
  this.readState.ttsChunks  = [];
  this.readState.audioChunks = [];
  this.readState.currentChunk = 0;
  this.readState.isPlaying = false;
  this.readState.chunks_voice = [];
  this.cur_voice = 'default';
  
  /* 重置音频计数状态 */
  this.audioChunksCount = 0;
  this.totalChunksCount = 0;

  /* 分段处理逻辑（保持原有） */
  const {
    chunks,
    chunks_voice,
    remaining,
    remaining_voice
  } = this.splitTTSBuffer(this.readConfig.longText);

  if (remaining) {
    chunks.push(remaining);
    chunks_voice.push(remaining_voice);
  }

  /* 去标签 + 去空白并同步删除 */
  const cleanedChunks = chunks.map(txt => txt.replace(/<\/?[^>]+>/g, '').trim());
  const finalChunks = [];
  const finalChunksVoice = [];

  cleanedChunks.forEach((txt, idx) => {
    if (txt) {
      finalChunks.push(txt);
      finalChunksVoice.push(chunks_voice[idx]);
    }
  });

  if (!finalChunks.length) {
    this.isReadRunning  = false;
    this.isReadStarting = false;
    return;
  }

  this.readState.ttsChunks   = finalChunks;
  this.readState.chunks_voice = finalChunksVoice;
  this.totalChunksCount = finalChunks.length;

  /* 通知 VRM 开始朗读 */
  this.sendTTSStatusToVRM('ttsStarted', {
    totalChunks: this.readState.ttsChunks.length
  });

  this.isReadStarting = false;

  /* 并发 TTS */
  this.isAudioSynthesizing = true;
  await this.startReadTTSProcess();
},

// 新增：暂停朗读
pauseRead() {
  if (!this.isReadRunning || this.isReadPaused) return;
  
  this.isReadPaused = true;
  
  // 暂停当前音频
  if (this.currentReadAudio) {
    this.currentReadAudio.pause();
  }
  
  // 通知 VRM 暂停
  this.sendTTSStatusToVRM('pauseSpeaking', {});
},

// 新增：恢复朗读
resumeRead() {
  if (!this.isReadRunning || !this.isReadPaused) return;
  
  this.isReadPaused = false;
  
  // 恢复当前音频播放
  if (this.currentReadAudio) {
    this.currentReadAudio.play().catch(console.error);
  }
  
  // 通知 VRM 恢复
  this.sendTTSStatusToVRM('resumeSpeaking', {});
  
  // 尝试继续播放后续音频
  this.checkReadAudioPlayback();
},

    // 修改 processReadTTSChunk 方法
    async processReadTTSChunk(index) {
      try {
        const chunk = this.readState.ttsChunks[index];
        const voice = this.readState.chunks_voice[index];
        const cachedAudio = this.readState.audioChunks[index];

        // 检查缓存是否命中
        if (cachedAudio?.url && cachedAudio?.base64 && cachedAudio?.text === chunk && cachedAudio?.voice === voice) {
          this.cur_audioDatas[index] = cachedAudio.base64;
        }
        else{
          /* —— 与对话版完全一致的文本清洗 —— */
          let chunk_text = chunk;
          let  chunk_expressions = [];
          if (chunk.indexOf('<') !== -1) {
              const tagReg = /<[^>]+>/g;
              chunk_expressions = (chunk.match(tagReg) || []).map(t => t.slice(1, -1)); // 去掉两端的 <>
              chunk_text = chunk.replace(tagReg, '').trim();
          }

          const res = await fetch('/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ttsSettings: this.ttsSettings,
              text: chunk_text,
              index,
              voice
            })
          });

          if (!res.ok) throw new Error('TTS failed');

          const blob = await res.blob();
          const url  = URL.createObjectURL(blob);

          /* Base64 给 VRM */
          const base64 = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload  = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
          });
          this.cur_audioDatas[index] = `data:${blob.type};base64,${base64}`;
          /* 缓存两样东西 */
          this.readState.audioChunks[index] = {
            url,                       // 本地播放用
            expressions: chunk_expressions,
            base64: this.cur_audioDatas[index], // VRM 播放用
            text: chunk_text,
            index,
            voice
          };
        }

        /* 新增: 增加已生成片段计数 */
        this.audioChunksCount++;
        
        /* 新增: 检查是否全部合成完成 */
        if (this.audioChunksCount >= this.totalChunksCount) {
          this.isAudioSynthesizing = false;
          this.audioChunksCount = this.totalChunksCount; // 重置计数
        }

        /* 立刻尝试播放 */
        this.checkReadAudioPlayback();
      } catch (e) {
        console.error(`Read TTS chunk ${index} error`, e);
        this.readState.audioChunks[index] = { url: null, expressions: chunk_expressions, text: chunk_text, index };
        this.cur_audioDatas[index] = null;
        
        /* 新增: 处理错误时也增加计数 */
        this.audioChunksCount++;
        
        /* 新增: 检查是否全部合成完成 */
        if (this.audioChunksCount >= this.totalChunksCount) {
          this.isAudioSynthesizing = false;
          this.audioChunksCount = this.totalChunksCount; // 重置计数
        }
        
        this.checkReadAudioPlayback();
      }
    },

    async ClickToListen(SampleText,voice='default') {
      if (!SampleText) {
        SampleText ='super agent party链接一切！'
      }

    try {
      // 创建副本，避免直接修改 this.ttsSettings
      let Settings = { ...this.ttsSettings };

      if (this.showAddTTSDialog) {
        Settings = { ...Settings, ...this.newTTSConfig };
      } else if (voice !== 'default' && this.ttsSettings.newtts && this.ttsSettings.newtts[voice]) {
        // 从角色语音卡片调用：合并角色配置
        Settings = { ...Settings, ...this.ttsSettings.newtts[voice] };
      }

      // ★ 关键修复：附带 modelProviders，供后端查找 API Key
      // 后端逻辑：如果角色配置缺少api_key但有selectedProvider，会从这里查找
      if (this.modelProviders && Array.isArray(this.modelProviders)) {
        Settings.modelProviders = this.modelProviders;
      }

        const res = await fetch('/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ttsSettings: Settings,
            text: SampleText,
            index: 0,          // 随便给个 index，后端不关心
            voice: voice || 'default'
          })
        });
        if (!res.ok) throw new Error('TTS failed');

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        /* 直接播放 */
        const audio = new Audio(url);
        audio.play().catch(console.error);

        /* 播放完清掉内存 */
        audio.onended = () => URL.revokeObjectURL(url);
      } catch (e) {
        console.error('ClickToListen error', e);
      }
    },

    // 添加下载方法
    downloadAudio() {
      // 确保有音频片段可以下载
      if (this.audioChunksCount === 0) {
        showNotification(this.t('noAudioToDownload'));
        return;
      }

      // 检查是否有有效的音频片段
      const validChunks = this.readState.audioChunks.filter(chunk => chunk && chunk.url);
      if (validChunks.length === 0) {
        showNotification(this.t('noValidAudioChunks'));
        return;
      }

      try {
        // 创建合并的音频文件，只包含有效的片段
        this.createCombinedAudio(validChunks, this.getAudioMimeType());
      } catch (error) {
        console.error('Audio download failed:', error);
        showNotification(this.t('audioDownloadFailed'));
      }
    },



    // 1. 修改 downloadAudio：不再需要传入 MIME 类型，交给内部探测
    downloadAudio() {
      if (this.audioChunksCount === 0) {
        showNotification(this.t('noAudioToDownload'));
        return;
      }

      // 过滤无效片段
      const validChunks = this.readState.audioChunks.filter(chunk => chunk && chunk.url);
      if (validChunks.length === 0) {
        showNotification(this.t('noValidAudioChunks'));
        return;
      }

      try {
        // 直接调用，不需要传参，函数内部会自己识别格式
        this.createCombinedAudio(validChunks);
      } catch (error) {
        console.error('Audio download failed:', error);
        showNotification(this.t('audioDownloadFailed'));
      }
    },

    // 2. 重写 createCombinedAudio：核心修改是“自动识别真实格式”
    async createCombinedAudio(chunks) {
      if (!chunks || chunks.length === 0) return;

      showNotification(this.t('audioProcessingStarted') || '正在处理音频...');

      try {
        // ================= 关键步骤：探测真实格式 =================
        // 先 Fetch 第一个片段，查看 HTTP 头或 Blob 类型，以此为准
        const firstResponse = await fetch(chunks[0].url);
        const firstBlob = await firstResponse.blob();
        
        // 获取真实的 MIME (例如: "audio/ogg; codecs=opus" -> "audio/ogg")
        const realMimeType = firstBlob.type.split(';')[0]; 
        
        console.log('Detected Real Audio Format:', realMimeType);

        // 根据真实 MIME 推导后缀名和处理逻辑
        let extension = 'mp3'; // 默认
        let isWav = false;

        if (realMimeType.includes('wav')) {
          extension = 'wav';
          isWav = true;
        } else if (realMimeType.includes('ogg')) {
          extension = 'ogg';
        } else if (realMimeType.includes('aac')) {
          extension = 'aac';
        } else if (realMimeType.includes('flac')) {
          extension = 'flac';
        } else if (realMimeType.includes('webm')) {
          extension = 'webm';
        } else if (realMimeType.includes('mp4') || realMimeType.includes('m4a')) {
          extension = 'm4a';
        }

        // ================= 开始获取所有数据 =================
        // 重用第一个 Blob，减少一次请求
        const firstBuffer = await firstBlob.arrayBuffer();
        
        // 并发获取剩余片段
        const restPromises = chunks.slice(1).map(async (chunk) => {
          const response = await fetch(chunk.url);
          return response.arrayBuffer();
        });
        
        const restBuffers = await Promise.all(restPromises);
        const allBuffers = [firstBuffer, ...restBuffers];

        // ================= 根据真实格式合并 =================
        let combinedBuffer;

        if (isWav) {
          // WAV 专用处理：去头
          combinedBuffer = this.mergeWavBuffers(allBuffers);
        } else {
          // 其他格式（MP3, OGG等）：直接拼接
          // 注意：OGG 直接拼接在浏览器中播放可能只能听第一句（Chained Ogg），
          // 但下载后用本地播放器（VLC/PotPlayer）是完整的。这是无损拼接的特性。
          combinedBuffer = this.mergeGeneralBuffers(allBuffers);
        }

        // ================= 下载文件 =================
        const blob = new Blob([combinedBuffer], { type: realMimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        
        a.href = url;
        // 使用探测到的真实后缀名
        a.download = `tts-merged-${timestamp}.${extension}`; 
        
        document.body.appendChild(a);
        a.click();
        
        // 清理
        setTimeout(() => {
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }, 100);
        
        showNotification(this.t('audioDownloadStarted'));

      } catch (error) {
        console.error('Audio merging failed:', error);
        showNotification(this.t('audioMergeFailed'));
      }
    },

    // --- 辅助函数保持不变 ---
    
    // 通用拼接 (MP3/OGG/AAC)
    mergeGeneralBuffers(buffers) {
      const totalLength = buffers.reduce((acc, buffer) => acc + buffer.byteLength, 0);
      const result = new Uint8Array(totalLength);
      
      let offset = 0;
      buffers.forEach(buffer => {
        result.set(new Uint8Array(buffer), offset);
        offset += buffer.byteLength;
      });
      
      return result;
    },

    // WAV 专用拼接
    mergeWavBuffers(buffers) {
      if (buffers.length === 0) return new Uint8Array(0);
      if (buffers.length === 1) return new Uint8Array(buffers[0]);

      const HEADER_SIZE = 44; 
      let totalDataLength = 0;
      
      buffers.forEach((buffer, index) => {
        if (index === 0) totalDataLength += buffer.byteLength;
        else totalDataLength += Math.max(0, buffer.byteLength - HEADER_SIZE);
      });

      const result = new Uint8Array(totalDataLength);
      
      // 写入第一个文件（含头）
      result.set(new Uint8Array(buffers[0]), 0);
      let offset = buffers[0].byteLength;

      // 写入后续文件（去头）
      for (let i = 1; i < buffers.length; i++) {
        const buffer = new Uint8Array(buffers[i]);
        if (buffer.byteLength > HEADER_SIZE) {
            const dataChunk = buffer.subarray(HEADER_SIZE);
            result.set(dataChunk, offset);
            offset += dataChunk.byteLength;
        }
      }

      // 修正 WAV 头
      const view = new DataView(result.buffer);
      view.setUint32(4, result.byteLength - 8, true); 
      view.setUint32(40, result.byteLength - HEADER_SIZE, true);

      return result;
    },


// 修改 stopRead 方法
stopRead() {
  if (!this.isReadRunning) return;
  
  this.isReadStopping = true;
  this.isReadRunning  = false;
  this.isReadPaused   = false;  // 重置暂停状态
  this.readState.isPlaying = false;

  /* 停掉当前音频 */
  if (this.currentReadAudio) {
    this.currentReadAudio.pause();
    this.currentReadAudio = null;
  }
  
  this.sendTTSStatusToVRM('stopSpeaking', {});
  
  /* 重置音频计数状态 */
  this.isAudioSynthesizing = false;
  this.audioChunksCount = 0;
  this.totalChunksCount = 0;
  
  this.isReadStopping = false;
},

// 修改 stopTTSActivities 方法
stopTTSActivities() {
  // 停止朗读流程
  if (this.isReadRunning) {
    this.isReadStopping = true;
    this.isReadRunning = false;
    this.isReadPaused = false;  // 重置暂停状态
    this.readState.isPlaying = false;
    
    /* 停掉当前音频 */
    if (this.currentReadAudio) {
      this.currentReadAudio.pause();
      this.currentReadAudio = null;
    }
    this.sendTTSStatusToVRM('stopSpeaking', {});
    
    /* 重置音频计数状态 */
    this.isAudioSynthesizing = false;
    
    this.isReadStopping = false;
  }
  
  // 停止音频转换流程（保持原有）
  if (this.isConvertingAudio) {
    this.isConvertStopping = true;
    this.isConvertingAudio = false;
    this.isAudioSynthesizing = false;
    showNotification(this.t('audioConversionStopped'));
    this.isConvertStopping = false;
  }
},
  /* ===============  复用 / 微调 TTS 流程  =============== */
  async startReadTTSProcess() {
    let max_concurrency = this.ttsSettings.maxConcurrency || 1;
    let nextIndex = 0;

    /* 与对话版唯一区别：readState 代替 messages[last] */
    while (this.isReadRunning) {
      while (
        this.readState.ttsQueue.size < max_concurrency &&
        nextIndex < this.readState.ttsChunks.length
      ) {
        if (!this.isReadRunning) break;

        const index = nextIndex++;
        this.readState.ttsQueue.add(index);

        this.processReadTTSChunk(index).finally(() => {
          this.readState.ttsQueue.delete(index);
        });

        /* 首包加速 */
        if (index === 0) await new Promise(r => setTimeout(r, 800));
      }
      await new Promise(r => setTimeout(r, 10));
    }
    console.log('Read TTS queue processing completed');
  },

  // 修改后的 convertAudioOnly 方法
  async convertAudioOnly() {
    if (!this.readConfig.longText.trim()) {
      showNotification(this.t('noTextToConvert'));
      return;
    }

    this.isConvertingAudio = true;
    
    try {
      // 1. 清空上一次的残留
      this.readState.ttsChunks = [];
      this.readState.audioChunks = [];
      this.readState.chunks_voice = [];
      this.audioChunksCount = 0;
      this.totalChunksCount = 0;

  /* 2. 分段 */
      const {
        chunks,
        chunks_voice,
        remaining,
        remaining_voice
      } = this.splitTTSBuffer(this.readConfig.longText);

      // 追加 remaining
      if (remaining) {
        chunks.push(remaining);
        chunks_voice.push(remaining_voice);
      }

      /* ================= 新增：去标签 + 去空白并同步删除 ================= */
      // 1. 去 HTML 标签
      const cleanedChunks = chunks.map(txt => txt.replace(/<\/?[^>]+>/g, '').trim());

      // 2. 过滤空白并同步删除 chunks_voice 对应项
      const finalChunks       = [];
      const finalChunksVoice  = [];

      cleanedChunks.forEach((txt, idx) => {
        if (txt) {                      // 非空才保留
          finalChunks.push(txt);
          finalChunksVoice.push(chunks_voice[idx]);
        }
      });

      // 3. 覆盖原来的数组
      chunks.length       = 0;
      chunks_voice.length = 0;
      chunks.push(...finalChunks);
      chunks_voice.push(...finalChunksVoice);
      /* ================================================================ */
      
      if (!chunks.length) {
        this.isConvertingAudio = false;
        return;
      }
      
      this.readState.ttsChunks = chunks;
      this.readState.chunks_voice = chunks_voice;
      this.totalChunksCount = chunks.length;

      // 3. 开始转换（复用 processReadTTSChunk 但禁用播放）
      this.isAudioSynthesizing = true;
      
      // 使用并发控制处理所有片段
      const maxConcurrency = this.ttsSettings.maxConcurrency || 1;
      let nextIndex = 0;
      const activeTasks = new Set();
      
      // 使用 Promise 来等待所有任务完成
      await new Promise((resolve) => {
        const processNext = async () => {
          // 检查是否被用户停止
          if (!this.isConvertingAudio) {
            resolve();
            return;
          }
          
          // 所有任务完成
          if (nextIndex >= chunks.length && activeTasks.size === 0) {
            resolve();
            return;
          }
          
          // 添加新任务（如果有空位且还有任务）
          while (activeTasks.size < maxConcurrency && nextIndex < chunks.length) {
            const index = nextIndex++;
            activeTasks.add(index);
            
            this.processTTSChunkWithoutPlayback(index)
              .finally(() => {
                activeTasks.delete(index);
                processNext(); // 检查是否可添加新任务
              });
          }
        };
        
        processNext();
      });
      
      // 只有在没有被停止的情况下才显示完成通知
      if (this.isConvertingAudio) {
        this.isAudioSynthesizing = false;
        showNotification(this.t('audioConversionCompleted', { count: chunks.length }));
      }
      
    } catch (error) {
      console.error('Audio conversion failed:', error);
      showNotification(this.t('audioConversionFailed'));
    } finally {
      this.isConvertingAudio = false;
    }
  },

    // 处理TTS片段但不播放
    async processTTSChunkWithoutPlayback(index) {
      const chunk = this.readState.ttsChunks[index];
      const voice = this.readState.chunks_voice[index];
      console.log(`Processing TTS chunk ${index}`);
      // 文本清洗
      let chunk_text = chunk;
      let chunk_expressions =[];
      if (chunk.indexOf('<') !== -1) {
        const tagReg = /<[^>]+>/g;
        chunk_expressions = (chunk.match(tagReg) || []).map(t => t.slice(1, -1)); // 去掉两端的 <>
        chunk_text = chunk.replace(tagReg, '').trim(); // 把标签从正文里删掉
      }

      try {
        const res = await fetch('/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ttsSettings: this.ttsSettings,
            text: chunk_text,
            index,
            voice
          })
        });

        if (!res.ok) throw new Error('TTS failed');

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        /* Base64 给 VRM */
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload  = () => resolve(reader.result.split(',')[1]);
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        this.cur_audioDatas[index] = `data:${blob.type};base64,${base64}`;
        /* 缓存两样东西 */
        this.readState.audioChunks[index] = {
          url,                       // 本地播放用
          expressions: chunk_expressions,
          base64: this.cur_audioDatas[index], // VRM 播放用
          text: chunk_text,
          index,
          voice
        };
        // 增加计数
        this.audioChunksCount++;
        if (this.audioChunksCount >= this.totalChunksCount) {
          this.isAudioSynthesizing = false;
          this.audioChunksCount = this.totalChunksCount; // 重置计数
        }
      } catch (e) {
        console.error(`TTS chunk ${index} error`, e);
        this.readState.audioChunks[index] = { 
          url: null, 
          expressions: chunk_expressions, 
          text: chunk_text, 
          index 
        };
        
        // 错误时也增加计数
        this.audioChunksCount++;
        if (this.audioChunksCount >= this.totalChunksCount) {
          this.isAudioSynthesizing = false;
          this.audioChunksCount = this.totalChunksCount; // 重置计数
        }
      }
    },

  /* ===============  播放监控  =============== */
  async startReadAudioPlayProcess() {
    /* 与对话版的 startAudioPlayProcess 完全一致，只是把 readState 替换掉 */
    this.readState.currentChunk = 0;
    this.readState.isPlaying   = false;
    this.audioPlayQueue = [];
  },

  async checkReadAudioPlayback() {
    if (this.isReadPaused) return;
    if (!this.isReadRunning || this.readState.isPlaying) return;

    const curIdx = this.readState.currentChunk;
    const total  = this.readState.ttsChunks.length;
    if (curIdx >= total) {
      /* 全部读完 */
      console.log('All read audio chunks played');
      this.readState.currentChunk = 0;
      this.isReadRunning = false;
      this.cur_audioDatas = [];
      this.sendTTSStatusToVRM('allChunksCompleted', {});
      return;
    }

    const audioChunk = this.readState.audioChunks[curIdx];
    if (!audioChunk) return;

    /* 开始播放这一块 */
    this.readState.isPlaying = true;
    console.log(`Playing read audio chunk ${curIdx}`);
    this.scrollToCurrentChunk(curIdx);
    try {
      this.currentReadAudio = new Audio(audioChunk.url);
      this.currentReadAudio.volume = this.vrmOnline ? 0.0000001 : 1; // VRM在线时静音
      this.sendTTSStatusToVRM('startSpeaking', {
        audioDataUrl: this.cur_audioDatas[curIdx],
        chunkIndex: curIdx,
        totalChunks: total,
        text: audioChunk.text,
        expressions: audioChunk.expressions,
        voice: this.readState.chunks_voice[curIdx]
      });

      await new Promise(resolve => {
        this.currentReadAudio.onended = () => {
          this.sendTTSStatusToVRM('chunkEnded', { chunkIndex: curIdx });
          resolve();
        };
        this.currentReadAudio.onerror = resolve;
        this.currentReadAudio.play().catch(console.error);
      });
    } catch (e) {
      console.error('Read playback error', e);
    } finally {
      this.readState.currentChunk++;
      this.readState.isPlaying = false;
      setTimeout(() => this.checkReadAudioPlayback(), 0);
    }
  },
    async parseSelectedFile() {
        this.readConfig.longText = '';
        this.readConfig.longTextList = [];
        this.longTextListIndex = 0;
        // 根据选择的文件unique_filename在textFiles中查找对应的文件信息
        const selectedFile = this.textFiles.find(file => file.unique_filename === this.selectedFile);
        try {
          if (selectedFile) {
            // 构建完整的请求URL
            const url = `/get_file_content?file_url=${selectedFile.unique_filename}`;
            
            // 发送请求获取文件内容
            const response = await fetch(url, {
              method: 'GET',
              headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            if (selectedFile.unique_filename.toLowerCase().endsWith('.epub')){
              // data.content转成字典
              let data_json = JSON.parse(data.content);
              this.readConfig.longTextList = data_json.chapters || [];
              if (this.readConfig.longTextList.length > 0){
                this.longTextListIndex = 0;
                this.readConfig.longText = this.readConfig.longTextList[0];
              }else{
                this.readConfig.longText = data.content;
              }
            }else{
              this.readConfig.longText = data.content;
            }
            // 如果this.readConfig.longText太长了，就只取前100000个
            // if (this.readConfig.longText.length > 100000) {
            //   this.readConfig.longText = this.readConfig.longText.substring(0, 100000);
            //   showNotification(this.t('contentTooLong'))
            // }
          }
        }
        catch (error) {
          console.error('Error:', error);
        }
    },
  NextPage() {
    if (this.longTextListIndex < this.readConfig.longTextList.length - 1) {
      this.longTextListIndex++;
      this.readConfig.longText = this.readConfig.longTextList[this.longTextListIndex];
    }
  },
  PrevPage() {
    if (this.longTextListIndex > 0) {
      this.longTextListIndex--;
      this.readConfig.longText = this.readConfig.longTextList[this.longTextListIndex];
    }
  },
  openAddTTSDialog() {
    this.newTTSConfig = {
      name: '',
      enabled: true,
      SampleText: 'super agent party链接一切！',
      engine: 'edgetts',
      edgettsLanguage: 'zh-CN',
      edgettsGender: 'Female',
      edgettsVoice: 'XiaoyiNeural',
      edgettsRate: 1.0,
      gsvServer: "http://127.0.0.1:9880",
      gsvTextLang: 'zh',
      gsvRate: 1.0,
      gsvPromptLang: 'zh',
      gsvPromptText: '',
      gsvRefAudioPath: '',
      gsvAudioOptions: [],
      selectedProvider: null,
      vendor: "OpenAI",
      model: "",
      base_url: "",
      api_key: "",
      openaiVoice:"alloy",
      openaiSpeed: 1.0,
      customTTSserver: "http://127.0.0.1:9880",
      customTTSspeaker: "",
      customTTSspeed: 1.0,
    };
    this.showAddTTSDialog = true;
  },

  saveNewTTSConfig() {
    const name = this.newTTSConfig.name;
    if (!name) return;

    this.ttsSettings.newtts[name] = { ...this.newTTSConfig };
    this.showAddTTSDialog = false;
    this.autoSaveSettings();
  },

  deleteTTS(name) {
    delete this.ttsSettings.newtts[name];
  },

  editTTS(name) {
    this.newTTSConfig = { ...this.ttsSettings.newtts[name] };
    this.showAddTTSDialog = true;
  },

  openAddAppearanceDialog() {
    this.newAppearanceConfig = {
      name: '',
      windowWidth: 540,
      windowHeight: 960,
      selectedModelId: 'alice', // 默认选择Alice模型
      selectedMotionIds: [],
    };
    this.showAddAppearanceDialog = true;
  },
  editAppearance(name) {
    this.newAppearanceConfig = { ...this.VRMConfig.newVRM[name] };
    this.showAddAppearanceDialog = true;
  },
  deleteAppearance(name) {
    delete this.VRMConfig.newVRM[name];
  },
  saveNewAppearanceConfig() {
    const name = this.newAppearanceConfig.name;
    if (!name) return;

    this.VRMConfig.newVRM[name] = { ...this.newAppearanceConfig };
    this.showAddAppearanceDialog = false;
    this.autoSaveSettings();
  },
  addBehavior() {
    // 深拷贝一份默认模板
    this.behaviorSettings.behaviorList.push(JSON.parse(JSON.stringify(this.newBehavior)));
    this.autoSaveSettings();
  },
  removeBehavior(idx) {
    this.behaviorSettings.behaviorList[idx].enabled = false;
    this.behaviorSettings.behaviorList.splice(idx, 1);
    showNotification(this.t('deleteBehaviorSuccess'))
    this.autoSaveSettings();
  },
  resetBehavior(idx) {
    this.behaviorSettings.behaviorList[idx] = JSON.parse(JSON.stringify(this.newBehavior));
    this.autoSaveSettings();
  },
  removeAllBehavior() {
    this.behaviorSettings.behaviorList.forEach((b) => {
      b.enabled = false;
    });
    this.behaviorSettings.behaviorList = [];
    showNotification(this.t('deleteAllBehaviorSuccess'))
    this.autoSaveSettings();
  },
    /* 真正执行行为 */
    runBehavior(b) {
      if (!b.enabled) return
      if (!this.noInputFlag){
        this.stopGenerate()
      }
      if (b.action.type === 'prompt' && b.action.prompt) {
        console.log('Prompt:', b.action.prompt)
        this.userInput= b.action.prompt
        // 这里把 prompt 发给你的模型即可，举例：
        this.sendMessage(role = 'system')   // 你需要实现这个函数
      }
      if (b.action.type === 'random' && b.action.random) {
        if(b.action.random.events.length > 0){
          if (b.action.random.type === 'random'){
            let randomEvent = b.action.random.events[Math.floor(Math.random() * b.action.random.events.length)];
            if(randomEvent){
              this.userInput= randomEvent;
              // 这里把 prompt 发给你的模型即可，举例：
              this.sendMessage(role = 'system')   // 你需要实现这个函数
            }
          }else if( b.action.random.type === 'order'){
            if(b.action.random.orderIndex >= b.action.random.events.length){
              b.action.random.orderIndex = 0;
            }
            if(b.action.random.events[b.action.random.orderIndex]){
              let randomEvent = b.action.random.events[b.action.random.orderIndex];
              b.action.random.orderIndex += 1;
              if(randomEvent){
                this.userInput= randomEvent;
                // 这里把 prompt 发给你的模型即可，举例：
                this.sendMessage(role = 'system')   // 你需要实现这个函数
              }
            }
          }
        }
      }
    },

    /* 触发一次后，如果是“不重复”就把 enabled 关掉 */
    disableOnceBehavior(b) {
      if (b.trigger.type === 'time' && !b.trigger.time.days.length) {
        b.enabled = false
        this.autoSaveSettings()
      }
    },
    handleAllBriefly(){
      this.allBriefly = !this.allBriefly;
      if(this.allBriefly){
        this.messages.forEach((m) => {
          m.briefly = true;
        })
      }else{
        this.messages.forEach((m) => {
          m.briefly = false;
        })
      }
    },
    async handleDownload(file) {
      // 构造文件URL（确保是完整URL）
      const fileUrl = `${this.partyURL}/uploaded_files/${file.unique_filename}`;
      console.log(fileUrl);
      if (isElectron) {
        try {
          await window.electronAPI.downloadFile({
            url: fileUrl,
            filename: file.original_filename || file.unique_filename
          });
        } catch (e) {
          console.error(e);
        }
      } else {
        // 非Electron环境保留原逻辑
        const link = document.createElement('a');
        link.href = fileUrl;
        link.download = file.unique_filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    },
  removeEvent(idx,index) {
    this.behaviorSettings.behaviorList[idx].action.random.events.splice(index, 1);
    this.autoSaveSettings(); // 删除后也触发自动保存
  },
  addNewEvent(idx) {
    this.behaviorSettings.behaviorList[idx].action.random.events.push(''); // 添加一个新的空事件，从而新增一个输入框
    this.autoSaveSettings();
  },

  // 初始化周期定时器
  initCycleTimer(behavior, index) {
    // 清除现有定时器
    if (this.cycleTimers[index]) {
      clearInterval(this.cycleTimers[index]);
    }
    
    // 解析周期时间 (HH:mm:ss)
    const [hours, minutes, seconds] = behavior.trigger.cycle.cycleValue.split(':').map(Number);
    const cycleMs = (hours * 3600 + minutes * 60 + seconds) * 1000;
    
    // 当前周期计数
    let currentCount = 0;
    
    // 创建定时器
    this.cycleTimers[index] = setInterval(() => {
      if (!behavior||!behavior.enabled) return;
      
      // 检查是否无限循环或未达到重复次数
      if (behavior.trigger.cycle.isInfiniteLoop || 
          currentCount < behavior.trigger.cycle.repeatNumber) {
        
        this.runBehavior(behavior);
        currentCount++;
        
        // 非无限循环且达到次数时停止
        if (!behavior.trigger.cycle.isInfiniteLoop && 
            currentCount >= behavior.trigger.cycle.repeatNumber) {
          clearInterval(this.cycleTimers[index]);
          this.cycleTimers[index] = null;
          behavior.enabled = false;
        }
      }
    }, cycleMs);
  },
  
  // 当配置变化时重置定时器
  resetCycleTimers() {
    this.cycleTimers.forEach((timer, index) => {
      if (timer) clearInterval(timer);
      this.cycleTimers[index] = null;
    });
    
    // 重新初始化启用的周期触发器
    this.behaviorSettings.behaviorList.forEach((b, index) => {
      if (b.enabled && b.trigger.type === 'cycle') {
        this.initCycleTimer(b, index);
      }
    });
  },
    startDriverGuide() {
      const KEY = 'driver_guide_shown';
      if (localStorage.getItem(KEY)) return;
      localStorage.setItem(KEY, '1');

      const driver = window.driver.js.driver;

      const d = driver({
        allowClose: true,
        disableActiveInteraction: false,
        showProgress: true,
        nextBtnText: this.t('next'),
        prevBtnText: this.t('prev'),
        doneBtnText: this.t('done'),
        steps: [
          {
            element: '#driver-guide-btn',
            popover: {
              title: this.t('guide.driver-guide-btn'),
              description: this.t('guide.driver-guide-btn-notice'),
              side: 'right',
              align: 'start',
            },
          },
          {
            element: '#model-config',
            popover: {
              title: this.t('guide.model-config'),
              description: this.t('guide.model-config-notice'),
              side: 'right',
              // 使用 onNextClick 替代 onNext
              onNextClick: async () => {
                await this.handleSelect('model-config');
                // 手动触发下一步导航
                d.moveNext();
              }
            },
          },
          {
            element: '#add-provider-card',
            popover: {
              title: this.t('guide.add-provider-card'),
              description: this.t('guide.add-provider-card-notice'),
              side: 'right',
              // 使用 onNextClick 替代 onNext
              onNextClick: () => {
                this.showAddDialog = true;
                setTimeout(() => d.moveNext(), 100); // 手动触发下一步导航
              }
            }
          },
          {
            element: '#show-Add-Dialog',
            popover: {
              title: this.t('guide.show-Add-Dialog'),
              description: this.t('guide.show-Add-Dialog-notice'),
              side: 'top',
              // 添加 onNextClick 处理逻辑
              onNextClick: async () => {
                // 1. 判断是否已选择供应商 (假设 newProviderTemp.vendor 为空即未选)
                if (!this.newProviderTemp.vendor) {
                  // 2. 确保供应商列表至少有3个，防止报错
                  if (this.vendorOptions && this.vendorOptions.length >= 3) {
                    // 取出第三个供应商的值 (数组索引从0开始，所以是2)
                    const thirdVendorValue = this.vendorOptions[2].value;
                    
                    // 调用你的选择方法，或者直接赋值
                    // this.newProviderTemp.vendor = thirdVendorValue; 
                    this.handleSelectVendor(thirdVendorValue);
                    
                    // 3. 等待 Vue 更新 DOM (这一步很重要，因为下一步要高亮"确认"按钮，
                    // 需要确保按钮的 disable 状态已被移除)
                    await this.$nextTick(); 
                  }
                }
                
                // 4. 手动触发下一步
                d.moveNext();
              }
            }
          },
          {
            element: '#confirm-Add-Provider-Button',
            popover: {
              title: this.t('guide.confirm-Add-Provider-Button'),
              side: 'right',
              // 使用 onNextClick 替代 onNext
              onNextClick: async () => {
                this.confirmAddProvider();
                // 手动触发下一步导航
                d.moveNext();
              }
            }
          },
          {
            element: '#get-API-key',
            popover: {
              title: this.t('guide.get-API-key'),
              description: this.t('guide.get-API-key-notice'),
              side: 'right',
              onPrevClick: () => {
                this.showAddDialog = true;
                setTimeout(() => d.moveNext(), 100); // 手动触发下一步导航
              },
            }
          },
          {
            element: '#input-api-Key',
            popover: {
              title: this.t('guide.input-api-Key'),
              description: this.t('guide.input-api-Key-notice'),
              side: 'right',
            }
          },
          {
            element: '#get-Models-List',
            popover: {
              title: this.t('guide.get-Models-List'),
              description: this.t('guide.get-Models-List-notice'),
              side: 'right',
            }
          },
          {
            element: '#model-Id',
            popover: {
              title: this.t('guide.model-Id'),
              description: this.t('guide.model-Id-notice'),
              side: 'right',
            }
          },
        ]
      });

      // 监听高亮元素点击
      const checkClick = (e) => {
        if (e.target.closest('#model-config')) {
          d.moveNext();
        }
        if (e.target.closest('#add-provider-card')) {
          d.moveNext();
        }
        if (e.target.closest('#confirm-Add-Provider-Button')) {
          d.moveNext();
        }
        if (e.target.closest('#get-API-key')) {
          d.moveNext();
        }
        if (e.target.closest('#get-Models-List')) {
          d.moveNext();
        }
        if (e.target.closest('#vendor-Option')) {
          setTimeout(() => d.moveNext(), 100); // 手动触发下一步导航
        }
      };
      document.addEventListener('click', checkClick);

      // 清理监听
      d.onDestroyed = () => document.removeEventListener('click', checkClick);

      setTimeout(() => d.drive(), 300);
    },


  // 手动重开引导（可绑定到按钮）
  restartDriverGuide() {
    localStorage.removeItem('driver_guide_shown');
    this.startDriverGuide();
  },
  showToolInfo(tool) {
    this.toolForShowInfo = tool;
    this.showToolInfoDialog = true;
  },
  toggleAssistantMode() {
    this.activeMenu = 'home';
    console.log('切换助手模式，当前状态:', this.isAssistantMode);

    if (this.isAssistantMode && !this.isMac) {
      // 退出助手模式，最大化窗口
      console.log('退出助手模式，最大化窗口');
      window.electronAPI.windowAction('maximize'); // 恢复默认大小
    } else {
      // 进入助手模式，设置为300x屏幕高度
      const screenHeight = window.screen.availHeight || window.innerHeight || 800;
      console.log('进入助手模式，设置大小为:', 340, screenHeight);
      window.electronAPI.toggleWindowSize(340, screenHeight);
    }

    this.sidePanelOpen = false;
    this.isAssistantMode = !this.isAssistantMode;
    console.log('切换完成，新状态:', this.isAssistantMode);
  },
    fixedWindow() {
    // 把新状态取反
    const next = !this.isFixedWindow;
    // 告诉主进程设置置顶
    window.electronAPI.setAlwaysOnTop(next);
    // 本地状态同步
    this.isFixedWindow = next;
  },
  async toggleScreenshot () {
    try {
      // 1. 调出遮罩并等待选区
      const rect = await window.electronAPI.showScreenshotOverlay()
      if (!rect) return          // 用户取消

      // 2. 主进程裁剪
      const buf = await window.electronAPI.cropDesktop({ rect })

      // 3. 组装成 File 塞进 images
      const blob = new Blob([buf], { type: 'image/png' })
      const file = new File([blob], `desktop_${Date.now()}.png`, { type: 'image/png' })
      this.images.push({ file, name: file.name, path: '' })
    } catch (e) {
      console.error(e)
    } finally {
      // 重新显示主窗口
      await window.electronAPI.cancelScreenshotOverlay();
      window.electronAPI.windowAction('show');
    }
  },
  async toggleCapsuleMode() {
    this.activeMenu = 'home';
    if (this.isCapsuleMode && !this.isMac) {
      window.electronAPI.windowAction('maximize') // 恢复默认大小
    } else{
      window.electronAPI.toggleWindowSize(220, 75);
    }
    this.sidePanelOpen = false;
    this.isCapsuleMode = !this.isCapsuleMode;
  },
  addPrompt() {
    this.promptForm = { id: null, name: '', content: '' };
    this.showPromptDialog = true;
  },
  editPrompt(row) {
    this.promptForm = { ...row };
    this.showPromptDialog = true;
  },
  savePrompt() {
    if (!this.promptForm.name || !this.promptForm.content) {
      ElMessage.warning(this.t('pleaseCompleteForm'))
      return
    }
    if (!this.promptForm.id) {
      // 新增
      this.SystemPromptsList.push({
        id: Date.now(),
        name: this.promptForm.name,
        content: this.promptForm.content
      })
    } else {
      // 编辑：找到索引直接替换
      const idx = this.SystemPromptsList.findIndex(p => p.id === this.promptForm.id)
      if (idx > -1) {
        // 直接赋值即可，不需要 $set
        this.SystemPromptsList[idx] = { ...this.promptForm }
      }
    }
    this.showPromptDialog = false
    this.autoSaveSettings()
  },

  removePrompt(id) {
    const idx = this.SystemPromptsList.findIndex(p => p.id === id);
    if (idx > -1) this.SystemPromptsList.splice(idx, 1);
    this.autoSaveSettings();
  },
  /* 点击“使用”按钮 */
  usePrompt(content) {
    this.messages[0].content = content;
    this.activeMenu = 'home';      // 切换到主界面
    this.showEditDialog = false;
  },
  /* 主入口 */
  async handleTranslate() {
    if (!this.sourceText.trim() || this.isTranslating) return;
    this.isTranslating = true;
    this.translatedText = this.t('translating') + '…';

    const controller = new AbortController();
    this.translateAbortController = controller;

    // 构造 TTS 提示（与 translateMessage 保持一致）
    let newttsList = [];
    if (this.ttsSettings?.newtts) {
      for (const key in this.ttsSettings.newtts) {
        if (this.ttsSettings.newtts[key].enabled) newttsList.push(key);
      }
    }
    const ttsPrompt =
      newttsList.length === 0 || !this.ttsSettings?.enabled
        ? '如果被翻译的文字与目标语言一致，则返回原文即可'
        : `你还需要在翻译的同时，添加对应的音色标签。如果被翻译的文字与目标语言一致，则只需要添加对应的音色标签。注意！不要使用<!--  -->这会导致部分文字不可见！你可以使用以下音色：\n${newttsList.join(
            ', '
          )}\n，当你生成回答时，将不同的旁白或角色的文字用<音色名></音色名>括起来，以表示这些话是使用这个音色，以控制不同TTS转换成对应音色。对于没有对应音色的部分，可以不括。即使音色名称不为英文，还是可以照样使用<音色名>使用该音色的文本</音色名>来启用对应音色。注意！如果是你扮演的角色的名字在音色列表里，你必须用这个音色标签将你扮演的角色说话的部分括起来！只要是非人物说话的部分，都视为旁白！角色音色应该标记在人物说话的前后！例如：<Narrator>现在是下午三点，她说道：</Narrator><角色名>”天气真好哇！“</角色名><Narrator>说完她伸了个懒腰。</Narrator>\n\n`;

    try {
      const res = await fetch('/simple_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.mainAgent,
          messages: [
            {
              role: 'system',
              content: `你是一位专业翻译，请将用户提供的任何内容严格翻译为${this.target_lang}，保持原有格式（如Markdown、换行等），不要添加任何额外内容。只需返回翻译结果。${ttsPrompt}`
            },
            {
              role: 'user',
              content: `请翻译以下内容到${this.target_lang}：\n\n${this.sourceText}`
            }
          ],
          stream: true,
          temperature: 0.1
        }),
        signal: controller.signal
      });

      if (!res.ok) throw new Error('Network error');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = ''; // 残余半截行
      let result = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 最后一行可能不完整，留到下一轮

        for (const line of lines) {
          if (!line) continue; // 跳过空行
          try {
            const chunk = JSON.parse(line);
            const delta = chunk.choices?.[0]?.delta?.content ?? '';
            if (delta) {
              result += delta;
              this.translatedText = result; // 实时渲染
            }
          } catch {
            // 忽略解析失败
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        this.translatedText = `Translation error: ${e.message}`;
      }
    } finally {
      this.isTranslating = false;
      this.translateAbortController = null;
    }
  },

  abortTranslate () {
    this.translateAbortController?.abort()
    this.isTranslating = false
  },

  clearAll () {
    this.sourceText = ''
    this.translatedText = ''
  },
  changeLanguage() {
    this.target_lang = this.targetLangSelected!="system"? this.targetLangSelected: navigator.language || navigator.userLanguage || 'zh-CN';
    this.autoSaveSettings()
  },
  copyTranslated() {
    if (!this.translatedText) return
    navigator.clipboard.writeText(this.translatedText)
    showNotification(this.t('copy_success'))
  },
  handleShowAddMemoryDialog() {
    if (this.isGenerating){
      showNotification(this.t('AIgening'))
       return;
    }
    this.showAddMemoryDialog = true
  },
  async handleQuickGen() {
    if (!this.quickCreatePrompt.trim() || this.isGenerating) return;

    this.isGenerating = true;
    showNotification(this.t('startGen'));

    const controller = new AbortController();
    this.QuickGenAbortController = controller;

    const systemPrompt = `你是一名专业的角色设计师。  
  生成的角色卡内容必须与用户输入的语言保持一致。  
  用户会提供一个简短的创意，你必须仅回复一段**有效的 JSON**，并放在一个标准的Markdown 代码块中。  
  JSON 结构必须为：

    {
      "name": "角色名称",
      "description": "简要背景/世界观设定，尽可能详细",
      "personality": "性格特征",
      "mesExample": "展示 2~5 轮聊天示例，格式：用户:xxx\n角色:xxx",
      "systemPrompt": "用于驱动角色的系统提示",
      "firstMes": "角色的第一句问候语",
      "alternateGreetings": ["可选问候2","可选问候3"],
      "characterBook": [
          {"keysRaw":"关键词1\n关键词2","content":"这里填入当用户提到关键词1或关键词2时，需要返回给AI看的内容……"},
          {"keysRaw":"关键词3","content":"这里填入当用户提到关键词3时，需要返回给AI看的内容……"}
      ]
    }

  所有字段都必须提供；characterBook也请尽可能的丰富，最好可以在10条以上，每条的字数可以不用太多。alternateGreetings最好也有5条以上。
  绝不可包含 avatar 字段。`;

    try {
      const res = await fetch('/simple_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: this.quickCreatePrompt }
          ],
          stream: true,   // ★ 打开流式
          temperature: 0.8
        }),
        signal: controller.signal
      });

      if (!res.ok) throw new Error('Network error');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';      // 残余半截行
      let fullText = '';    // 累积完整回复

      // 1. 实时读流
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 最后一行可能不完整

        for (const line of lines) {
          if (!line) continue;
          try {
            const chunk = JSON.parse(line);
            const delta = chunk.choices?.[0]?.delta?.content ?? '';
            if (delta) {
              fullText += delta;
              this.quickCreatePrompt = fullText; // 实时显示
            }
          } catch {
            // 忽略解析失败
          }
        }
      }

      // 2. 流结束，再走原来的解析逻辑
      let raw = fullText.trim();

      // 去 code-block
      const codeBlock = raw.match(/^```json\s*([\s\S]*?)```$/);
      if (codeBlock) raw = codeBlock[1];
      const tildeBlock = raw.match(/^```\s*([\s\S]*?)```$/);
      if (tildeBlock) raw = tildeBlock[1];

      // 解析 JSON
      let json;
      try {
        json = JSON.parse(raw);
      } catch (e) {
        throw new Error('AI 返回的不是合法 JSON：' + e.message);
      }

      // 3. 写入 newMemory 并保存
      Object.assign(this.newMemory, {
        name: json.name ?? '',
        providerId: null,
        model: '',
        base_url: '',
        api_key: '',
        vendor: '',
        description: json.description ?? '',
        personality: json.personality ?? '',
        mesExample: json.mesExample ?? '',
        systemPrompt: json.systemPrompt ?? '',
        firstMes: json.firstMes ?? '',
        alternateGreetings: json.alternateGreetings?.filter(Boolean) ?? [],
        characterBook: (json.characterBook ?? []).map(b => ({
          keysRaw: b.keysRaw ?? '',
          content: b.content ?? ''
        })),
        avatar: ''
      });
      this.newMemory.id = null;
      this.addMemory();
      showNotification(this.t('genSuccess'));

    } catch (e) {
      if (e.name === 'AbortError') {
        console.log('QuickGen aborted');
      } else {
        showNotification(this.t('genFailed') + ': ' + e.message, 'error');
      }
    } finally {
      this.isGenerating = false;
      this.QuickGenAbortController = null;
    }
  },
  stopQuickGen() {
    this.QuickGenAbortController?.abort()
    this.isGenerating = false
  },
  async handleSystemPromptQuickGen() {
    if (!this.quickCreateSystemPrompt.trim() || this.isSystemPromptGenerating) return;
    
    this.isSystemPromptGenerating = true;
    this.promptForm.name = this.quickCreateSystemPrompt;
    showNotification(this.t('startGen'));
    
    const controller = new AbortController();
    this.QuickGenSystemPromptAbortController = controller;
    
    try {
      const res = await fetch('/simple_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.mainAgent,
          messages: [
            {
              role: 'system',
              content: `你需要将用户发给你的简短的系统提示词优化成可以驱动大模型更好的工作的详细的系统提示词。
  注意！生成的系统提示词必须与用户输入的语言保持一致。如果用户说英文，你就必须生成英文的系统提示词；如果用户说中文，你就必须生成中文的系统提示词。以此类推！
  你可以从这几个方面来写，但也不要限于这些方面：角色名、角色定位、核心能力、回答风格、约束、输出格式示例等等`,
            },
            {
              role: 'user',
              content: `${this.quickCreateSystemPrompt}`,
            },
          ],
          stream: true,
          temperature: 0.8
        }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error('Network error');
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let result = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (!line) continue;
          
          try {
            const data = JSON.parse(line);
            
            // 适配新的流式响应格式
            if (data.choices && data.choices[0]) {
              const choice = data.choices[0];
              
              // 处理流式响应中的增量内容
              if (choice.delta && choice.delta.content) {
                result += choice.delta.content;
                this.quickCreateSystemPrompt = result;
              }
              // 或者处理 finish_reason 为 stop 的最终响应
              else if (choice.finish_reason === 'stop') {
                // 最终完成，不需要额外处理
              }
            }
          } catch (e) {
            console.warn('Failed to parse SSE line:', line, e);
          }
        }
        
        buffer = lines[lines.length - 1];
      }
      
      // 处理可能剩余的缓冲数据
      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer);
          if (data.choices && data.choices[0] && data.choices[0].delta && data.choices[0].delta.content) {
            result += data.choices[0].delta.content;
            this.quickCreateSystemPrompt = result;
          }
        } catch (e) {
          console.warn('Failed to parse remaining buffer:', buffer, e);
        }
      }
      
      // 保存生成的提示词
      this.promptForm.content = this.quickCreateSystemPrompt;
      this.promptForm.id = null;
      await this.savePrompt();
      
      showNotification(this.t('genSuccess'));
      this.quickCreateSystemPrompt = '';
      
    } catch (e) {
      if (e.name === 'AbortError') {
        // 用户取消了生成，不需要显示错误
        console.log('System prompt generation was aborted');
      } else {
        console.error('System prompt generation failed:', e);
        showNotification(this.t('genFailed') + ': ' + e.message, 'error');
      }
    } finally {
      this.isSystemPromptGenerating = false;
      this.QuickGenSystemPromptAbortController = null;
    }
  },
  stopSystemPromptQuickGen() {
    this.QuickGenSystemPromptAbortController?.abort()
    this.isSystemPromptGenerating = false
  },
  async toggleQuickGen(index) {
    let systemPrompt = this.messages[index].content;
    if (!systemPrompt.trim()) {
      showNotification(this.t('noSystemPromptToExtend'), 'error');
      return;
    }
    
    showNotification(this.t('startGen'));
    this.isQuickGenerating = true;
    const abortController = new AbortController();
    this.abortController = abortController;
    
    try {
      const res = await fetch('/simple_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.mainAgent,
          messages: [
            {
              role: 'system',
              content: `你需要将用户发给你的简短的系统提示词优化成可以驱动大模型更好的工作的详细的系统提示词。
  注意！生成的系统提示词必须与用户输入的语言保持一致。如果用户说英文，你就必须生成英文的系统提示词；如果用户说中文，你就必须生成中文的系统提示词。以此类推！
  你可以从这几个方面来写，但也不要限于这些方面：角色名、角色定位、核心能力、回答风格、约束、输出格式示例等等`
            },
            {
              role: 'user',
              content: `${systemPrompt}`,
            },
          ],
          stream: true,
          temperature: 0.8
        }),
        signal: this.abortController.signal,
      });

      if (!res.ok) throw new Error('Network error');
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let result = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (!line) continue;
          
          try {
            const data = JSON.parse(line);
            
            // 适配新的流式响应格式
            if (data.choices && data.choices[0]) {
              const choice = data.choices[0];
              
              // 处理流式响应中的增量内容
              if (choice.delta && choice.delta.content) {
                result += choice.delta.content;
                this.messages[index].content = result;
                this.scrollToBottom();
              }
              // 或者处理 finish_reason 为 stop 的最终响应
              else if (choice.finish_reason === 'stop') {
                // 最终完成，不需要额外处理
              }
            }
          } catch (e) {
            console.warn('Failed to parse SSE line:', line, e);
          }
        }
        
        buffer = lines[lines.length - 1];
      }
      
      // 处理可能剩余的缓冲数据
      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer);
          if (data.choices && data.choices[0] && data.choices[0].delta && data.choices[0].delta.content) {
            result += data.choices[0].delta.content;
            this.messages[index].content = result;
            this.scrollToBottom();
          }
        } catch (e) {
          console.warn('Failed to parse remaining buffer:', buffer, e);
        }
      }
      
      showNotification(this.t('genSuccess'));
      
    } catch (e) {
      if (e.name === 'AbortError') {
        // 用户取消了生成，不需要显示错误
        console.log('Quick generation was aborted');
      } else {
        console.error('Quick generation failed:', e);
        showNotification(this.t('genFailed') + ': ' + e.message, 'error');
      }
    } finally {
      this.isQuickGenerating = false;
      this.abortController = null;
    }
  },
  saveSystemPrompt(index) {
    let systemPrompt = this.messages[index].content;
    this.activeMenu = 'role';
    this.subMenu = 'memory';
    this.activeMemoryTab = 'prompts';
    this.promptForm = { id: null, name: '', content: systemPrompt };
    this.showPromptDialog = true;
  },
  async browseDirectory() {
    if (!this.isElectron) {
      // 浏览器环境
      return;
    } else {
      // Electron 环境
      try {
        const result = await window.electronAPI.openDirectoryDialog();
        if (!result.canceled && result.filePaths.length > 0) {
          this.CLISettings.cc_path = result.filePaths[0];
          this.autoSaveSettings();
        }
      } catch (error) {
        console.error('选择目录出错:', error);
        showNotification('选择目录失败', 'error');
      }
    }
  },
  async installClaudeCode() {
    try {
      const scriptUrl = `${this.partyURL}/sh/claude_code_install.sh`;
      const platform = await window.electronAPI.getPlatform();

      if (platform === 'win32') {
        // 一条命令：先 curl 拉取远程 bat，再立即执行；/k 保持窗口
        const batUrl = `${this.partyURL}/sh/claude_code_install.bat`;
        window.electronAPI.execCommand(
          `start "" cmd /k "curl -fsSL ${batUrl} -o \"%TEMP%\\claude_install.bat\" && \"%TEMP%\\claude_install.bat\""`
        );
      } else if (platform === 'darwin') {
        // macOS
        window.electronAPI.execCommand(
          `osascript -e 'tell app "Terminal" to do script "bash -c \\\"$(curl -fsSL ${scriptUrl}) \\\""'`
        );
      } else {
        // Linux
        window.electronAPI.execCommand(
          `gnome-terminal -- bash -c "curl -fsSL ${scriptUrl} | bash; exec bash"`
        );
      }
      showNotification(this.t('scriptExecuting'));
    } catch (error) {
      showNotification(`failed to install Claude Code: ${error.message}`, 'error');
    } finally {

    }
  },

  async installQwenCode() {
    try {
      const scriptUrl = `${this.partyURL}/sh/qwen_code_install.sh`;
      const platform = await window.electronAPI.getPlatform();

      if (platform === 'win32') {
        // 一条命令：先 curl 拉取远程 bat，再立即执行；/k 保持窗口
        const batUrl = `${this.partyURL}/sh/qwen_code_install.bat`;
        window.electronAPI.execCommand(
          `start "" cmd /k "curl -fsSL ${batUrl} -o \"%TEMP%\\qwen_install.bat\" && \"%TEMP%\\qwen_install.bat\""`
        );
      } else if (platform === 'darwin') {
        // macOS
        window.electronAPI.execCommand(
          `osascript -e 'tell app "Terminal" to do script "bash -c \\\"$(curl -fsSL ${scriptUrl}) \\\""'`
        );
      } else {
        // Linux
        window.electronAPI.execCommand(
          `gnome-terminal -- bash -c "curl -fsSL ${scriptUrl} | bash; exec bash"`
        );
      }
      showNotification(this.t('scriptExecuting'));
    } catch (error) {
      showNotification(`failed to install Qwen Code: ${error.message}`, 'error');
    } finally {

    }
  },
  
  _toggleHighlight(e) {
    const blk = e.target.closest('.highlight-block');
    if (!blk) return;
    blk.classList.toggle('expanded');
  },
  changeSystemPrompt() {
    this.editContent = this.SystemPromptsList.find(prompt => prompt.id === this.selectSystemPromptId)?.content;
  },
/* -------------------------------------------------- */
/* 1. 自动分段（复用全文算法）                       */
/* -------------------------------------------------- */
reSegment() {
  this.stopSegmentTTS();          // 停旧音频
    const {
      chunks,
      chunks_voice,
      remaining,
      remaining_voice
    } = this.splitTTSBuffer(this.readConfig.longText);

    if (remaining) {
      chunks.push(remaining);
      chunks_voice.push(remaining_voice);
    }

      /* ================= 新增：去标签 + 去空白并同步删除 ================= */
      // 1. 去 HTML 标签
      const cleanedChunks = chunks.map(txt => txt.replace(/<\/?[^>]+>/g, '').trim());

      // 2. 过滤空白并同步删除 chunks_voice 对应项
      const finalChunks       = [];
      const finalChunksVoice  = [];

      cleanedChunks.forEach((txt, idx) => {
        if (txt) {                      // 非空才保留
          finalChunks.push(txt);
          finalChunksVoice.push(chunks_voice[idx]);
        }
      });

      // 3. 覆盖原来的数组
      chunks.length       = 0;
      chunks_voice.length = 0;
      chunks.push(...finalChunks);
      chunks_voice.push(...finalChunksVoice);
      /* ================================================================ */

  this.readState.ttsChunks = chunks;
  this.readState.chunks_voice = chunks_voice;
  this.readState.audioChunks  = new Array(this.readState.ttsChunks.length);
  this.readState.currentChunk = -1;
},

/* -------------------------------------------------- */
/* 2. 播放单句（含 VRM 同步）                        */
/* -------------------------------------------------- */
async playSingleSegment(idx) {
  try{
    if (!this.readState.ttsChunks[idx]) return;
    this.isReadingOnetext = true;
    this.readState.currentChunk = idx;
    const chunk = this.readState.ttsChunks[idx];
    const voice = this.readState.chunks_voice[idx];
    const cachedAudio = this.readState.audioChunks[idx];

    // 检查缓存是否命中
    if (cachedAudio?.url && cachedAudio?.base64 && cachedAudio?.text === chunk && cachedAudio?.voice === voice) {
      this.doPlayAudio(this.readState.audioChunks[idx].url, idx, false); // false=不连播
      return;
    }
    // 未命中先合成
    await this.synthSegment(idx);
    this.doPlayAudio(this.readState.audioChunks[idx].url, idx, false);
  } finally {
    this.isReadingOnetext = false;
  }
},

/* -------------------------------------------------- */
/* 3. 连续播放开关                                   */
/* -------------------------------------------------- */
async toggleContinuousPlay() {
  if (this.readState.isPlaying) {          // 暂停
    this.stopSegmentTTS(isEnd=false);
    return;
  }
  this.readState.isPlaying   = true;
  if (this.readState.currentChunk < 0 || this.readState.currentChunk >= this.readState.ttsChunks.length) { // 从头开始
    this.readState.currentChunk = 0;         // 从第一句开始
  }
  await this.playNextInQueue(true);        // true 表示连续
},

/* -------------------------------------------------- */
/* 4. 新增：仅播放下一句（播完即停）                  */
/* -------------------------------------------------- */
async playNextSegmentOnce() {
  let next = this.readState.currentChunk + 1;
  this.readState.currentChunk = next;
  if (next >= this.readState.ttsChunks.length) {
    next = 0;
    this.readState.currentChunk = next;
  }
  this.readState.isPlaying = false;      // 确保不自动连播
  await this.playSingleSegment(next);    // 播完即停
},

/* -------------------------------------------------- */
/* 5. 停止所有分段音频                               */
/* -------------------------------------------------- */
stopSegmentTTS(isEnd = true) {
  this.stopTTSActivities();
  if (isEnd){
    this.readState.currentChunk = -1;
  }
  if (this._curAudio) {
    this._curAudio.pause();
    this._curAudio = null;
  }
  this.readState.isPlaying   = false;
},
/* -------------------------------------------------- */
/* 6. 编辑段文本                                      */
/* -------------------------------------------------- */
toggleEditSegment(idx) {
  if (this.activeSegmentIdx === idx) {
    // 保存：把临时值写回正式字段
    this.readState.ttsChunks[idx] = this.segmentEditBuffer
    this.readState.chunks_voice[idx] = this.segmentVoiceEditBuffer[idx] ?? this.readState.chunks_voice[idx]
    this.activeSegmentIdx = -1
  } else {
    // 进入编辑：先给“音色临时数组”对应位置塞个初始值
    this.segmentEditBuffer = this.readState.ttsChunks[idx]
    // Vue3 直接赋值即可
    this.segmentVoiceEditBuffer[idx] = this.readState.chunks_voice[idx]
    this.activeSegmentIdx = idx
  }
},

/* 1. 合成时顺便转 base64 */
async synthSegment(idx) {
  try {
    const text  = this.readState.ttsChunks[idx];
    const voice = this.readState.chunks_voice[idx] || 'default';
    /* —— 与对话版完全一致的文本清洗 —— */
    let chunk_text = text;
    let chunk_expressions =[];
    if (text.indexOf('<') !== -1) {
      const tagReg = /<[^>]+>/g;
      chunk_expressions = (text.match(tagReg) || []).map(t => t.slice(1, -1)); // 去掉两端的 <>
      chunk_text = text.replace(tagReg, '').trim(); // 把标签从正文里删掉
    }
    const res = await fetch('/tts', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ ttsSettings: this.ttsSettings, text, index: idx, voice }),
    });
    if (!res.ok) throw new Error('TTS failed');

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);

    /* 关键：同步转 base64 */
    const base64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload  = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

    /* 缓存两样东西 */
    this.readState.audioChunks[idx] = {
      url,                       // 本地播放用
      expressions: chunk_expressions,
      base64: `data:${blob.type};base64,${base64}`, // VRM 播放用
      text: chunk_text,
      idx,
      voice
    };
  } catch (e) {
    console.error(`TTS chunk ${idx} error`, e);
    this.readState.audioChunks[idx] = { 
      url: null, 
      base64: null,
      expressions: [],
      text: "",
      idx 
    };
  }
},
scrollToCurrentChunk(idx) {
  // 使用 nextTick 确保 DOM 更新完成
  this.$nextTick(() => {
    const segmentList = document.querySelector('.segment-list');
    const segmentItem = document.querySelector(`.segment-item:nth-child(${idx + 1})`);
    if (segmentList && segmentItem) {
      segmentItem.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  });
},

async doPlayAudio(url, idx, continuous = false) {
  if (this._curAudio) {
    this._curAudio.pause();
    this.sendTTSStatusToVRM('stopSpeaking', {});
  }
  try {
    const audio = new Audio(url);
    this._curAudio = audio;

    // 滚动到当前行
    this.scrollToCurrentChunk(idx);

    const chunk = this.readState.audioChunks[idx];
    if (chunk.base64 == null) throw new Error('No base64');
    this._curAudio.volume = this.vrmOnline ? 0.0000001 : 1; // VRM在线时静音
    this.sendTTSStatusToVRM('startSpeaking', {
      audioDataUrl: chunk.base64,
      chunkIndex: idx,
      totalChunks: this.readState.ttsChunks.length,
      text: chunk.text,
      expressions: chunk.expressions || [],
      voice: this.readState.chunks_voice[idx] || 'default',
    });

    // 监听错误事件
    audio.addEventListener('error', (e) => {
      console.error('Audio load error', e);
      this.readState.currentChunk++;
      if (this.readState.currentChunk < this.readState.ttsChunks.length) {
        this.playNextInQueue(true);
      } else {
        this.stopSegmentTTS();
      }
    });

    await new Promise(resolve => {
      this._curAudio.addEventListener('ended', () => {
        this.sendTTSStatusToVRM('chunkEnded', { chunkIndex: idx });
        if (continuous && this.readState.isPlaying) {
          this.readState.currentChunk++;
          if (this.readState.currentChunk < this.readState.ttsChunks.length) {
            this.playNextInQueue(true);
          } else {
            this.stopSegmentTTS();
          }
        } else {
          this.stopSegmentTTS(isEnd = false);
        }
        resolve();
      });
      console.log('play audio', `${idx + 1}`);
      audio.play().catch(e => {
        console.error('Audio play error', e);
        this.readState.currentChunk++;
        if (this.readState.currentChunk < this.readState.ttsChunks.length) {
          this.playNextInQueue(true);
        } else {
          this.stopSegmentTTS();
        }
        resolve(); // 确保 Promise 被 resolve
      });
    });
  } catch (e) {
    console.error('Read playback error', e);
    this.readState.currentChunk++;
    if (this.readState.currentChunk < this.readState.ttsChunks.length) {
      this.playNextInQueue(true);
    } else {
      this.stopSegmentTTS();
    }
  } finally {
      this.isReadingOnetext = false;
    }
},

// 连续播放专用：自动合成&播放下一帧
async playNextInQueue(continuous) {
  const idx = this.readState.currentChunk;   // 当前要播的索引
  const chunk = this.readState.ttsChunks[idx];
  const voice = this.readState.chunks_voice[idx];
  const cachedAudio = this.readState.audioChunks[idx];

  // 检查缓存是否命中
  if (cachedAudio?.url && cachedAudio?.base64 && cachedAudio?.text === chunk && cachedAudio?.voice === voice) {
    // 命中就无事发生
  }else{
    await this.synthSegment(idx);
  }
  this.doPlayAudio(this.readState.audioChunks[idx].url, idx, continuous);
},

// 清空分段
clearSegments() {
  this.stopSegmentTTS();
  this.readState.ttsChunks   = [];
  this.readState.chunks_voice = [];
  this.readState.audioChunks  = [];
  this.readState.currentChunk = -1;
},
  // 扫描扩展但不自动加载
  async scanExtensions() {
    try {
      // 使用API获取扩展列表
      const response = await fetch('/api/extensions/list');
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '获取扩展列表失败');
      }
      
      const data = await response.json();
      this.extensions = data.extensions || [];
      
      // 不再自动加载第一个扩展
      // 默认显示 sidePanelText 内容
      this.currentExtension = null;
      this.sidePanelURL = '';
    } catch (error) {
      console.error('扫描扩展出错:', error);
    }
  },
  
    // 加载指定扩展
  async loadExtension(extension) {
    if (!extension) {
      this.currentExtension = null;
      this.sidePanelURL = '';
      return;
    }

    /* 1. 先尝试 Node 模式 */
    try {
      const r = await fetch(`/api/extensions/${extension.id}/start-node`, { method: 'POST' });
      const res = await r.json();

      if (res.mode === 'node') {
        // ✅ Node 成功
        this.currentExtension = extension;
        this.sidePanelURL = `/api/extensions/${extension.id}/node/`;
        showNotification(`${this.t('loadExtension(node)')}: ${extension.name}`, 'success');
        return;
      }
      // res.mode === 'static' 继续走下面兜底
    } catch (e) {
      // 任何异常也继续兜底
    }

    /* 2. 回退静态路由 */
    this.currentExtension = extension;
    this.sidePanelURL = `/ext/${extension.id}/index.html`;
    showNotification(`${this.t('loadExtension(static)')}: ${extension.name}`, 'success');
  },
  
  // 切换到默认视图
  resetToDefaultView() {
    this.loadExtension(null);
    this.showExtensionsDialog = false;
    this.expandChatArea();
    this.collapseSidePanel();
    this.messages[0].content = '';
  },
  // 打开扩展选择对话框
  openExtensionsDialog() {
    this.showExtensionsDialog = true;
  },
  
  // 切换扩展
  async switchExtension(extension) {
    this.sidePanelURL = '';
    this.showExtensionsDialog = false; // 关闭对话框
    this.currentExtension = extension;
    this.expandSidePanel();
    await this.loadExtension(extension);
  },

  // 工具函数：返回扩展真正能访问的地址（Node > 静态）
  async getExtensionURL(ext) {
    console.log('获取扩展URL', ext);
    // 1. 先尝试启动 Node
    try {
      const r = await fetch(`/api/extensions/${ext.id}/start-node`, { method: 'POST' });
      const res = await r.json();
      if (res.mode === 'node') {
        return `/api/extensions/${ext.id}/node/`;   // ✅ Node 代理路径
      }
      console.log('启动 Node 失败，回退静态',res);
    } catch { 
     }
    // 2. 回退静态
    return `/ext/${ext.id}/index.html`;
  }, 

    async openExtension(extension) {
      const url = await this.getExtensionURL(extension);   // ⬅️ 异步拿地址
      console.log('打开扩展', `${this.partyURL}${url}`);
      if (isElectron) {
        window.electronAPI.openExternal(`${this.partyURL}${url}`);
      } else {
        window.open(url, '_blank');
      }
    },
    // 删除扩展
    async removeExtension(ext) {
      // 若是 Node 模式就停进程，忽略错误
      await fetch(`/api/extensions/${ext.id}/stop-node`, { method: 'POST' }).catch(() => {});
      try {
        const res = await fetch(`/api/extensions/${ext.id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('删除失败');
        showNotification(this.t('deleteSuccess'), 'success');
        this.scanExtensions(); // 刷新列表
      } catch (e) {

         showNotification(e.message, 'error');
      }
    },

    // 打开「添加扩展」对话框
    openAddExtensionDialog() {
      this.newExtensionUrl = '';
      this.showExtensionForm = true;
      this.fetchRemotePlugins();
    },

    async pollInstallStatus(extId, onSuccess, onError) {
      const poll = async () => {
        try {
          const res = await fetch(`/api/extensions/task-status/${extId}`);
          const data = await res.json();

          if (data.status === 'success') {
            // 安装成功
            onSuccess(data.detail);
          } else if (data.status === 'error') {
            // 安装失败
            onError(data.detail);
          } else if (data.status === 'installing') {
             // 仍在安装中，继续轮询 (这里可以顺便更新界面提示，如果你有对应UI的话)
             // 例如：console.log(data.detail); 
             setTimeout(poll, 1000); // 1秒后再次检查
          } else {
             // 未知状态，可能是重启了或者ID错了
             onError("任务状态丢失");
          }
        } catch (e) {
          onError("网络请求错误");
        }
      };
      // 开始第一次轮询
      poll();
    },

    // 真正「安装」按钮触发
    async addExtension() {
      const url = this.newExtensionUrl.trim();
      if (!url) return showNotification('请输入 GitHub 地址', 'error');
      
      this.installLoading = true; // 开启 Loading 遮罩
      
      try {
        const res = await fetch('/api/extensions/install-from-github', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            url,
            backupUrl: ""  
          }),
        });
        
        if (res.status === 409) throw new Error(this.t('extensionExists'));
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || this.t('deleteFailed'));
        }

        const resData = await res.json();
        const extId = resData.ext_id;

        // --- 核心修改：开始轮询 ---
        showNotification('正在后台下载，请稍候...', 'info');
        
        this.pollInstallStatus(
          extId,
          (msg) => {
            // 成功回调
            this.installLoading = false;
            showNotification(msg || '安装成功！', 'success');
            this.showExtensionForm = false; // 关闭弹窗
            this.scanExtensions(); // 立即刷新列表
          },
          (errMsg) => {
            // 失败回调
            this.installLoading = false;
            showNotification(`安装失败: ${errMsg}`, 'error');
          }
        );

      } catch (e) {
        this.installLoading = false;
        showNotification(e.message, 'error');
      }
    },
    // 打开文件选择器
    selectLocalZip() {
      this.$refs.zipInput.click();
    },

    // 选中文件后自动上传
    async onZipSelected(e) {
      const file = e.target.files?.[0];
      if (!file) return;
      this.installLoading = true;
      const form = new FormData();
      form.append('file', file);
      try {
        const res = await fetch('/api/extensions/upload-zip', {
          method: 'POST',
          body: form,
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || '上传失败');
        }
        showNotification(this.t('waitExtensionInstall'));
        this.showExtensionForm = false;
        this.scanExtensions(); // 刷新
      } catch (err) {
        showNotification(err.message,'error');
      } finally {
        this.installLoading = false;
        e.target.value = ''; // 允许重复选同一文件
      }
    },

    async fetchRemotePlugins() {
      try {
        await this.scanExtensions(); // 刷新
        const res = await fetch('/api/extensions/remote-list');
        const { plugins } = await res.json();   // 取出 plugins 数组
        console.log(plugins);
        const localRes = await fetch('/api/extensions/list');
        const { extensions } = await localRes.json();
        console.log(extensions);
        this.remotePlugins = plugins.map(r => ({
          ...r,
          installed: extensions.some(l => l.repository.trim() === r.repository.trim()),
        }));
      } catch (e) {
        
      }
    },
async togglePlugin(plugin) {
    if (plugin.installed) {
      // 卸载逻辑保持不变...
      await this.removeExtension(plugin);
      plugin.installed = false;
    } else {
      // --- 安装逻辑 ---
      
      // 1. 设置局部 loading 状态 (如果你的 plugin 对象支持)
      // 如果没有局部 loading，就用全局 this.installLoading = true
      plugin.installing = true
      this.installLoading = true; 

      try {
        const res = await fetch('/api/extensions/install-from-github', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            url: plugin.repository,
            backupUrl: plugin.backupRepository || "" 
          }),
        });

        if (res.status === 409) throw new Error('插件已存在');
        if (!res.ok) throw new Error('请求失败');
        
        const resData = await res.json();
        const extId = resData.ext_id;

        showNotification('已开始下载，请耐心等待...', 'info');

        // --- 核心修改：开始轮询 ---
        this.pollInstallStatus(
          extId,
          (msg) => {
            // 成功
            this.installLoading = false;
            if (plugin) plugin.installing = false;
            plugin.installed = true; // 更新前端状态
            showNotification('安装成功！', 'success');
            this.scanExtensions(); // 刷新完整列表以确保数据一致
          },
          (errMsg) => {
            // 失败
            this.installLoading = false;
            if (plugin) plugin.installing = false;
            showNotification(`安装失败: ${errMsg}`, 'error');
          }
        );

      } catch (e) {
        this.installLoading = false;
        if (plugin) plugin.installing = false;
        showNotification(e.message, 'error');
      }
    }
  },
  handleRefreshClick() {
    this.refreshing = true;
    
    // 调用原有的刷新方法
    this.fetchRemotePlugins().then(() => {
      // 请求完成后
      this.refreshing = false;
      this.refreshButtonText = this.t('refreshedSuccess') || '已刷新';
      
      // 2秒后恢复按钮文字
      setTimeout(() => {
        this.refreshButtonText = this.t('refreshList');
      }, 2000);
    }).catch(error => {
      // 处理错误情况
      this.refreshing = false;
      this.refreshButtonText = this.t('refreshFailed') || '刷新失败';
      
      // 2秒后恢复按钮文字
      setTimeout(() => {
        this.refreshButtonText = this.t('refreshList');
      }, 2000);
    });
  },
  openRepository(url) {
    if (isElectron) {
      window.electronAPI.openExternal(url)   // 主进程会新建可关闭的独立窗口
    } else {
      window.open(url, '_blank')
    }
  },
  // 开始拖拽调整大小
  startResize(e) {
    if (!this.chatAreaOpen || !this.sidePanelOpen) return;
    
    const container = this.$refs.chatWrapperRef;
    if (!container) {
      console.error('Container not found');
      return;
    }
    
    this.isResizing = true;
    const startX = e.clientX;
    const containerRect = container.getBoundingClientRect();
    const containerWidth = containerRect.width;
    
    // 添加拖拽状态类到容器
    container.classList.add('resizing');

    const handleMouseMove = (e) => {
      if (!this.isResizing) return;
      
      // 计算鼠标相对于容器的位置
      const mouseX = e.clientX - containerRect.left;
      
      // 限制鼠标位置在容器范围内
      const clampedMouseX = Math.max(0, Math.min(mouseX, containerWidth));
      
      // 计算新的分割条位置（像素值）
      const newResizerPosition = clampedMouseX;
      
      // 计算左右面板的像素宽度
      const leftWidth = newResizerPosition;
      const rightWidth = containerWidth - newResizerPosition - 8; // 8px 是分割条宽度
      
      // 转换为百分比（用于检查最小宽度）
      const leftPercent = (leftWidth / containerWidth) * 100;
      const rightPercent = (rightWidth / containerWidth) * 100;
      
      // 检查是否需要收起面板
      if (leftPercent < this.minPanelWidth) {
        this.collapseChatArea();
        return;
      }
      
      if (rightPercent < this.minPanelWidth) {
        this.collapseSidePanel();
        return;
      }
      
      // 直接设置像素宽度，而不是百分比
      this.updatePanelWidthsWithPixels(leftWidth, rightWidth);
    };

    const handleMouseUp = () => {
      this.isResizing = false;
      
      // 移除拖拽状态类
      container.classList.remove('resizing');
      
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      
      // 拖拽结束后，重新计算百分比（用于响应式）
      this.recalculatePercentages();
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  },

  // 使用像素宽度更新面板
  updatePanelWidthsWithPixels(leftWidth, rightWidth) {
    this.$nextTick(() => {
      const chatArea = this.$refs.chatAreaRef;
      const sidePanel = this.$refs.sidePanelRef;
      
      if (!chatArea || !sidePanel) {
        return;
      }
      
      if (this.chatAreaOpen && this.sidePanelOpen) {
        chatArea.style.width = `${leftWidth}px`;
        sidePanel.style.width = `${rightWidth}px`;
      }
    });
  },

  // 重新计算百分比（用于保存状态和响应式）
  recalculatePercentages() {
    const container = this.$refs.chatWrapperRef;
    if (!container) return;
    
    const containerWidth = container.offsetWidth;
    const chatArea = this.$refs.chatAreaRef;
    const sidePanel = this.$refs.sidePanelRef;
    
    if (chatArea && sidePanel && this.chatAreaOpen && this.sidePanelOpen) {
      const chatAreaWidth = chatArea.offsetWidth;
      const sidePanelWidth = sidePanel.offsetWidth;
      
      this.chatAreaWidth = (chatAreaWidth / containerWidth) * 100;
      this.sidePanelWidth = (sidePanelWidth / containerWidth) * 100;
    }
  },

  // 处理分割条点击
  handleResizerClick(e) {
    if (e.target.closest('.expand-chat-btn') || e.target.closest('.expand-side-btn')) {
      return;
    }
    
    // 双击重置为50:50
    if (e.detail === 2) {
      this.resetPanelSizes();
    }
  },

  // 收起对话区域
  collapseChatArea() {
    this.chatAreaOpen = false;
    this.sidePanelWidth = 100;
    this.updatePanelWidths();
  },

  // 收起侧边栏
  collapseSidePanel() {
    this.sidePanelOpen = false;
    this.chatAreaWidth = 100;
    this.updatePanelWidths();
  },

  // 展开对话区域
  expandChatArea() {
    this.chatAreaOpen = true;
    this.chatAreaWidth = 50;
    this.sidePanelWidth = 50;
    this.updatePanelWidths();
  },

  // 展开侧边栏
  expandSidePanel() {
    this.sidePanelOpen = true;
    this.chatAreaWidth = 50;
    this.sidePanelWidth = 50;
    this.updatePanelWidths();
  },

  // 重置面板大小
  resetPanelSizes() {
    this.chatAreaWidth = 50;
    this.sidePanelWidth = 50;
    this.chatAreaOpen = true;
    this.sidePanelOpen = true;
    this.updatePanelWidths();
  },

  // 更新面板宽度样式（用于非拖拽时的调整）
  updatePanelWidths() {
    this.$nextTick(() => {
      const chatArea = this.$refs.chatAreaRef;
      const sidePanel = this.$refs.sidePanelRef;
      
      if (!chatArea || !sidePanel) {
        return;
      }
      
      if (this.chatAreaOpen && this.sidePanelOpen) {
        chatArea.style.width = `${this.chatAreaWidth}%`;
        sidePanel.style.width = `${this.sidePanelWidth}%`;
      } else if (this.chatAreaOpen) {
        chatArea.style.width = '100%';
      } else if (this.sidePanelOpen) {
        sidePanel.style.width = '100%';
      }
    });
  },

  // 处理窗口大小变化
  handleResize() {
    if (this.chatAreaOpen && this.sidePanelOpen) {
      this.updatePanelWidths();
    }
  },
  // 修改 openExtensionInWindow 方法
  async openExtensionInWindow(extension) {
    const url = await this.getExtensionURL(extension);   // ⬅️ 同样先启动/拿地址

    // 下面逻辑你原来就有，只把 url 换成异步得到的即可
    this.showExtensionsDialog = false;
    this.messages[0].content = extension.systemPrompt || '';
    let windowWidth = 800;
    let windowHeight = 600;
    if (window.electronAPI && window.electronAPI.openExtensionWindow) {
      try {
        if (extension.enableVrmWindowSize){
          console.log('VRM window size enabled')
          windowWidth = this.VRMConfig.windowWidth;
          windowHeight = this.VRMConfig.windowHeight
        }
        else{
          windowWidth = extension.width || 800;
          windowHeight = extension.height || 600;
        }
        const windowId = await window.electronAPI.openExtensionWindow(`${this.partyURL}${url}`, {
          id: extension.id,
          name: extension.name,
          transparent: extension.transparent || false,
          width: windowWidth,
          height: windowHeight,
        });
        console.log(`Extension window opened with ID: ${windowId}`);
      } catch (error) {
        console.error('Failed to open extension window:', error);
        window.open(`${this.partyURL}${url}`, '_blank');
      }
    } else {
      window.open(`${this.partyURL}${url}`, '_blank');
    }
  },
  async sherpaModelStatus() {
    const res = await fetch('/sherpa-model/status')
    if (!res.ok) return
    const { exists, model } = await res.json()
    this.sherpaModelExists = exists
    this.sherpaModelName  = model ?? ''   // 后端没返回时留空
  },

  async sherpaDownload(source = 'modelscope') {
      if (this.sherpaEventSource) this.sherpaEventSource.close()
      this.sherpaDownloading = true
      this.sherpaPercent = 0
      
      // 确保在 EventSource 实例化之前设置状态
      this.sherpaEventSource = null

      const es = new EventSource(`/sherpa-model/download/${source}`)
      this.sherpaEventSource = es
      
      // 监听消息流
      es.onmessage = e => {
          let data
          try {
              data = JSON.parse(e.data)
          } catch (error) {
              console.error('Failed to parse download progress data:', e.data, error)
              return
          }

          // --------------------------------------
          // 核心修复逻辑：处理多文件聚合进度
          // --------------------------------------
          
          // 1. 检查下载是否完成或失败
          if (data.status === 'complete') {
              es.close()
              this.sherpaDownloading = false
              this.sherpaPercent = 100
              this.sherpaModelStatus()
              showNotification(this.t('modelDownloadSuccess'))
              return
          }

          if (data.status === 'failed') {
              es.close()
              this.sherpaDownloading = false
              showNotification(this.t('modelDownloadFailed') + (data.error || ''), 'error')
              return
          }

          // 2. 聚合所有文件的进度
          let totalDone = 0
          let grandTotal = 0

          if (data.files && data.files.length > 0) {
              data.files.forEach(file => {
                  totalDone += file.done || 0
                  grandTotal += file.total || 0
                  // 检查是否有任何单个文件失败
                  if (file.failed) {
                      es.close()
                      this.sherpaDownloading = false
                      showNotification(this.t('modelDownloadFailed') + `: ${file.filename} 失败`, 'error')
                  }
              })
          }

          // 3. 计算整体百分比
          this.sherpaPercent = grandTotal > 0 ? Math.round((totalDone / grandTotal) * 100) : 0
      }
      
      // 监听错误
      es.onerror = () => {
          // 如果 EventSource 在没有收到 close 消息的情况下关闭，通常意味着错误
          es.close()
          this.sherpaDownloading = false
          showNotification(this.t('modelDownloadFailed'), 'error')
          this.sherpaModelStatus() // 再次检查状态，以防实际已下载完成
      }
  },

  async sherpaRemove() {
    try {
      const res = await fetch('/sherpa-model/remove', { method: 'DELETE' })
      if (!res.ok) throw new Error()
      showNotification(this.t('deleteSuccess'))
      this.sherpaModelStatus()
    } catch {
      showNotification(this.t('deleteFailed'),'error')
    }
  },

  async loadSherpaStatus() {
    await this.sherpaModelStatus()
  },

    /**
     * 检查 MiniLM 模型状态 (是否存在)
     */
    async minilmModelStatus() {
        try {
            const res = await fetch('/minilm-model/status');
            if (!res.ok) throw new Error('Failed to fetch status');
            const data = await res.json();
            this.minilmModelExists = data.exists;
        } catch (error) {
            console.error("Error checking MiniLM model status:", error);
            this.minilmModelExists = false; // 假设网络错误导致无法检查，也视为不存在
        }
    },

    /**
     * 下载 MiniLM 模型
     * @param {string} source - 下载源: 'modelscope' 或 'huggingface'
     */
    async minilmDownload(source = 'modelscope') {
        if (this.minilmEventSource) this.minilmEventSource.close();
        
        this.minilmDownloading = true;
        this.minilmPercent = 0;
        this.minilmEventSource = null;

        const es = new EventSource(`/minilm-model/download/${source}`);
        this.minilmEventSource = es;
        
        // 监听消息流
        es.onmessage = async e => {
            let data;
            try {
                // 后端会发送 JSON 格式的进度数据
                data = JSON.parse(e.data);
            } catch (error) {
                // 后端可能会发送 'close' 这样的非 JSON 消息
                if (e.data === 'close') {
                    es.close();
                }
                console.error('Failed to parse download progress data:', e.data, error);
                return;
            }

            // 1. 检查下载是否完成或失败
            if (data.status === 'complete') {
                es.close();
                this.minilmDownloading = false;
                this.minilmPercent = 100;

                // 1. 通知后端热重载
                await fetch('/minilm/reload', { method: 'POST' });

                // 2. 再刷新一次存在状态（此时一定为 true）
                await this.minilmModelStatus();

                if (typeof showNotification === 'function') {
                    showNotification(this.t('modelDownloadSuccess'));
                }
                return;
            }

            if (data.status === 'failed') {
                es.close();
                this.minilmDownloading = false;
                // 尝试从 files 列表中提取具体的错误信息
                const firstError = data.files.find(f => f.failed)?.error || '';
                if (typeof showNotification === 'function') {
                    showNotification(this.t('modelDownloadFailed') + (firstError ? `: ${firstError}` : ''), 'error');
                }
                return;
            }

            // 2. 聚合所有文件的进度
            let totalDone = 0;
            let grandTotal = 0;

            if (data.files && data.files.length > 0) {
                let hasFailedFile = false;
                data.files.forEach(file => {
                    totalDone += file.done || 0;
                    grandTotal += file.total || 0;
                    
                    // 检查是否有任何单个文件失败 (后端已经在 status='failed' 中处理了，这里做冗余检查)
                    if (file.failed) {
                        hasFailedFile = true;
                    }
                });

                if (hasFailedFile) {
                      // 如果检测到文件失败，但 status 还没有被后端更新为 'failed'，则手动关闭和报错
                      es.close();
                      this.minilmDownloading = false;
                      const failedFile = data.files.find(f => f.failed);
                      if (typeof showNotification === 'function') {
                        showNotification(this.t('modelDownloadFailed') + `: ${failedFile.filename} 失败`, 'error');
                      }
                      return;
                }
            }

            // 3. 计算整体百分比
            this.minilmPercent = grandTotal > 0 ? Math.round((totalDone / grandTotal) * 100) : 0;
        };
        
        // 监听错误
        es.onerror = () => {
            // 如果 EventSource 在没有收到 close 消息的情况下关闭，通常意味着错误
            if (this.minilmEventSource) {
                this.minilmEventSource.close();
            }
            this.minilmDownloading = false;
            if (typeof showNotification === 'function') {
                showNotification(this.t('modelDownloadFailed') + ' (Network/Connection Error)', 'error');
            }
            this.minilmModelStatus(); // 再次检查状态，以防实际已下载完成
        };
    },

    /**
     * 删除本地 MiniLM 模型
     */
    async minilmRemove() {
        try {
            // 使用 Element Plus 确认对话框来增加安全性（如果可用）
            // 示例：await this.$confirm('确定删除 MiniLM 模型吗？', '警告', { type: 'warning' })

            const res = await fetch('/minilm-model/remove', { method: 'DELETE' });
            if (!res.ok) throw new Error();
            
            if (typeof showNotification === 'function') {
                showNotification(this.t('deleteSuccess'));
            }
            this.minilmModelStatus(); // 刷新模型存在状态
        } catch (error) {
            if (typeof showNotification === 'function') {
                showNotification(this.t('deleteFailed') + (error.message || ''), 'error');
            }
        }
    },

  async updatePlugin(plugin) {
    // 临时响应式标记
    plugin._updating = true // 发送更新请求
    try {
      const res = await fetch(`/api/extensions/${plugin.id}/update`, { method: 'PUT' })
      if (!res.ok) throw new Error(await res.text())
      showNotification(this.t('updateSuccess'))
      // 更新完后刷新本地列表，重新标 installed 状态
      this.fetchRemotePlugins();
    } catch (e) {
      showNotification(this.t('updateFailed') + ': ' + e.message, 'error')
    } finally {
      plugin._updating = false
    }
  },

    // 打开向量库交互主弹窗
    async openVectorDialog(mid) {
      this.vectorDialogVisible = true
      this.vectorDialogMemoryId = mid
      // 取 memory 名字只是为了标题展示
      this.vectorDialogMemoryName = this.memories.find(m => m.id === mid)?.name || mid
      await this.loadVectorTable(mid)
    },

    // 读取记忆内容
    async loadVectorTable(mid) {
      this.vectorLoading = true
      try {
        const res = await fetch(`/memory/${mid}`)
        if (!res.ok) throw new Error(await res.text())
        // 后端已平铺，直接赋值
        this.vectorTable = await res.json()
      } catch (e) {
        this.vectorTable = []
        console.error(e)
      } finally {
        this.vectorLoading = false
      }
    },

    // 新增记忆
    async addVectorRow() {
      if (!this.newVectorText.trim()) return
      try {
        const mid = this.vectorDialogMemoryId
        const res = await fetch(`/memory/${mid}`, {
          
        })
      } finally {
        this.vectorLoading = false
      }
    },

  startEditRow(tableIndex) {
    const row = this.vectorTable[tableIndex]
    this.editRowIdx = row.idx
    this.editRowText = row.text
    this.editRowVisible = true
  },
  async submitEditRow() {
    if (!this.editRowText.trim()) return
    try {
      const mid = this.vectorDialogMemoryId
      const res = await fetch(`/memory/${mid}/${this.editRowIdx}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_text: this.editRowText.trim() })
      })
      if (!res.ok) throw new Error(await res.text())
      this.editRowVisible = false
      await this.loadVectorTable(mid)
    } catch (e) {
      showNotification(e.message, 'error')
    }
  },
  async deleteVectorRow(idx) {
    try {
      const mid = this.vectorDialogMemoryId
      const res = await fetch(`/memory/${mid}/${idx}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      await this.loadVectorTable(mid)
    } catch (e) {
      showNotification(e.message, 'error')
    }
  },
  /* 探针 */
  async probeNode() {
    const res = await fetch('/api/node/probe');
    const { installed } = await res.json();
    this.nodeInstalled = installed;
  },

  /* 一键安装 */
  async installNode() {
    this.nodeInstalling = true;
    this.nodeProgress = 0;
    try {
      // 1. 发起安装
      const res = await fetch('/api/node/install', { method: 'POST' });
      const { task_id } = await res.json();

      // 2. 轮询进度
      this.nodeTimer = setInterval(async () => {
        const progRes = await fetch(`/api/node/progress/${task_id}`);
        const { percent, status } = await progRes.json();
        this.nodeProgress = Math.round(percent);

        if (status === 'finished') {
          clearInterval(this.nodeTimer);
          this.nodeInstalling = false;
          this.nodeInstalled = true;
          this.$message.success(this.t('installSuccess'));
        } else if (status === 'error') {
          clearInterval(this.nodeTimer);
          this.nodeInstalling = false;
          this.$message.error(this.t('installFail'));
        }
      }, 1000);
    } catch (e) {
      this.nodeInstalling = false;
      this.$message.error(this.t('installFail'));
    }
  },

    /* ===== uv 相关 ===== */
  async probeUv() {
    const res = await fetch('/api/uv/probe');
    const { installed } = await res.json();
    this.uvInstalled = installed;
  },

  async installUv() {
    this.uvInstalling = true;
    this.uvProgress = 0;
    try {
      const res = await fetch('/api/uv/install', { method: 'POST' });
      const { task_id } = await res.json();

      this.uvTimer = setInterval(async () => {
        const progRes = await fetch(`/api/uv/progress/${task_id}`);
        const { percent, status } = await progRes.json();
        this.uvProgress = Math.round(percent);

        if (status === 'finished') {
          clearInterval(this.uvTimer);
          this.uvInstalling = false;
          this.uvInstalled = true;
          this.$message.success(this.t('installUvSuccess'));
        } else if (status === 'error') {
          clearInterval(this.uvTimer);
          this.uvInstalling = false;
          this.$message.error(this.t('installUvFail'));
        }
      }, 1000);
    } catch (e) {
      this.uvInstalling = false;
      this.$message.error(this.t('installUvFail'));
    }
  },
  /* ===== git ===== */
  async probeGit() {
    const res = await fetch('/api/git/probe');
    const { installed } = await res.json();
    this.gitInstalled = installed;
  },

  async installGit() {
    this.gitInstalling = true;
    this.gitProgress = 0;
    try {
      const res = await fetch('/api/git/install', { method: 'POST' });
      const { task_id } = await res.json();

      this.gitTimer = setInterval(async () => {
        const progRes = await fetch(`/api/git/progress/${task_id}`);
        const { percent, status } = await progRes.json();
        this.gitProgress = Math.round(percent);

        if (status === 'finished') {
          clearInterval(this.gitTimer);
          this.gitInstalling = false;
          this.gitInstalled = true;
          this.$message.success(this.t('installGitSuccess'));
        } else if (status === 'error') {
          clearInterval(this.gitTimer);
          this.gitInstalling = false;
          this.$message.error(this.t('installGitFail'));
        }
      }, 1000);
    } catch (e) {
      this.gitInstalling = false;
      this.$message.error(this.t('installGitFail'));
    }
  },
  async openLogDialog() {
    this.showLogDialog = true;
    await this.fetchLogs();
    // 自动滚动到底部
    this.$nextTick(() => {
      if (this.$refs.logContainer) {
        this.$refs.logContainer.scrollTop = this.$refs.logContainer.scrollHeight;
      }
    });
  },

  async fetchLogs() {
    if (window.electronAPI) {
      try {
        this.logContent = await window.electronAPI.getBackendLogs();
      } catch (e) {
        this.logContent = 'Failed to load logs: ' + e.message;
      }
    }
  },
  async fetchSystemVoices() {
      this.isLoadingSystemVoices = true;
      try {
        // 使用 fetch API 调用后端接口
        const response = await fetch('/system/voices'); // 请根据你的API前缀调整
        
        if (!response.ok) {
            // 处理 HTTP 错误状态（如 404, 500）
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data && data.voices) {
          this.systemVoices = data.voices;
          
          // 如果当前没有选中的音色，或者选中的音色不在列表里，默认选中第一个
          const currentVoiceValid = this.systemVoices.some(v => v.id === this.ttsSettings.systemVoiceName);
          if (!this.ttsSettings.systemVoiceName || !currentVoiceValid) {
             if (this.systemVoices.length > 0) {
               this.ttsSettings.systemVoiceName = this.systemVoices[0].id;
               this.autoSaveSettings(); // 保存默认选择
             }
          }
        }
      } catch (error) {
        console.error("获取系统音色失败:", error);
        if (this.$message) {
           this.$message.error(`获取系统音色列表失败: ${error.message}`);
        }
      } finally {
        this.isLoadingSystemVoices = false;
      }
    },

  addTableEnhancements() {
    this.$nextTick(() => {
      const tables = document.querySelectorAll('.markdown-body table');
      
      tables.forEach((table) => {
        if (table.parentElement.classList.contains('markdown-table-wrapper')) return;

        // 1. 创建容器
        const wrapper = document.createElement('div');
        wrapper.className = 'markdown-table-wrapper';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);

        // 2. 创建按钮
        const btn = document.createElement('button');
        btn.className = 'table-download-btn';
        // 使用 fa-file-excel 图标，更直观
        btn.innerHTML = '<i class="fa-solid fa-file-excel"></i> XLSX';
        btn.title = '导出为 Excel 文件';
        
        // 3. 绑定点击事件 (调用新的 exceljs 逻辑)
        btn.onclick = async (e) => {
          e.stopPropagation();
          // 添加加载状态反馈（可选）
          const originalText = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 导出中...';
          btn.disabled = true;
          
          try {
            await this.downloadTableAsXLSX(table);
          } catch (error) {
            console.error('Excel 导出失败:', error);
            this.$message?.error('导出失败，请重试');
          } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
          }
        };

        wrapper.appendChild(btn);
      });
    });
  },

  /**
   * 使用 ExcelJS 生成真正的 .xlsx 文件
   */
  async downloadTableAsXLSX(tableElement) {
    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet('数据导出');

    // --- 1. 提取 HTML 表格数据 ---
    const rows = tableElement.querySelectorAll('tr');
    
    // 遍历 HTML 行
    rows.forEach((row, rowIndex) => {
      const cells = row.querySelectorAll('td, th');
      const rowData = [];
      
      cells.forEach(cell => {
        // 获取纯文本
        rowData.push(cell.innerText.trim());
      });
      
      // 添加到 Worksheet
      const excelRow = worksheet.addRow(rowData);
    });

    // --- 2. 美化 Excel 样式 (Pro 模式) ---
    
    // 2.1 设置表头样式 (第一行)
    const headerRow = worksheet.getRow(1);
    headerRow.font = { 
      name: '微软雅黑', 
      bold: true, 
      color: { argb: 'FFFFFFFF' } // 白字
    };
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF1E849B' } // 使用你的主题色 (深青色)
    };
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' };

    // 2.2 自动计算列宽
    worksheet.columns.forEach(column => {
      let maxLength = 0;
      column.eachCell({ includeEmpty: true }, cell => {
        const columnLength = cell.value ? cell.value.toString().length : 10;
        if (columnLength > maxLength) maxLength = columnLength;
      });
      // 限制最大宽度，防止太宽
      column.width = maxLength < 10 ? 10 : (maxLength > 50 ? 50 : maxLength + 2);
    });

    // 2.3 添加边框
    worksheet.eachRow((row, rowNumber) => {
      row.eachCell((cell) => {
        cell.border = {
          top: { style: 'thin', color: { argb: 'FFDCDFE6' } },
          left: { style: 'thin', color: { argb: 'FFDCDFE6' } },
          bottom: { style: 'thin', color: { argb: 'FFDCDFE6' } },
          right: { style: 'thin', color: { argb: 'FFDCDFE6' } }
        };
        // 内容垂直居中
        cell.alignment = { ...cell.alignment, vertical: 'middle', wrapText: true };
      });
    });

    // --- 3. 生成并下载文件 ---
    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[-T:]/g, "");
    link.href = URL.createObjectURL(blob);
    link.download = `table_export_${timestamp}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  },

    // [A2UI 新增] 处理用户点击操作
    handleA2UIAction(msg) {
      console.log('A2UI Action Triggered:', msg);
      this.userInput = msg;
      this.sendMessage();
    },

    // [A2UI 新增] 拆分消息内容为 文本/UI 段
    splitMessageContent(content) {
      if (!content) return [];
      const segments = [];
      const regex = /```a2ui\s*([\s\S]*?)\s*```/g;
      
      let lastIndex = 0;
      let match;

      while ((match = regex.exec(content)) !== null) {
        if (match.index > lastIndex) {
          const textPart = content.slice(lastIndex, match.index);
          if (textPart) segments.push({ type: 'text', content: textPart });
        }

        try {
          const uiConfig = JSON.parse(match[1]);
          segments.push({ type: 'ui', content: uiConfig });
        } catch (e) {
          segments.push({ type: 'text', content: match[0] });
        }
        lastIndex = regex.lastIndex;
      }

      if (lastIndex < content.length) {
        segments.push({ type: 'text', content: content.slice(lastIndex) });
      }

      return segments;
    },

}
