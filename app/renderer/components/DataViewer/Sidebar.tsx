import React from 'react';
import { ScrollText, Brain, Network, Braces } from 'lucide-react';
import { TableInfo } from './types';

interface SidebarProps {
    activeTab: 'tables' | 'query' | 'stats' | 'graph';
    selectedTable: string | null;
    onTabChange: (tab: 'tables' | 'query' | 'stats' | 'graph') => void;
    onTableSelect: (tableName: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
    activeTab,
    selectedTable,
    onTabChange,
    onTableSelect
}) => {
    return (
        <div style={{ 
            width: '240px', 
            backgroundColor: 'rgba(20, 10, 30, 0.3)', 
            borderRight: '1px solid rgba(255, 105, 180, 0.1)', 
            display: 'flex', flexDirection: 'column',
            backdropFilter: 'blur(10px)'
        }}>
            <div style={{ padding: '20px 20px 10px', fontSize: '11px', fontWeight: '800', color: '#f472b6', textTransform: 'uppercase', letterSpacing:'1px' }}>Core Memories</div>
            
            {/* Conversation View */}
            <div 
                onClick={() => { onTabChange('tables'); onTableSelect('conversation_log'); }}
                style={{ 
                    padding: '12px 20px', cursor: 'pointer', display:'flex', alignItems:'center', gap:'12px',
                    background: (activeTab === 'tables' && selectedTable === 'conversation_log') ? 'linear-gradient(90deg, rgba(236, 72, 153, 0.15), transparent)' : 'transparent',
                    color: (activeTab === 'tables' && selectedTable === 'conversation_log') ? '#fff' : 'rgba(255,255,255,0.6)',
                    borderLeft: (activeTab === 'tables' && selectedTable === 'conversation_log') ? '3px solid #ec4899' : '3px solid transparent',
                    transition: 'all 0.2s'
                }}
            >
                <ScrollText size={18} /> 
                <span style={{fontSize:'14px', fontWeight: (activeTab === 'tables' && selectedTable === 'conversation_log') ? '600' : '400'}}>Conversation Logs</span>
            </div>

            {/* Episodic Memory View */}
            <div 
                onClick={() => { onTabChange('tables'); onTableSelect('episodic_memory'); }}
                style={{ 
                    padding: '12px 20px', cursor: 'pointer', display:'flex', alignItems:'center', gap:'12px',
                    background: (activeTab === 'tables' && selectedTable === 'episodic_memory') ? 'linear-gradient(90deg, rgba(236, 72, 153, 0.15), transparent)' : 'transparent',
                    color: (activeTab === 'tables' && selectedTable === 'episodic_memory') ? '#fff' : 'rgba(255,255,255,0.6)',
                    borderLeft: (activeTab === 'tables' && selectedTable === 'episodic_memory') ? '3px solid #ec4899' : '3px solid transparent',
                    transition: 'all 0.2s'
                }}
            >
                <Brain size={18} /> 
                <span style={{fontSize:'14px', fontWeight: (activeTab === 'tables' && selectedTable === 'episodic_memory') ? '600' : '400'}}>Episodic Memory</span>
            </div>

            <div style={{ padding: '20px 20px 10px', fontSize: '11px', fontWeight: '800', color: '#a78bfa', textTransform: 'uppercase', letterSpacing:'1px', marginTop:'10px' }}>Knowledge Graph</div>

            {/* Visual Graph View */}
            <div 
                onClick={() => { onTabChange('graph'); }}
                style={{ 
                    padding: '12px 20px', cursor: 'pointer', display:'flex', alignItems:'center', gap:'12px',
                    background: activeTab === 'graph' ? 'linear-gradient(90deg, rgba(139, 92, 246, 0.15), transparent)' : 'transparent',
                    color: activeTab === 'graph' ? '#fff' : 'rgba(255,255,255,0.6)',
                    borderLeft: activeTab === 'graph' ? '3px solid #8b5cf6' : '3px solid transparent',
                    transition: 'all 0.2s'
                }}
            >
                <Network size={18} /> 
                <span style={{fontSize:'14px', fontWeight: activeTab === 'graph' ? '600' : '400'}}>Visual Graph</span>
            </div>

            {/* Text Facts View */}
            <div 
                onClick={() => { onTabChange('tables'); onTableSelect('knowledge_facts'); }}
                style={{ 
                    padding: '12px 20px', cursor: 'pointer', display:'flex', alignItems:'center', gap:'12px',
                    background: (activeTab === 'tables' && selectedTable === 'knowledge_facts') ? 'linear-gradient(90deg, rgba(59, 130, 246, 0.15), transparent)' : 'transparent',
                    color: (activeTab === 'tables' && selectedTable === 'knowledge_facts') ? '#fff' : 'rgba(255,255,255,0.6)',
                    borderLeft: (activeTab === 'tables' && selectedTable === 'knowledge_facts') ? '3px solid #3b82f6' : '3px solid transparent',
                    transition: 'all 0.2s'
                }}
            >
                 <Braces size={18} /> 
                 <span style={{fontSize:'14px', fontWeight: (activeTab === 'tables' && selectedTable === 'knowledge_facts') ? '600' : '400'}}>Knowledge Data</span>
            </div>
        </div>
    );
};
