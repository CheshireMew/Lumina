
import React from 'react';
import { HistoryEvent, Fact } from './types';

// --- Helpers ---
const parseContent = (jsonStr: string) => {
    try {
        const obj = JSON.parse(jsonStr);
        return obj.content || jsonStr;
    } catch {
        return jsonStr;
    }
};

const getRole = (jsonStr: string) => {
    try {
        const obj = JSON.parse(jsonStr);
        return obj.role || 'unknown';
    } catch {
        return 'system';
    }
};

const getName = (jsonStr: string) => {
    try {
        const obj = JSON.parse(jsonStr);
        return obj.name || '';
    } catch {
        return '';
    }
};

const getImportanceColor = (score: number) => {
    if (score >= 8) return '#ff3366'; // Critical (Red)
    if (score >= 5) return '#ffcc00'; // Medium (Yellow)
    return '#444'; // Trivia (Grey)
};

// --- Components ---

interface HistoryListProps {
    history?: HistoryEvent[];
    activeCharacterId: string;
}

export const HistoryList: React.FC<HistoryListProps> = ({ history, activeCharacterId }) => {
    if (!history || history.length === 0) {
        return <div style={{color: '#666', textAlign: 'center'}}>No recent history found.</div>;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {history
                .filter(event => {
                    const text = parseContent(event.content);
                    return !text.includes('(Private System Instruction');
                })
                .map((event, i) => {
                const role = event.role || getRole(event.content);
                const text = parseContent(event.content);
                const parseName = event.name || getName(event.content);
                
                const normalizedRole = role?.toLowerCase() || '';
                const normalizedCharId = activeCharacterId.toLowerCase();
                
                const isAI = normalizedRole === normalizedCharId || 
                             normalizedRole === 'assistant' || 
                             normalizedRole === 'ai' || 
                             normalizedRole === 'system' ||
                             normalizedRole === 'lillian' || 
                             normalizedRole === 'hiyori';
                             
                const isUser = !isAI;
                const displayName = parseName || (role === 'user' ? 'USER' : (role === 'system' ? 'SYSTEM' : role)) || 'AI';
                
                return (
                    <div key={i} style={{ 
                        padding: '10px 15px', 
                        background: isUser ? '#2a2a3a' : '#1a1a2a', 
                        border: isUser ? '1px solid #444' : '1px solid #336699',
                        borderRadius: '8px',
                        alignSelf: isUser ? 'flex-end' : 'flex-start',
                        maxWidth: '80%'
                    }}>
                        <div style={{ fontSize: '0.8em', color: isUser ? '#aaa' : '#4facfe', marginBottom: '4px' }}>
                            {displayName} • {new Date(event.timestamp).toLocaleString()}
                        </div>
                        <div style={{ fontSize: '1em', color: '#eee', whiteSpace: 'pre-wrap' }}>
                            {text}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

interface FactListProps {
    facts?: Fact[];
}

export const FactList: React.FC<FactListProps> = ({ facts }) => {
    if (!facts || facts.length === 0) {
        return <div style={{color: '#666', textAlign: 'center'}}>No crystallized facts found yet. Try chatting more!</div>;
    }

    return (
        <div style={{ display: 'grid', gap: '8px' }}>
            {facts.map((fact, i) => {
                const isUserMemory = fact.channel === 'user';
                const channelLabel = isUserMemory ? 'User' : 'Character';
                const channelColor = isUserMemory ? '#60a5fa' : '#f472b6';
                const displayContent = fact.content.replace(/^\([a-fA-F0-9-]+\)\s*\[[^\]]+\]\s*/, '').trim();
                
                return (
                    <div key={i} style={{ 
                        padding: '10px 12px', 
                        background: '#1a1a1a', 
                        borderLeft: `3px solid ${getImportanceColor(fact.importance)}`,
                        borderRadius: '4px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        gap: '12px'
                    }}>
                        <div style={{ flex: 1 }}>
                            <div style={{ 
                                display: 'inline-block',
                                fontSize: '0.7em', 
                                color: channelColor,
                                backgroundColor: `${channelColor}22`,
                                padding: '2px 8px',
                                borderRadius: '4px',
                                marginBottom: '6px',
                                fontWeight: 'bold'
                            }}>
                                {channelLabel} {fact.source_name ? `• ${fact.source_name}` : ''}
                            </div>
                            <div style={{ fontSize: '0.9em', marginBottom: '4px', lineHeight: '1.4' }}>
                                {displayContent}
                            </div>
                            <div style={{ fontSize: '0.7em', color: '#666' }}>
                                {new Date(fact.created_at).toLocaleString()} • {fact.emotion}
                            </div>
                        </div>
                        <div style={{ 
                            fontSize: '1.2em', 
                            opacity: 0.3, 
                            fontWeight: 'bold',
                            minWidth: '24px',
                            textAlign: 'right'
                        }}>
                            {fact.importance}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
