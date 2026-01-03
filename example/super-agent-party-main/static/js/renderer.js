// 在页面加载完成后添加 content-loaded 类
document.addEventListener('DOMContentLoaded', function() {
  // 设置一个短暂的延迟，确保所有资源都已加载
  setTimeout(function() {
    document.body.classList.add('content-loaded');
  }, 100);
});

// ==========================================
// 1. 定义 A2UI 渲染组件 (支持 Markdown 渲染)
// ==========================================
const A2UIRendererComponent = {
  name: 'A2UIRenderer',
  components: {}, 
  template: `
    <div :class="['a2ui-root', isSelfContained ? 'a2ui-root-clean' : 'a2ui-root-boxed']">
      
      <!-- 根标题 -->
      <div v-if="uiConfig.props && uiConfig.props.title && !isSelfContained" class="a2ui-title">
        {{ uiConfig.props.title }}
      </div>
      <!-- 根描述 (也支持 MD) -->
      <div 
        v-if="uiConfig.props && uiConfig.props.description && !isSelfContained" 
        class="a2ui-text-content markdown-body" 
        style="color: var(--el-text-color-secondary); font-size: 13px; margin-bottom: 15px;"
        v-html="renderMarkdown(uiConfig.props.description)"
      ></div>

      <el-form :model="formData" label-position="top" size="default" @submit.prevent>
        
        <div :class="containerClass">
          
          <template v-for="(item, index) in normalizedChildren" :key="index">
            
            <!-- 1. Input -->
            <el-form-item 
              v-if="item.type === 'Input'" 
              :label="item.props.label" 
              style="margin-bottom: 15px; flex: 1; min-width: 200px;"
            >
              <el-input 
                v-model="formData[item.props.key || ('input_'+index)]" 
                :placeholder="item.props.placeholder || '请输入...'"
                size="large"
              >
                <template #append v-if="item.props.action === 'search'">
                  <el-button @click="handleAction(item, formData[item.props.key || ('input_'+index)])">
                    <i class="fa-solid fa-magnifying-glass"></i>
                  </el-button>
                </template>
              </el-input>
            </el-form-item>

            <!-- 2. Select -->
            <el-form-item 
              v-if="item.type === 'Select'" 
              :label="item.props.label"
              style="margin-bottom: 15px; flex: 1;"
            >
              <el-select 
                v-model="formData[item.props.key]" 
                :placeholder="item.props.placeholder || '请选择'" 
                style="width: 100%"
                size="large"
              >
                <el-option 
                  v-for="(opt, oIdx) in item.props.options" 
                  :key="oIdx" 
                  :label="isObj(opt) ? opt.label : opt" 
                  :value="isObj(opt) ? opt.value : opt" 
                />
              </el-select>
            </el-form-item>

            <!-- 3. Text (★ 修复点：使用 v-html + Markdown) -->
            <!-- 添加 markdown-body 类以复用你的全局 MD 样式 -->
            <div 
              v-if="item.type === 'Text'" 
              class="a2ui-text-content markdown-body"
              v-html="renderMarkdown(item.props.content)"
            ></div>

            <!-- 4. Divider -->
            <el-divider 
              v-if="item.type === 'Divider'" 
              style="margin: 18px 0; border-color: var(--el-border-color-lighter);" 
            />

            <!-- 5. Group -->
            <div v-if="item.type === 'Group'" class="a2ui-group-container">
               <div v-if="item.props && item.props.title" style="width: 100%; font-weight: bold; margin-bottom: 8px; font-size: 14px;">
                  {{ item.props.title }}
               </div>
              <!-- ★ 修改点：添加 :shared-form-data="formData" -->
              <a2-u-i-renderer 
                v-for="(child, cIdx) in item.children" 
                :key="cIdx" 
                :config="child"
                :shared-form-data="formData" 
                @action="relayAction"
                style="flex: 1; min-width: auto;" 
              />
            </div>

            <!-- 6. List -->
            <div v-if="item.type === 'List'" class="a2ui-list">
              <div 
                v-for="(listItem, lIdx) in item.props.items" 
                :key="lIdx" 
                class="a2ui-list-item"
                @click="handleManualAction('点击条目', listItem.title)"
              >
                <div class="a2ui-list-title">{{ listItem.title }}</div>
                <div class="a2ui-list-desc">{{ listItem.description }}</div>
                <div class="a2ui-list-meta">
                  <span v-if="listItem.source" class="tag">{{ listItem.source }}</span>
                  <span class="time">{{ listItem.timestamp }}</span>
                </div>
              </div>
            </div>

            <!-- 7. Card -->
            <el-card 
              v-if="item.type === 'Card'" 
              shadow="hover" 
              class="a2ui-inner-card"
            >
              <template #header v-if="item.props.title">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: bold; font-size: 16px;">{{ item.props.title }}</span>
                  <span v-if="item.props.subtitle" style="font-size: 12px; color: #909399; font-weight: normal;">{{ item.props.subtitle }}</span>
                </div>
              </template>
              
              <!-- ★ 修复点 1：独立渲染 Card 的 content，不再使用 v-else -->
              <!-- 这样，无论有没有 children，只要 content 存在就会显示 -->
              <div 
                v-if="item.props.content || item.props.description" 
                class="a2ui-card-desc markdown-body"
                style="margin-bottom: 15px;"
              >
                <div v-if="Array.isArray(item.props.content)">
                    <div v-for="(line, lIdx) in item.props.content" :key="lIdx" v-html="renderMarkdown(line)"></div>
                </div>
                <div v-else-if="item.props.content" v-html="renderMarkdown(item.props.content)"></div>
                <div v-else-if="item.props.description" v-html="renderMarkdown(item.props.description)"></div>
              </div>

              <!-- ★ 修复点 2：独立渲染 Card 的 children -->
              <div v-if="item.children && item.children.length > 0">
                 <!-- ★ 修改点：添加 :shared-form-data="formData" -->
                 <a2-u-i-renderer 
                    v-for="(child, ccIdx) in item.children" 
                    :key="ccIdx" 
                    :config="child"
                    :shared-form-data="formData"
                    @action="relayAction"
                 />
              </div>

              <div class="tags" v-if="item.props.tags" style="margin-top: 12px;">
                <el-tag v-for="tag in item.props.tags" :key="tag" size="default" effect="plain" style="margin-right: 6px;">
                  {{ tag }}
                </el-tag>
              </div>

              <div v-if="item.props.actions" class="a2ui-card-actions">
                <el-button 
                    v-for="(btn, bIdx) in item.props.actions"
                    :key="bIdx"
                    :type="bIdx === item.props.actions.length - 1 ? 'primary' : ''"
                    size="default"
                    @click="handleManualAction(btn.label, item.props.title)"
                >
                    {{ btn.label }}
                </el-button>
              </div>
            </el-card>

            <!-- 8. Button (Description 也支持 Markdown) -->
            <div 
              v-if="item.type === 'Button'" 
              :style="buttonStyle"
            >
              <el-button 
                v-if="item.props.description"
                :type="resolveBtnType(item.props)"
                @click="handleAction(item)" 
                :disabled="isSubmitted"
                size="large"
                style="height: auto; padding: 12px 20px; text-align: left; display: inline-flex; flex-direction: column; align-items: flex-start; line-height: 1.4; width: 100%;"
              >
                <span style="font-weight: 600; font-size: 15px;">{{ item.props.label }}</span>
                <span style="font-size: 12px; opacity: 0.8; font-weight: normal; margin-top: 4px;" v-html="renderMarkdown(item.props.description)"></span>
              </el-button>

              <el-button 
                v-else
                :type="resolveBtnType(item.props)" 
                @click="handleAction(item)" 
                :disabled="isSubmitted"
                size="large" 
                style="width: 100%; font-weight: 500;"
              >
                {{ item.props.label }}
              </el-button>
            </div>

            <!-- 9. Slider (滑块) -->
            <el-form-item 
              v-if="item.type === 'Slider'" 
              :label="item.props.label"
              style="margin-bottom: 15px; flex: 1; min-width: 200px;"
            >
              <div style="display: flex; align-items: center; width: 100%;">
                <el-slider 
                  v-model="formData[item.props.key]" 
                  :min="item.props.min || 0" 
                  :max="item.props.max || 100"
                  :step="item.props.step || 1"
                  show-input
                  size="default"
                  style="flex: 1; margin-right: 10px;"
                />
                <span v-if="item.props.unit" style="font-size: 12px; color: #909399;">{{ item.props.unit }}</span>
              </div>
            </el-form-item>

            <!-- 10. Switch (开关) -->
            <el-form-item 
              v-if="item.type === 'Switch'" 
              :label="item.props.label"
              style="margin-bottom: 15px;"
            >
              <el-switch 
                v-model="formData[item.props.key]" 
                :active-text="item.props.activeText || '开'"
                :inactive-text="item.props.inactiveText || '关'"
              />
            </el-form-item>

            <!-- 11. Radio (单选组) -->
            <el-form-item 
              v-if="item.type === 'Radio'" 
              :label="item.props.label"
              style="margin-bottom: 15px;"
            >
              <el-radio-group v-model="formData[item.props.key]">
                <el-radio 
                  v-for="(opt, oIdx) in item.props.options" 
                  :key="oIdx" 
                  :label="isObj(opt) ? opt.value : opt"
                  border
                >
                  {{ isObj(opt) ? opt.label : opt }}
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- 12. Checkbox (多选组) -->
            <el-form-item 
              v-if="item.type === 'Checkbox'" 
              :label="item.props.label"
              style="margin-bottom: 15px;"
            >
              <el-checkbox-group v-model="formData[item.props.key]">
                <el-checkbox 
                  v-for="(opt, oIdx) in item.props.options" 
                  :key="oIdx" 
                  :label="isObj(opt) ? opt.value : opt"
                >
                  {{ isObj(opt) ? opt.label : opt }}
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <!-- 13. DatePicker (日期选择) -->
            <el-form-item 
              v-if="item.type === 'DatePicker'" 
              :label="item.props.label"
              style="margin-bottom: 15px;"
            >
              <el-date-picker
                v-model="formData[item.props.key]"
                :type="item.props.subtype || 'date'" 
                :placeholder="item.props.placeholder || '选择日期'"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%;"
              />
            </el-form-item>
            
            <!-- 14. Rate (评分) -->
            <el-form-item 
              v-if="item.type === 'Rate'" 
              :label="item.props.label"
              style="margin-bottom: 15px;"
            >
              <el-rate 
                v-model="formData[item.props.key]" 
                allow-half 
                show-text
                :texts="['极差', '失望', '一般', '满意', '惊喜']"
              />
            </el-form-item>

             <!-- 15. Alert (提示条) -->
             <div v-if="item.type === 'Alert'" style="margin-bottom: 15px; width: 100%;">
                <el-alert
                    :title="item.props.title"
                    :type="item.props.variant || 'info'"
                    :show-icon="item.props.showIcon !== false"
                    :closable="false"
                >
                    <template #default v-if="item.props.content">
                        <div v-html="renderMarkdown(item.props.content)"></div>
                    </template>
                </el-alert>
             </div>

            <!-- 16. Code (代码块 - 独立渲染，无额外 wrapper) -->
            <div 
              v-if="item.type === 'Code'" 
              class="a2ui-code-block"
            >
              <div class="code-header">
                <span class="lang-tag">{{ item.props.language || 'text' }}</span>
                <div class="copy-btn" @click="copyToClipboard(item.props.content, $event)">
                  <i class="fa-regular fa-copy"></i>
                  <span>copy</span>
                </div>
              </div>
              <div class="code-body">
                <pre><code>{{ item.props.content }}</code></pre>
              </div>
            </div>

            <!-- 17. Table (表格组件) -->
            <div 
              v-if="item.type === 'Table'" 
              class="a2ui-table-wrapper"
            >
              <div class="a2ui-table-scroll">
                <table class="a2ui-table">
                  <thead>
                    <tr>
                      <th v-for="(head, hIdx) in item.props.headers" :key="hIdx">
                        {{ head }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rIdx) in item.props.rows" :key="rIdx">
                      <!-- 支持简单 HTML 或纯文本 -->
                      <td v-for="(cell, cIdx) in row" :key="cIdx" v-html="renderMarkdown(String(cell))"></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- 18. 朗读文本块 -->
            <div 
              v-if="item.type === 'TTSBlock'" 
              class="a2ui-tts-block"
              @click="handleTTS(item.props.content, item.props.voice)"
              title="点击播放语音"
            >
              <div class="tts-icon">
                <i class="fa-solid fa-volume-high"></i>
              </div>
              <div class="tts-body">
                <div class="tts-label" v-if="item.props.label">{{ item.props.label }}</div>
                <div class="tts-content markdown-body" v-html="renderMarkdown(item.props.content)"></div>
              </div>
              <div class="tts-action-hint">
                <i class="fa-solid fa-play"></i>
              </div>
            </div>

            <div 
              v-if="item.type === 'Audio'" 
              class="a2ui-audio-player"
              style="margin-bottom: 15px; width: 100%;"
            >
              <div v-if="item.props.title" style="font-weight: bold; margin-bottom: 5px; font-size: 14px;">
                {{ item.props.title }}
              </div>
              <audio controls style="width: 100%; height: 40px;" :src="item.props.src">
                您的浏览器不支持音频元素。
              </audio>
              <div v-if="item.props.description" style="font-size: 12px; color: #909399; margin-top: 4px;">
                {{ item.props.description }}
              </div>
            </div>

          </template>
        </div>
      </el-form>
    </div>
  `,
  props: {
    config: { type: Object, required: true, default: () => ({}) },
    sharedFormData: { type: Object, default: null } 
  },
  data() {
    return { internalFormData: {}, isSubmitted: false };
  },
  computed: {
    formData() {
      return this.sharedFormData || this.internalFormData;
    },
    uiConfig() {
      if (Array.isArray(this.config)) return { children: this.config };
      return this.config || {};
    },
    isSelfContained() {
      return ['Card', 'Group', 'List', 'Divider'].includes(this.uiConfig.type);
    },
    normalizedChildren() {
        const conf = this.uiConfig;
        if (conf.children && Array.isArray(conf.children)) {
            return conf.children;
        }
        if (conf.type) {
            return [conf];
        }
        return [];
    },
    containerClass() {
      if (this.uiConfig.type === 'Group') {
        return 'a2ui-group-container';
      }
      return 'a2ui-form-container';
    },
    buttonStyle() {
      if (this.uiConfig.type === 'Group') {
        return { margin: '0 5px', flex: '1' };
      }
      return { textAlign: 'right', marginTop: '10px', width: '100%' };
    }
  },
  created() {
    this.normalizedChildren.forEach((child, idx) => {
      // 需要绑定数据的组件列表
      const formComponents = ['Input', 'Select', 'Slider', 'Switch', 'Radio', 'Checkbox', 'DatePicker', 'Rate'];
      
      if (formComponents.includes(child.type)) {
         const key = (child.props && child.props.key) || (child.type.toLowerCase() + '_' + idx);
         
         if (this.formData[key] === undefined) {
            // 根据组件类型初始化默认值
            if (child.type === 'Checkbox') {
                this.formData[key] = []; // 多选必须初始化为数组
            } else if (child.type === 'Slider' || child.type === 'Rate') {
                this.formData[key] = child.props.min || 0; // 数字类型
            } else if (child.type === 'Switch') {
                this.formData[key] = child.props.defaultValue || false; // 布尔类型
            } else {
                this.formData[key] = ''; // 字符串类型
            }
         }
      }
    });
  },
  methods: {
    resetForm() {
      // 定义递归函数：遍历所有层级寻找表单项
      const traverseAndReset = (items) => {
        if (!Array.isArray(items)) return;

        items.forEach(item => {
          // 递归：如果是容器组件 (Group, Card 等)，继续深入查找
          if (item.children && Array.isArray(item.children)) {
            traverseAndReset(item.children);
          }

          // 处理：如果是表单组件，执行重置
          const formComponents = ['Input', 'Select', 'Slider', 'Switch', 'Radio', 'Checkbox', 'DatePicker', 'Rate'];
          
          if (formComponents.includes(item.type)) {
             // 获取绑定的 key
             const key = (item.props && item.props.key);
             if (!key) return; // 忽略无 key 的组件
             
             // 根据组件类型恢复默认值
             if (item.type === 'Checkbox') {
                 this.formData[key] = []; // 多选 -> 空数组
             } else if (item.type === 'Slider' || item.type === 'Rate') {
                 this.formData[key] = item.props.min || 0; // 数字 -> 0
             } else if (item.type === 'Switch') {
                 this.formData[key] = item.props.defaultValue || false; // 开关 -> false
             } else {
                 this.formData[key] = ''; // 其他文本类 -> 空字符串
             }
          }
        });
      };

      // 从当前组件的根子节点开始递归
      traverseAndReset(this.normalizedChildren);

      // 重置提交状态
      this.isSubmitted = false;
      
      // 界面反馈
      if (typeof showNotification === 'function') {
          showNotification('已重置所有选项', 'success');
      }
    },
    handleTTS(text, voice) {
      // 尝试调用根组件的 ClickToListen 方法
      if (this.$root && typeof this.$root.ClickToListen === 'function') {
        this.$root.ClickToListen(text, voice);
      } else {
        console.warn('A2UI: 根实例上未找到 ClickToListen 方法。');
        this.$emit('action', `TTS播放请求: ${text}`); // 降级处理
      }
    },

    async copyToClipboard(text, event) {
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        
        // 简单的交互反馈：修改按钮文字
        const btn = event.currentTarget;
        const originalHtml = btn.innerHTML;
        const span = btn.querySelector('span');
        if(span) span.innerText = 'Copied!';
        
        setTimeout(() => {
          btn.innerHTML = originalHtml;
        }, 2000);
        
        // 如果你有全局提示组件，也可以用：
        // showNotification('代码已复制', 'success');
      } catch (err) {
        console.error('复制失败:', err);
      }
    },

    // 渲染 Markdown 的核心方法
    renderMarkdown(text) {
        if (!text) return '';
        // 尝试使用全局定义的 md 对象
        if (typeof md !== 'undefined' && md.render) {
            return md.render(text);
        }
        // 兜底：如果没有 md，简单的换行处理
        return text.replace(/\n/g, '<br>');
    },
    isObj(val) {
      return val && typeof val === 'object';
    },
    resolveBtnType(props) {
        if (props.variant === 'primary') return 'primary';
        if (props.variant === 'danger') return 'danger';
        return props.type || 'default';
    },
handleAction(item, extraValue) {
      // ... (保留之前的 Clear/Reset 拦截逻辑) ...
      if (item.props.action === 'clear' || item.props.action === 'reset') {
          if (this.sharedFormData) {
              this.$emit('action', '_A2UI_RESET_ALL_'); 
          } else {
              this.resetForm();
          }
          return; 
      }

      // ---------------------------------------------------------
      // ★ 常规业务逻辑 (Submit / Search)
      // ---------------------------------------------------------
      this.isSubmitted = true;
      let payload = item.props.label;
      
      if (item.props.action === 'search' && extraValue) {
          payload = `搜索：${extraValue}`;
      }
      else if (item.props.action === 'submit') {
        const formDataKeys = Object.keys(this.formData);
        
        // 场景A: 单字段表单，直接发送 "标签：值"
        if (formDataKeys.length === 1 && this.formData[formDataKeys[0]]) {
            const singleValue = this.formData[formDataKeys[0]];
            payload = `${item.props.label}：${singleValue}`;
        } 
        // 场景B: 多字段表单，发送汇总详情
        else {
            let details = [];
            const findFieldLabel = (nodes, targetKey) => {
                for (const node of nodes) {
                    if (node.props && node.props.key === targetKey) return node.props.label;
                    if (node.children) {
                        const found = findFieldLabel(node.children, targetKey);
                        if (found) return found;
                    }
                }
                return targetKey; 
            };

            for (const [key, val] of Object.entries(this.formData)) {
                 if (val === undefined || val === '' || val === null || (Array.isArray(val) && val.length === 0)) continue;
                 
                 const label = findFieldLabel(this.normalizedChildren, key);
                 let displayVal = val;
                 details.push(`${label}：${displayVal}`);
            }
            
            if (details.length > 0) {
                // ============================================================
                // ★ 修复重点在此处 ★
                // 原代码：payload = `表单提交：\n${details.join('\n')}`;
                // 修改为：将按钮名称 (item.props.label) 明确拼接到消息头部
                // ============================================================
                payload = `提交操作：${item.props.label}\n表单数据：\n${details.join('\n')}`;
            } else {
                // 如果表单全是空的，保留按钮名称
                payload = `${item.props.label} (空表单提交)`;
            }
        }
      } 
      else if (item.props.data) {
          payload = `选择操作：${item.props.label} (ID:${item.props.data})`;
      }
      
      // 发送最终 payload 给父级
      this.$emit('action', payload);
    },

    handleManualAction(actionName, title) {
        this.$emit('action', `选择了：${title} - ${actionName}`);
    },
    relayAction(payload) {
        // ★ 拦截特殊信号：_A2UI_RESET_ALL_
        if (payload === '_A2UI_RESET_ALL_') {
            if (this.sharedFormData) {
                // 我还是子组件，继续像接力棒一样往上传
                this.$emit('action', '_A2UI_RESET_ALL_');
            } else {
                // 我是根组件！终于传到我这了，执行清空
                this.resetForm();
            }
            return; // ★ 拦截结束，不触发 sendMessage
        }

        // 普通消息：直接透传给上一层，最终触发 handleA2UIAction
        this.$emit('action', payload);
    }
  }
};

