
import React from 'react';
import { Database, Gem, Users, Info } from 'lucide-react';
import { ProcessingStatus } from './types';

interface MemoryStatusProps {
    status: ProcessingStatus | null;
}

const MemoryStatus: React.FC<MemoryStatusProps> = ({ status }) => {
    if (!status) return null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <Database size={20} color="#a78bfa" />
                    <h3 style={{ margin: 0, color: '#a78bfa' }}>Conversation Buffer</h3>
                </div>
                <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: '#aaa' }}>
                    Pending: {status.conversations.unprocessed}/{status.conversations.threshold}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{
                        flex: 1,
                        height: '30px',
                        background: '#2a2a3a',
                        borderRadius: '8px',
                        overflow: 'hidden',
                        border: '1px solid #444',
                        position: 'relative'
                    }}>
                        <div style={{
                            width: `${status.conversations.progress_percent}%`,
                            height: '100%',
                            background: status.conversations.progress_percent >= 100 ? '#ef4444' : 
                                       status.conversations.progress_percent >= 70 ? '#f59e0b' : '#10b981',
                            transition: 'width 0.3s ease, background 0.3s ease'
                        }} />
                    </div>
                </div>
                <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#888' }}>
                    {status.conversations.unprocessed >= status.conversations.threshold ? 
                        'Batch extraction will trigger!' : 
                        `Need ${status.conversations.threshold - status.conversations.unprocessed} more conversations`}
                </div>
            </div>

            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <Gem size={20} color="#60a5fa" />
                    <h3 style={{ margin: 0, color: '#60a5fa' }}>User Facts Consolidation</h3>
                </div>
                <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: '#aaa' }}>
                    Unconsolidated: {status.facts.user.unconsolidated}/{status.facts.user.threshold} | Total: {status.facts.user.total}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{
                        flex: 1,
                        height: '30px',
                        background: '#2a2a3a',
                        borderRadius: '8px',
                        overflow: 'hidden',
                        border: '1px solid #444'
                    }}>
                        <div style={{
                            width: `${status.facts.user.progress_percent}%`,
                            height: '100%',
                            background: status.facts.user.progress_percent >= 100 ? '#ef4444' : 
                                       status.facts.user.progress_percent >= 70 ? '#f59e0b' : '#10b981',
                            transition: 'width 0.3s ease, background 0.3s ease'
                        }} />
                    </div>
                </div>
                <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#888' }}>
                    {status.facts.user.unconsolidated >= status.facts.user.threshold ? 
                        'Consolidation will trigger!' : 
                        `Need ${status.facts.user.threshold - status.facts.user.unconsolidated} more facts`}
                </div>
            </div>

            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <Users size={20} color="#f472b6" />
                    <h3 style={{ margin: 0, color: '#f472b6' }}>Character Facts Consolidation</h3>
                </div>
                <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: '#aaa' }}>
                    Unconsolidated: {status.facts.character.unconsolidated}/{status.facts.character.threshold} | Total: {status.facts.character.total}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{
                        flex: 1,
                        height: '30px',
                        background: '#2a2a3a',
                        borderRadius: '8px',
                        overflow: 'hidden',
                        border: '1px solid #444'
                    }}>
                        <div style={{
                            width: `${status.facts.character.progress_percent}%`,
                            height: '100%',
                            background: status.facts.character.progress_percent >= 100 ? '#ef4444' : 
                                       status.facts.character.progress_percent >= 70 ? '#f59e0b' : '#10b981',
                            transition: 'width 0.3s ease, background 0.3s ease'
                        }} />
                    </div>
                </div>
                <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#888' }}>
                    {status.facts.character.unconsolidated >= status.facts.character.threshold ? 
                        'Consolidation will trigger!' : 
                        `Need ${status.facts.character.threshold - status.facts.character.unconsolidated} more facts`}
                </div>
            </div>

            <div style={{ 
                marginTop: '1rem', 
                padding: '1rem', 
                background: '#2a2a3a', 
                borderRadius: '8px',
                border: '1px solid #444'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Info size={16} color="#aaa" />
                    <strong style={{ color: '#aaa' }}>How it works:</strong>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#888', lineHeight: '1.6' }}>
                    • Conversations accumulate until 20 → Batch extraction → Facts saved<br/>
                    • Facts accumulate until 10/channel → LLM deduplication → Clean database<br/>
                    • Status auto-refreshes every 5 seconds
                </div>
            </div>
        </div>
    );
};

export default MemoryStatus;
