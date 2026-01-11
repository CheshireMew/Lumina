# Proposal: Frontend UI Optimization (optimize-frontend-ui)

## 为什么

需要提升前端界面的美观度、交互流畅性和功能完整性，以匹配后端能力的增强（如 Soul Evolution）。此变更旨在解决现有 UI 的痛点并引入更精致的视觉体验。

## 变更内容

本提案旨在对现有 React 前端进行系统性优化。具体范围包括：

1. **聊天界面 (Chat Interface)**:

   - 优化消息气泡样式。
   - 增强动态背景或 Live2D 容器的视觉融合。
   - 改进输入框（Voice/Text）的交互状态（如麦克风动画）。

2. **状态可视化 (State Visualization)**:

   - 重构 `GalGameHud.tsx`，使其更具沉浸感。
   - 实时显示 PAD/Mood/Energy 变化动画。

3. **设置与配置 (Settings)**:

   - 优化 `SettingsModal` 的布局和易用性。
   - 添加“便携模式”路径显示（只读）。

4. **记忆可视化 (Memory Viewer)**:
   - (可选) 重构 SurrealDB Graph Viewer，提供更清晰的节点关系图。

## 影响范围

- `app/renderer/`: 所有前端组件。
- `app/main/`: IPC 通信（若涉及窗口控制）。

## 验证

- **Visual Regression**: 人工检查 UI 在不同尺寸下的表现。
- **Interaction Test**: 验证对话流、设置保存、Live2D 交互的响应速度。