// ==========================================
// 2. 创建 Vue 应用
// ==========================================
const app = Vue.createApp({
  data() {
    return vue_data
  },
  // 在组件销毁时清除定时器
  beforeDestroy() {
    if (this.behaviorTimeTimer)   clearInterval(this.behaviorTimeTimer)
    if (this.behaviorNoInputTimer) clearInterval(this.behaviorNoInputTimer)
    if (this.vrmPollTimer) clearInterval(this.vrmPollTimer)
    clearInterval(this.behaviorCycleTimer);
    this.cycleTimers.forEach(timer => {
      if (timer) clearInterval(timer);
    });
    if (this.statusInterval) {
      clearInterval(this.statusInterval);
    }
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    window.removeEventListener('resize', this.checkMobile);
    this.shouldReconnectWs = false; // 设置标志位
    this.stopDanmuProcessor(); // 停止弹幕处理器
    this.disconnectWebSocket();
  },
  async mounted() {
    await this.probeNode();
    await this.probeUv(); 
    await this.probeGit();
    this.checkMobile();
    this.loadSherpaStatus();
    this.minilmModelStatus();
    window.addEventListener('resize', this.handleResize);
    if (isElectron) {
      this.checkServerPort();
    }
    window.addEventListener('keydown', this.handleKeyDown)
    window.addEventListener('keyup', this.handleKeyUp)
    window.addEventListener('resize', this.checkMobile);
    this.pollVRMStatus()   // 启动轮询
    if (isElectron) {
      this.isMac = window.electron.isMac;
      this.isWindows = window.electron.isWindows;
    }
    this.initWebSocket();
    this.highlightCode();
    this.initDownloadButtons();
    if (isElectron) {
      // 检查更新
      this.checkForUpdates();
      // 监听更新事件
      window.electronAPI.onUpdateAvailable((_, info) => {
        this.updateAvailable = true;
        this.updateInfo = info;
        showNotification(this.t('updateAvailable'), 'info');
      });
      window.electronAPI.onUpdateNotAvailable(() => {
        this.updateAvailable = false;
        this.updateInfo = null;
      });
      window.electronAPI.onUpdateError((_, err) => {
        showNotification(err, 'error');
      });
      window.electronAPI.onDownloadProgress((_, progress) => {
        this.downloadProgress = progress.percent;
        this.updateIcon = 'fa-solid fa-spinner fa-spin';
      });
      window.electronAPI.onUpdateDownloaded(() => {
        this.updateDownloaded = true;
        this.updateIcon = 'fa-solid fa-rocket';
      });
    }
    this.$nextTick(() => {
      this.initPreviewButtons();
    });
    this.$nextTick(() => {               // 保证 DOM 已渲染
      document.addEventListener('click', this._toggleHighlight, false);
    });
    document.documentElement.setAttribute('data-theme', this.systemSettings.theme);
    if (isElectron) {
      window.stopQQBotHandler = this.requestStopQQBotIfRunning;
      window.stopFeishuBotHandler = this.requestFeishuBotStopIfRunning;
      window.stopDiscordBotHandler = this.requestDiscordBotStopIfRunning;
      window.stopTelegramBotHandler = this.requestTelegramBotStopIfRunning;
      window.electronAPI.onWindowState((_, state) => {
        this.isMaximized = state === 'maximized'
      });
    }
    this.initTTSWebSocket();
    this.$nextTick(() => {
      this.generateQRCode(); // 生成二维码
    });
    // 1. 时间触发器（每秒扫一次）
    this.behaviorTimeTimer = setInterval(() => {
      if (!this.behaviorSettings.enabled) return
      const now = new Date()
      const hm = now.toLocaleTimeString('zh-CN', { hour12: false }) // HH:mm:ss
      const d  = now.getDay() // 0=周日
      this.behaviorSettings.behaviorList.forEach(b => {
        if (!b.enabled || b.trigger.type !== 'time') return
        const tv = b.trigger.time.timeValue
        const ds = b.trigger.time.days
        if (tv === hm) {
          if (ds.length === 0 || ds.includes(d)) {
            this.runBehavior(b)
            this.disableOnceBehavior(b)
          }
        }
      })
    }, 1000)

    // 2. 无-input 触发器（每 1s 检查一次）
    this.noInputSec = 0 // 连续无输入秒数
    this.behaviorNoInputTimer = setInterval(() => {
      if (!this.behaviorSettings.enabled) return
      this.behaviorSettings.behaviorList.forEach(b => {
        if (!b.enabled || b.trigger.type !== 'noInput') return
        const need = b.trigger.noInput.latency
        if (this.noInputFlag) {
          this.noInputSec++
          if (this.noInputSec >= need) {
            this.runBehavior(b)
            this.noInputSec = 0 // 触发后重置
          }
        } else {
          this.noInputSec = 0
        }
      })
    }, 1000)

   // 在 mounted() 函数中添加以下代码
  this.cycleTimers = []; // 存储所有周期触发器的定时器

  // 3. 周期触发器（每1秒检查一次）
  this.behaviorCycleTimer = setInterval(() => {
    if (!this.behaviorSettings.enabled) return;
    
    const now = new Date();
    this.behaviorSettings.behaviorList.forEach((b, index) => {
      if (!b.enabled || b.trigger.type !== 'cycle') return;
      
      // 检查是否已有定时器
      if (!this.cycleTimers[index]) {
        this.initCycleTimer(b, index);
      }
    });
  }, 1000); 
    this.scanExtensions(); // 扫描扩展
    if (this.ttsSettings && this.ttsSettings.engine === 'systemtts') {
      this.fetchSystemVoices();
    }
  },
  beforeUnmount() {
    clearInterval(this.nodeTimer);
    clearInterval(this.uvTimer); 
    clearInterval(this.gitTimer);
    if (isElectron) {
      delete window.stopQQBotHandler;
      delete window.stopFeishuBotHandler;
      delete window.stopDiscordBotHandler;
      delete window.stopTelegramBotHandler;
    }
    if (this.ttsWebSocket) {
      this.ttsWebSocket.close();
    }
    document.removeEventListener('click', this._toggleHighlight, false);
    window.removeEventListener('resize', this.handleResize);
  },
  watch: {
    messages: {
      handler() {
        // 这里的 setTimeout 是为了等待 Markdown 渲染库完成 DOM 更新
        setTimeout(() => {
          this.addTableEnhancements();
        }, 300); 
      },
      deep: true
    },

    'ttsSettings.engine': function(newVal) {
      if (newVal === 'systemtts') {
        // 如果列表为空，则去获取
        if (this.systemVoices.length === 0) {
          this.fetchSystemVoices();
        }
      }
    },
    'readConfig.longText': {
      immediate: true,
      async handler(val) {          // ← 加 async
        await this.$nextTick();     // ← 保证组件完成上一轮渲染
        if (!val?.trim()) {
          this.clearSegments();
          return;
        }
        this.reSegment();
      }
    },
    selectedCodeLang() {
      this.highlightCode();
    },
    modelProviders: {
      deep: true,
      handler(newProviders) {
        const existingIds = new Set(newProviders.map(p => p.id));
        // 自动清理无效的 selectedProvider
        [this.settings, this.reasonerSettings,this.visionSettings,this.KBSettings,this.text2imgSettings,this.ccSettings,this.qcSettings].forEach(config => {
          if (config.selectedProvider && !existingIds.has(config.selectedProvider)) {
            config.selectedProvider = null;
            // 可选项：同时重置相关字段
            config.model = '';
            config.base_url = '';
            config.api_key = '';
          }
          if (!config.selectedProvider && newProviders.length > 0) {
            config.selectedProvider = newProviders[0].id;
          }
        });
        [this.settings, this.reasonerSettings,this.visionSettings,this.KBSettings,this.text2imgSettings,this.ccSettings].forEach(config => {
          if (config.selectedProvider) this.syncProviderConfig(config);
        });
      }
    },
    'systemSettings.theme': {
      handler(newVal) {
        document.documentElement.setAttribute('data-theme', newVal);
        
        // 更新 mermaid 主题
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'loose',
          theme : ['dark','midnight','neon'].includes(newVal) ? 'dark' : 'default'
        });

        // 完整的主题色映射
        const themeColors = {
          light: '#21859c',      // 默认
          dark: '#ee7e00',       // 橙色
          midnight: '#21859c',   // 午夜蓝
          desert: '#d98236',     // 沙漠黄
          neon: '#ff2d95' ,       // 霓虹粉
          marshmallow: '#f5a5c3',  // Marshmallow 粉色
          ink: '#2c3e50',        // 墨水蓝
          party: '#ed7d00',        // 派对黄
          rainbow: '#845ec2',        // 彩虹
        };

        // 获取当前主题色
        const themeColor = themeColors[newVal] || themeColors.light;
        const root = document.documentElement;

        // 设置主色及其衍生色（Element Plus 需要完整的色系）
        root.style.setProperty('--el-color-primary', themeColor);
        root.style.setProperty('--el-color-primary-light-9', this.colorBlend(themeColor, '#ffffff', 0.1));
        root.style.setProperty('--el-color-primary-light-8', this.colorBlend(themeColor, '#ffffff', 0.2));
        root.style.setProperty('--el-color-primary-light-7', this.colorBlend(themeColor, '#ffffff', 0.3));
        root.style.setProperty('--el-color-primary-light-6', this.colorBlend(themeColor, '#ffffff', 0.4));
        root.style.setProperty('--el-color-primary-light-5', this.colorBlend(themeColor, '#ffffff', 0.5));
        root.style.setProperty('--el-color-primary-light-4', this.colorBlend(themeColor, '#ffffff', 0.6));
        root.style.setProperty('--el-color-primary-light-3', this.colorBlend(themeColor, '#ffffff', 0.7));
        root.style.setProperty('--el-color-primary-light-2', this.colorBlend(themeColor, '#ffffff', 0.8));
        root.style.setProperty('--el-color-primary-light-1', this.colorBlend(themeColor, '#ffffff', 0.9));
        root.style.setProperty('--el-color-primary-dark-1', this.colorBlend(themeColor, '#000000', 0.3));
        root.style.setProperty('--el-color-primary-dark-2', this.colorBlend(themeColor, '#000000', 0.2));
        root.style.setProperty('--el-color-primary-dark-3', this.colorBlend(themeColor, '#000000', 0.1));

        // 强制刷新 Element Plus 主题
        if (window.__ELEMENT_PLUS_INSTANCE__) {
          window.__ELEMENT_PLUS_INSTANCE__.config.globalProperties.$ELEMENT.reload();
        }
      },
      immediate: true
    },
    'systemSettings.language': {
      handler(newVal) {
        if (this.isElectron) {
          window.electronAPI.sendLanguage(newVal);
        }
      },
      immediate: true
    },
  },
  computed: {
    sidePanelText() {
      if (this.messages.length === 0) {
        return '';
      }
      
      // 过滤出所有助手消息并按时间倒序排列
      const assistantMessages = this.messages
        .filter(msg => msg.role === 'assistant')
        .reverse();
      
      // 找到第一个非空消息
      for (const msg of assistantMessages) {
        if (msg.pure_content && msg.pure_content.trim() !== '') {
          return msg.pure_content;
        }
      }
      
      // 如果没有找到符合条件的消息
      return '';
    },
  currentViewName() {
    return this.currentExtension ? this.currentExtension.name : this.t('defaultView');
  },
    /* 计算属性：默认模板 */
    defaultSidePanelHTML() {
      // 如果用户已给出自定义模板，就直接用
      if (this.sidePanelHTML) return this.sidePanelHTML;

      return `
        <div class="side-panel-default">
          <div class="side-panel-content markdown-body" v-data-mjx-disabled="true">
            ${this.formatMessage(this.sidePanelText)}
          </div>
        </div>`;
    },
    noInputFlag() {
      return !this.TTSrunning &&
             !this.ASRrunning &&
             !this.isInputting &&
             !this.isTyping
    },
    // 计算处理百分比
    processingPercentage() {
      if (this.totalChunksCount === 0) return 0;
      return Math.round((this.audioChunksCount / this.totalChunksCount) * 100);
    },
    
    // 生成进度文本
    processingProgressText() {
      if (this.totalChunksCount === 0) return this.t('waiting');
      
      return `${this.audioChunksCount} / ${this.totalChunksCount} (${this.processingPercentage}%)`;
    },
    
    // 根据状态设置进度条颜色
    progressStatus() {
      if (this.isReadRunning || this.isConvertingAudio) {
        if (this.processingPercentage >= 90) return 'success';
        if (this.processingPercentage >= 50) return '';
        return 'exception';
      }
      return 'success';
    },

    allChecked: {
      get() {
        return this.textFiles.length > 0 && this.selectedFiles.length === this.textFiles.length;
      },
      set(val) {
        this.selectedFiles = val ? this.textFiles.map(f => f.unique_filename) : [];
      }
    },
    indeterminate() {
      return (
        this.selectedFiles.length > 0 &&
        this.selectedFiles.length < this.textFiles.length
      );
    },
    // 图片全选状态
    allImagesChecked: {
      get() {
        return this.imageFiles.length > 0 && 
              this.selectedImages.length === this.imageFiles.length
      },
      set(val) {
        this.selectedImages = val 
          ? this.imageFiles.map(i => i.unique_filename) 
          : []
      }
    },
    
    // 视频全选状态
    allVideosChecked: {
      get() {
        return this.videoFiles.length > 0 && 
              this.selectedVideos.length === this.videoFiles.length
      },
      set(val) {
        this.selectedVideos = val 
          ? this.videoFiles.map(v => v.unique_filename) 
          : []
      }
    },
    sidebarStyle() {
      return {
        width: this.isMobile ? 
          (this.sidebarVisible ? '200px' : '0') : 
          (this.isCollapse ? '64px' : '200px')
      }
    },
    filteredSeparators() {
      const current = this.qqBotConfig.separators;
      const defaults = this.defaultSeparators;
      const custom = current
        .filter(s => !defaults.some(d => d.value === s))
        .map(s => ({
          label: `(${this.formatSeparator(s)})`,
          value: s
        }));
      return [...this.defaultSeparators, ...custom];
    },
    filteredClaudeModelProviders() {
      let vendors = ["Anthropic", "Deepseek", "siliconflow", "ZhipuAI", "moonshot", "aliyun", "modelscope","302.AI"];
      // this.modelProviders中，vendor在vendors中的，添加到filteredClaudeModelProviders
      return this.modelProviders.filter((item) => vendors.includes(item.vendor));
    },

    // 计算属性，判断配置是否有效
    isQQBotConfigValid() {
        return this.qqBotConfig.appid && this.qqBotConfig.secret;
    },
    isfeishuBotConfigValid() {
      return this.feishuBotConfig.appid && this.feishuBotConfig.secret;
    },
    filteredFeishuSeparators() {
      const current = this.feishuBotConfig.separators;
      const defaults = this.defaultSeparators;
      const custom = current
        .filter(s => !defaults.some(d => d.value === s))
        .map(s => ({
          label: `(${this.formatSeparator(s)})`,
          value: s
        }));
      return [...this.defaultSeparators, ...custom];
    },
    isTelegramBotConfigValid() {
      return this.feishuBotConfig.appid && this.feishuBotConfig.secret;
    },
    filteredTelegramSeparators() {
      const current = this.telegramBotConfig.separators;
      const defaults = this.defaultSeparators;
      const custom = current
        .filter(s => !defaults.some(d => d.value === s))
        .map(s => ({
          label: `(${this.formatSeparator(s)})`,
          value: s
        }));
      return [...this.defaultSeparators, ...custom];
    },
    isDiscordBotConfigValid() {
      return !!this.discordBotConfig.token;
    },
    filteredDiscordSeparators() {
      const current = this.discordBotConfig.separators;
      const defaults = this.defaultSeparators;
      const custom = current
        .filter(s => !defaults.some(d => d.value === s))
        .map(s => ({
          label: `(${this.formatSeparator(s)})`,
          value: s
        }));
      return [...this.defaultSeparators, ...custom];
    },
    // isWXBotConfigValid() {
    //     return this.WXBotConfig.nickNameList && this.WXBotConfig.nickNameList.length > 0;
    // },
    isLiveConfigValid() {
        if (this.liveConfig.bilibili_enabled) {
            if(this.liveConfig.bilibili_type === 'web'){
                return this.liveConfig.bilibili_room_id && this.liveConfig.bilibili_room_id.trim() !== '';
            }
            else if(this.liveConfig.bilibili_type === 'open_live'){
                return this.liveConfig.bilibili_ACCESS_KEY_ID !== '' &&
                this.liveConfig.bilibili_SECRET_ACCESS_KEY !== '' &&
                this.liveConfig.bilibili_APP_ID !== '' &&
                this.liveConfig.bilibili_ROOM_OWNER_AUTH_CODE !== '';
            }
        }
        else if (this.liveConfig.youtube_enabled) {
          return this.liveConfig.youtube_video_id !== '' &&
          this.liveConfig.youtube_api_key !== '';
        }
        else if (this.liveConfig.twitch_enabled) {
          return this.liveConfig.twitch_channel !== '' &&
          this.liveConfig.twitch_access_token !== '';
        }
        return false;
    },
    updateButtonText() {
      if (this.updateDownloaded) return this.t('installNow');
      if (this.downloadProgress > 0) return this.t('downloading');
      return this.t('updateAvailable');
    },
    allItems() {
      return [
        ...this.files.map(file => ({ ...file, type: 'file' })),
        ...this.images.map(image => ({ ...image, type: 'image' }))
      ];
    },
    sortedConversations() {
      return [...this.conversations].sort((a, b) => b.timestamp - a.timestamp);
    },
    filteredConversations() {
        const keyword = this.searchKeyword.toLowerCase()
        return [...this.conversations]
            .filter(conv => {
                // 匹配标题或消息内容
                const titleMatch = (conv.title || this.t('untitled')).toLowerCase().includes(keyword)
                const contentMatch = conv.messages?.some(msg => 
                    msg.content.toLowerCase().includes(keyword)
                )
                return titleMatch || contentMatch
            })
            .sort((a, b) => b.timestamp - a.timestamp)
    },
    iconClass() {
      return this.isExpanded ? 'fa-solid fa-compress' : 'fa-solid fa-expand';
    },
    hasEnabledA2AServers() {
      return Object.values(this.a2aServers).some(server => server.enabled);
    },
    hasEnabledLLMTools() {
      return this.llmTools.some(tool => tool.enabled);
    },
    hasEnabledKnowledgeBases() {
      return this.knowledgeBases.some(kb => kb.enabled)
    },
    hasEnabledMCPServers() {
      // 检查this.mcpServers中的sever中是否有disable为false的
      return Object.values(this.mcpServers).some(server => !server.disabled);
    },
    hasEnabledHttpTools() {
      return this.customHttpTools.some(tool => tool.enabled);
    },
    hasEnabledComfyUI() {
      return this.workflows.some(tool => tool.enabled);
    },
    hasEnabledStickerPacks() {
      return this.stickerPacks.some(pack => pack.enabled);
    },
    hasFiles() {
      return this.files.length > 0
    },
    hasImages() {
      return this.images.length > 0
    },
    formValid() {
      return !!this.newLLMTool.name && !!this.newLLMTool.type
    },
    defaultBaseURL() {
      switch(this.newLLMTool.type) {
        case 'openai': 
          return 'https://api.openai.com/v1'
        case 'ollama':
          return this.isdocker ? 
            'http://host.docker.internal:11434' : 
            'http://127.0.0.1:11434'
        default:
          return ''
      }
    },
    defaultApikey() {
      switch(this.newLLMTool.type) {
        case 'ollama':
          return 'ollama'
        default:
          return ''
      }
    },
    validProvider() {
      if (!this.newProviderTemp.vendor) return false
      if (this.newProviderTemp.vendor === 'custom') {
        return this.newProviderTemp.url.startsWith('http')
      }
      return true
    },
    vendorOptions() {
      return this.vendorValues.map(value => ({
        label: this.t(`vendor.${value}`), // 使用统一的翻译键
        value
      }));
    },
    MCPvendorOptions() {
      return this.MCPvendorValues.map(value => ({
        label: this.t(`MCPvendor.${value}`), // 使用统一的翻译键
        value
      }));
    },
    PromptOptions() {
      return this.promptValues.map(value => ({
        label: this.t(`prompt.${value}`), // 使用统一的翻译键
        value
      }));
    },
    CardOptions() {
      return this.cardValues.map(value => ({
        label: this.t(`card.${value}`), // 使用统一的翻译键
        value
      }));
    },
    themeOptions() {
      return this.themeValues.map(value => ({
        label: this.t(`theme.${value}`),
        value // 保持原始值（推荐）
      }));
    },
    hasAgentChanges() {
      return this.mainAgent !== 'super-model' || 
        Object.values(this.agents).some(a => a.enabled)
    },
    // 获取所有唯一的语言
    uniqueLanguages() {
      const languages = [...new Set(this.edgettsvoices.map(voice => voice.language))];
      return languages.sort();
    },
    
    // 根据选择的语言获取可用的性别
    uniqueGenders() {
      const voicesForLanguage = this.edgettsvoices.filter(voice => 
        voice.language === this.edgettsLanguage
      );
      const genders = [...new Set(voicesForLanguage.map(voice => voice.gender))];
      return genders.sort();
    },
    
    // 根据选择的语言和性别过滤语音
    filteredVoices() {
      return this.edgettsvoices.filter(voice => 
        voice.language === this.edgettsLanguage && 
        voice.gender === this.edgettsGender
      );
    },
    uniqueNewLanguages() {
      const languages = [...new Set(this.edgettsvoices.map(voice => voice.language))];
      return languages.sort();
    },
    uniqueNewGenders() {
      const voicesForLanguage = this.edgettsvoices.filter(voice => 
        voice.language === this.newTTSConfig.edgettsLanguage
      );
      const genders = [...new Set(voicesForLanguage.map(voice => voice.gender))];
      return genders.sort();
    },
    filteredNewVoices() {
      return this.edgettsvoices.filter(voice => 
        voice.language === this.newTTSConfig.edgettsLanguage && 
        voice.gender === this.newTTSConfig.edgettsGender
      );
    },
    selectedVendor() {
      return this.modelProviders.find(
        p => p.id === this.settings.selectedProvider
      );
    },
  },
  methods: {
    ...vue_methods,
  }
});

