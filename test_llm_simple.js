/**
 * 简化版 LLM 请求测试脚本
 * 专注于打印核心消息结构
 */

// 模拟数据
const mockHistory = [
    { role: 'user', content: '你好，Hiyori' },
    { role: 'assistant', content: '你好呀，Master！今天想聊什么呢？[微笑]' },
    { role: 'user', content: '我想了解一下你最近在做什么' },
    { role: 'assistant', content: '最近在学习新的舞蹈呢！虽然有点累，但很开心~[害羞]' },
    { role: 'user', content: '听起来不错！需要帮忙吗？' },
    { role: 'assistant', content: '谢谢你！有你的鼓励我就很满足啦~[爱心]' }
];

const mockUserMessage = '今天天气怎么样？';

const mockSystemPrompt = `# 角色设定
你是 Hiyori，一个活泼开朗的虚拟角色。

## 性格特点
- 亲切友好，喜欢用可爱的语气说话
- 对 Master 有特殊的好感
- 喜欢跳舞和唱歌`;

const mockMemory = `- Master 上周提到他喜欢晴天
- Master之前说过他工作很忙
- Master对音乐有特别的兴趣`;

const mockSummary = 'Master和Hiyori讨论了最近的生活，Hiyori分享了她正在学习舞蹈的事情，Master表示了鼓励和支持。';

const userName = 'Master';
const charName = 'Hiyori';

// 构建消息（与 llm_service.ts 逻辑一致）
function buildAPIMessages() {
    const messages = [];

    // 1. 历史对话
    for (const msg of mockHistory) {
        messages.push({
            role: msg.role === 'user' ? 'user' : 'assistant',
            content: msg.content,
            name: msg.role === 'user' ? userName : charName
        });
    }

    // 2. 当前用户消息
    messages.push({
        role: 'user',
        content: mockUserMessage,
        name: userName
    });

    // 3. System Prompt（合并记忆和摘要）
    let systemContent = mockSystemPrompt;
    if (mockMemory) {
        systemContent += `\n\n## 相关记忆（来自过往对话）\n${mockMemory}\n\n请利用这些记忆提供个性化的回复，但不要明确提及你在阅读记忆，除非相关。`;
    }
    if (mockSummary) {
        systemContent += `\n\n## 之前的对话摘要\n${mockSummary}`;
    }

    messages.push({
        role: 'system',
        content: systemContent
    });

    return messages;
}

// 执行测试
console.log('\n='.repeat(60));
console.log('LLM Request Test - DeepSeek Cache Optimization');
console.log('='.repeat(60));

const messages = buildAPIMessages();

console.log(`\nTotal Messages: ${messages.length}`);
console.log(`User Name: ${userName}`);
console.log(`Character Name: ${charName}\n`);

console.log('='.repeat(60));
console.log('Message Structure:');
console.log('='.repeat(60));

messages.forEach((msg, index) => {
    console.log(`\n[${index + 1}] ${msg.role.toUpperCase()}${msg.name ? ` (name: "${msg.name}")` : ''}`);
    const preview = msg.content.substring(0, 80);
    console.log(`Content: ${preview}${msg.content.length > 80 ? '...' : ''}`);
    console.log(`Length: ${msg.content.length} chars`);
});

console.log('\n' + '='.repeat(60));
console.log('API Request Format (JSON):');
console.log('='.repeat(60) + '\n');

const apiRequest = {
    model: 'deepseek-chat',
    messages: messages,
    stream: true,
    temperature: 0.7
};

console.log(JSON.stringify(apiRequest, null, 2));

console.log('\n' + '='.repeat(60));
console.log('Cache Analysis:');
console.log('='.repeat(60));

const historyTokens = mockHistory.reduce((sum, m) => sum + Math.ceil(m.content.length / 4), 0);
const currentTokens = Math.ceil(mockUserMessage.length / 4);
const systemTokens = Math.ceil(messages[messages.length - 1].content.length / 4);
const total = historyTokens + currentTokens + systemTokens;

console.log(`\n1. History Messages (Cacheable): ~${historyTokens} tokens`);
console.log(`2. Current User Message: ~${currentTokens} tokens`);
console.log(`3. System Prompt: ~${systemTokens} tokens`);
console.log(`\nTotal: ~${total} tokens`);
console.log(`Cacheable Ratio: ${((historyTokens / total) * 100).toFixed(1)}%`);
console.log(`Estimated Cost Savings: 40-60% (from 2nd turn onwards)\n`);

console.log('='.repeat(60));
console.log('Full System Prompt:');
console.log('='.repeat(60) + '\n');
console.log(messages[messages.length - 1].content);

console.log('\n' + '='.repeat(60));
console.log('Test Complete!');
console.log('='.repeat(60) + '\n');
