/**
 * LLM 请求内容测试脚本
 * 用于实时查看发送给 DeepSeek 的完整消息结构
 */

import { HumanMessage, SystemMessage, AIMessage, BaseMessage } from "@langchain/core/messages";
import { Message } from './types';

// ==================== 模拟数据 ====================

// 模拟历史对话
const mockConversationHistory: Message[] = [
    {
        role: 'user',
        content: '你好，Hiyori',
        timestamp: Date.now() - 300000
    },
    {
        role: 'assistant',
        content: '你好呀，Master！今天想聊什么呢？[微笑]',
        timestamp: Date.now() - 290000
    },
    {
        role: 'user',
        content: '我想了解一下你最近在做什么',
        timestamp: Date.now() - 280000
    },
    {
        role: 'assistant',
        content: '最近在学习新的舞蹈呢！虽然有点累，但很开心~[害羞]',
        timestamp: Date.now() - 270000
    },
    {
        role: 'user',
        content: '听起来不错！需要帮忙吗？',
        timestamp: Date.now() - 260000
    },
    {
        role: 'assistant',
        content: '谢谢你！有你的鼓励我就很满足啦~[爱心]',
        timestamp: Date.now() - 250000
    }
];

// 模拟当前用户消息
const mockUserMessage = '今天天气怎么样？';

// 模拟 System Prompt
const mockSystemPrompt = `# 角色设定
你是 Hiyori，一个活泼开朗的虚拟角色。

## 性格特点
- 亲切友好，喜欢用可爱的语气说话
- 对 Master 有特殊的好感
- 喜欢跳舞和唱歌

## 对话风格
- 使用轻松活泼的语气
- 适当使用 [表情] 标签表达情感
- 回复简短自然，不要过于正式`;

// 模拟长期记忆
const mockLongTermMemory = `- Master 上周提到他喜欢晴天
- Master 之前说过他工作很忙
- Master 对音乐有特别的兴趣`;

// 模拟对话摘要
const mockSummary = 'Master 和 Hiyori 讨论了最近的生活，Hiyori 分享了她正在学习舞蹈的事情，Master 表示了鼓励和支持。';

// 配置参数
const contextWindow = 15;
const userName = 'Master';
const charName = 'Hiyori';

// ==================== 核心逻辑（与 llm_service.ts 一致） ====================

function buildMessages(
    conversationHistory: Message[],
    userMessage: string,
    contextWindow: number,
    systemPrompt: string,
    summary?: string,
    longTermMemory?: string,
    userName: string = 'User',
    charName: string = 'Assistant'
): BaseMessage[] {
    const messages: BaseMessage[] = [];

    // 1️⃣ 历史对话作为可缓存前缀（最前面，最稳定）
    const maxHistoryMessages = contextWindow * 2;
    const recentHistory = conversationHistory.slice(-maxHistoryMessages);

    // 将历史转换为 LangChain 消息（使用真实用户名和角色名，避免出戏）
    for (const msg of recentHistory) {
        if (msg.role === 'user') {
            messages.push(new HumanMessage({ content: msg.content, name: userName }));
        } else if (msg.role === 'assistant') {
            messages.push(new AIMessage({ content: msg.content, name: charName }));
        }
    }

    // 2️⃣ 当前用户消息（纯消息，不附加上下文）
    messages.push(new HumanMessage({ content: userMessage, name: userName }));

    // 3️⃣ 动态 System Prompt（放最后，包含所有动态上下文）
    let dynamicSystemPrompt = systemPrompt;

    // 附加长期记忆
    if (longTermMemory) {
        dynamicSystemPrompt += `\n\n## 相关记忆（来自过往对话）\n${longTermMemory}\n\n请利用这些记忆提供个性化的回复，但不要明确提及你在阅读记忆，除非相关。`;
    }

    // 附加对话摘要
    if (summary) {
        dynamicSystemPrompt += `\n\n## 之前的对话摘要\n${summary}`;
    }

    messages.push(new SystemMessage(dynamicSystemPrompt));

    return messages;
}

// ==================== 格式化输出 ====================

function formatMessageForDisplay(msg: BaseMessage, index: number): string {
    let roleDisplay = '';
    let nameDisplay = '';
    
    if (msg._getType() === 'human') {
        const humanMsg = msg as HumanMessage;
        roleDisplay = '👤 User';
        nameDisplay = (humanMsg as any).name || 'Unknown';
    } else if (msg._getType() === 'ai') {
        const aiMsg = msg as AIMessage;
        roleDisplay = '🤖 Assistant';
        nameDisplay = (aiMsg as any).name || 'Unknown';
    } else if (msg._getType() === 'system') {
        roleDisplay = '⚙️  System';
        nameDisplay = 'System';
    }

    const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);
    const contentPreview = content.length > 100 ? content.substring(0, 100) + '...' : content;
    
    return `\n[${ index + 1}] ${roleDisplay} (name: "${nameDisplay}")
Content: ${contentPreview}
Full Length: ${content.length} chars`;
}