function showNotification(message, type = 'success') {
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);
  
  // 强制重绘确保动画生效
  void notification.offsetWidth;
  
  notification.classList.add('show');

  // 设置显示时间：错误提示显示5秒，其他提示显示2秒
  const duration = type === 'error' ? 5000 : 2000;

  setTimeout(() => {
    notification.classList.remove('show');
    notification.classList.add('hide');
    setTimeout(() => notification.remove(), 400);
  }, duration);
}

function removeNonAsciiTags(html) {
  // 匹配所有标签（包括开始标签和结束标签）
  // 例如：<旁白> 和 </旁白>
  const regex = /<\/?([^\s>]+)[^>]*>/g;
  
  return html.replace(regex, (match, tagName) => {
    // 检查标签名是否包含非 ASCII 字符
    const hasNonAscii = [...tagName].some(char => char.charCodeAt(0) > 127);
    
    // 如果标签名包含非 ASCII 字符，删除标签（但保留内容）
    if (hasNonAscii) {
      return '';
    }
    
    // 否则，保留标签
    return match;
  });
}

// 修改图标注册方式（完整示例）
app.use(ElementPlus);

// ==========================================
// ★ 修改点：注册 A2UI 组件
// ==========================================
app.component('a2-u-i-renderer', A2UIRendererComponent);

// 正确注册所有图标（一次性循环注册）
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 挂载应用
app.mount('#app');