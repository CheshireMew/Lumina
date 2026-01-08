/**
 * SettingsModal 组件索引
 * 
 * 使用方式：
 * import SettingsModal from '@renderer/components/SettingsModal';
 */

// 主组件 - 使用重构版
export { default } from './SettingsModalRefactored';
export { default as SettingsModalRefactored } from './SettingsModalRefactored';

// 旧版本（作为备份）
export { default as SettingsModalLegacy } from '../SettingsModal';

// 子组件导出
export * from './tabs';
export * from './types';
export * from './styles';
