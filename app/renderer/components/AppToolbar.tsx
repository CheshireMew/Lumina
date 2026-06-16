import React from 'react';
import { Settings as SettingsIcon, Activity, Brain, BookOpen } from 'lucide-react';

interface AppToolbarProps {
    onOpenSettings: () => void;
    onOpenMotionTester: () => void;
    onOpenLLMSettings: () => void;
    onOpenMemoryInspector: () => void;
}

export const AppToolbar: React.FC<AppToolbarProps> = ({
    onOpenSettings,
    onOpenMotionTester,
    onOpenLLMSettings,
    onOpenMemoryInspector
}) => {
    return (
        <div style={{ position: 'absolute', top: 30, right: 30, display: 'flex', flexDirection: 'column', gap: 15, zIndex: 100 }}>
            {/* Voice Toggle moved to InputBox */}
            <ToolbarButton onClick={onOpenLLMSettings} color="rgba(76, 175, 80, 0.2)" icon={<Brain size={24} />} title="LLM Configuration" />
            <ToolbarButton onClick={onOpenMemoryInspector} color="rgba(0, 255, 157, 0.2)" icon={<BookOpen size={24} />} title="Memory" />
            <ToolbarButton onClick={onOpenSettings} color="rgba(33,150,243,0.2)" icon={<SettingsIcon size={24} />} title="Settings" />
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