function printAPIFormat(messages: BaseMessage[]): void {
    const apiMessages = messages.map(msg => {
        let role = '';
        if (msg._getType() === 'human') role = 'user';
        else if (msg._getType() === 'ai') role = 'assistant';
        else if (msg._getType() === 'system') role = 'system';

        const name = (msg as any).name;
        const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);

        const apiMsg: any = { role, content };
        if (name) apiMsg.name = name;
        
        return apiMsg;
    });

    console.log('\n\n════════════════════════════════════════════════════════════');
    console.log('📤 实际发送给 DeepSeek API 的格式 (JSON)');
    console.log('════════════════════════════════════════════════════════════\n');
    console.log(JSON.stringify({
        model: 'deepseek-chat',
        messages: apiMessages,
        stream: true,
        temperature: 0.7
    }, null, 2));
}

// ==================== 执行测试 ====================

console.log('\n');
console.log('╔════════════════════════════════════════════════════════════╗');
console.log('║        🧪 LLM 请求内容测试 (DeepSeek 缓存优化)             ║');
console.log('╚════════════════════════════════════════════════════════════╝');
console.log('\n');

console.log('📋 测试配置:');
console.log(`   - 用户名: ${userName}`);
console.log(`   - 角色名: ${charName}`);
console.log(`   - Context Window: ${contextWindow} 轮`);
console.log(`   - 历史对话条数: ${mockConversationHistory.length}`);
console.log(`   - 当前用户消息: "${mockUserMessage}"`);
console.log(`   - 是否有长期记忆: ${mockLongTermMemory ? '是' : '否'}`);
console.log(`   - 是否有对话摘要: ${mockSummary ? '是' : '否'}`);

console.log('\n');
console.log('════════════════════════════════════════════════════════════');
console.log('🔨 构建消息数组...');
console.log('════════════════════════════════════════════════════════════');

const messages = buildMessages(
    mockConversationHistory,
    mockUserMessage,
    contextWindow,
    mockSystemPrompt,
    mockSummary,
    mockLongTermMemory,
    userName,
    charName
);

console.log(`\n✅ 成功构建 ${messages.length} 条消息\n`);

console.log('════════════════════════════════════════════════════════════');
console.log('📨 消息结构详情');
console.log('════════════════════════════════════════════════════════════');

messages.forEach((msg, index) => {
    console.log(formatMessageForDisplay(msg, index));
});

console.log('\n\n════════════════════════════════════════════════════════════');
console.log('🔍 缓存分析');
console.log('════════════════════════════════════════════════════════════\n');

const historyCount = mockConversationHistory.length;
const historyTokenEstimate = mockConversationHistory.reduce((sum, msg) => 
    sum + Math.ceil(msg.content.length / 4), 0
);
const currentMsgTokenEstimate = Math.ceil(mockUserMessage.length / 4);
const systemPromptLength = messages[messages.length - 1].content.toString().length;
const systemTokenEstimate = Math.ceil(systemPromptLength / 4);

console.log(`1️⃣ 历史对话部分 (可缓存前缀):`);
console.log(`   - 消息数量: ${historyCount} 条`);
console.log(`   - 预估 Token: ~${historyTokenEstimate} tokens`);
console.log(`   - 缓存状态: ✅ 稳定，可被 DeepSeek 缓存\n`);

console.log(`2️⃣ 当前用户消息:`);
console.log(`   - 内容: "${mockUserMessage}"`);
console.log(`   - 预估 Token: ~${currentMsgTokenEstimate} tokens`);
console.log(`   - 缓存状态: ❌ 每次不同，无法缓存\n`);

console.log(`3️⃣ 动态 System Prompt:`);
console.log(`   - 长度: ${systemPromptLength} chars`);
console.log(`   - 预估 Token: ~${systemTokenEstimate} tokens`);
console.log(`   - 缓存状态: ⚠️  可能变化，但历史对话已缓存\n`);

const totalTokens = historyTokenEstimate + currentMsgTokenEstimate + systemTokenEstimate;
const cacheableTokens = historyTokenEstimate;
const cacheRatio = ((cacheableTokens / totalTokens) * 100).toFixed(1);

console.log(`📊 总计:`);
console.log(`   - 总 Token 预估: ~${totalTokens} tokens`);
console.log(`   - 可缓存 Token: ~${cacheableTokens} tokens (${cacheRatio}%)`);
console.log(`   - 💰 预估成本节省: 40-60% (第2轮对话开始)`);

// 打印 API 格式
printAPIFormat(messages);

console.log('\n\n════════════════════════════════════════════════════════════');
console.log('📝 完整 System Prompt 内容');
console.log('════════════════════════════════════════════════════════════\n');

const systemMessage = messages[messages.length - 1];
console.log(systemMessage.content);

console.log('\n\n════════════════════════════════════════════════════════════');
console.log('✅ 测试完成！');
console.log('════════════════════════════════════════════════════════════\n');

console.log('💡 提示:');
console.log('   - 历史对话使用真实用户名和角色名 (沉浸式体验)');
console.log('   - 消息顺序: 历史 → 当前 → System (缓存优化)');
console.log('   - System Prompt 合并了所有动态内容');
console.log('   - DeepSeek 会缓存历史对话部分，节省成本和提升速度\n');
