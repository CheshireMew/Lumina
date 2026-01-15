import React from 'react';
import { Mic, Keyboard, Settings as SettingsIcon, Activity, Puzzle, User, Brain } from 'lucide-react';
import VTuberModeToggle from './VTuberModeToggle';

interface AppToolbarProps {
    chatMode: 'text' | 'voice';
    onToggleChatMode: () => void;
    onOpenAvatarSelector: () => void;
    onOpenSettings: () => void;
    onOpenPlugins: () => void;
    onOpenMotionTester: () => void;
    onOpenLLMSettings: () => void;
}

export const AppToolbar: React.FC<AppToolbarProps> = ({
    chatMode,
    onToggleChatMode,
    onOpenAvatarSelector,
    onOpenSettings,
    onOpenPlugins,
    onOpenMotionTester,
    onOpenLLMSettings
}) => {
    return (
        <div style={{ position: 'absolute', top: 30, right: 30, display: 'flex', flexDirection: 'column', gap: 15, zIndex: 100 }}>
            <VTuberModeToggle />
            <ToolbarButton 
                onClick={onToggleChatMode}
                color={chatMode === 'voice' ? 'rgba(255,107,107,0.2)' : 'rgba(76,175,80,0.2)'}
                icon={chatMode === 'text' ? <Mic size={24} /> : <Keyboard size={24} />}
                title={chatMode === 'text' ? 'Voice Mode' : 'Text Mode'}
            />
            <ToolbarButton onClick={onOpenAvatarSelector} color="rgba(255, 193, 7, 0.2)" icon={<User size={24} />} title="Switch Avatar" />
            <ToolbarButton onClick={onOpenLLMSettings} color="rgba(76, 175, 80, 0.2)" icon={<Brain size={24} />} title="LLM Configuration" />
            <ToolbarButton onClick={onOpenSettings} color="rgba(33,150,243,0.2)" icon={<SettingsIcon size={24} />} title="Settings" />
            <ToolbarButton onClick={onOpenPlugins} color="rgba(156,39,176,0.2)" icon={<Puzzle size={24} />} title="Plugins" />
            <ToolbarButton onClick={onOpenMotionTester} color="rgba(156,39,176,0.2)" icon={<Activity size={24} />} title="Motions" />
        </div>
    );
};

const ToolbarButton: React.FC<{
    onClick: () => void;
    color: string;
    icon: React.ReactNode;
    title: string;
}> = ({ onClick, color, icon, title }) => (
    <button
        onClick={onClick}
        title={title}
        style={{
            width: 48, height: 48, borderRadius: '50%',
            backgroundColor: color, color: 'white',
            border: '1px solid rgba(255,255,255,0.3)',
            backdropFilter: 'blur(10px)',
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease'
        }}
        onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
    >
        {icon}
    </button>
);
