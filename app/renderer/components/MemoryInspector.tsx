import React, { useEffect, useState } from 'react';
import { Database, Gem, Users, Settings, Info } from 'lucide-react';

interface HistoryEvent {
    id: string;
    event_type?: string; 
    content: string;
    timestamp: string;
    role?: string; // Backend-provided role (e.g. '柴郡', 'Lillian')
    name?: string; // Backend-provided name
}

interface Fact {
    id: string;
    content: string;
    importance: number;
    emotion: string;
    created_at: string;
    channel?: string;        // 'user' 或 'character'
    source_name?: string;    // 来源名称（如 '柴郡', 'hiyori'）
}

interface GraphEdge {
    source: string;
    target: string;
    label: string;
}

interface MemoryData {
    facts: Fact[];
    graph: {
        nodes: any[];
        edges: GraphEdge[];
    };
    user_facts?: Fact[]; // Add user_facts
    history?: HistoryEvent[];
}

interface ProcessingStatus {
    status: string;
    conversations: {
        unprocessed: number;
        total: number;
        threshold: number;
        progress_percent: number;
    };
    facts: {
        user: {
            unconsolidated: number;
            total: number;
            threshold: number;
            progress_percent: number;
        };
        character: {
            unconsolidated: number;
            total: number;
            threshold: number;
            progress_percent: number;
        };
    };
}

const MemoryInspector: React.FC<{ onClose: () => void, activeCharacterId: string }> = ({ onClose, activeCharacterId }) => {
    const [activeTab, setActiveTab] = useState<'history' | 'facts' | 'status' | 'graph'>('history');
    const [data, setData] = useState<MemoryData | null>(null);
    const [status, setStatus] = useState<ProcessingStatus | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchData();
        fetchStatus();
        
        // Auto-refresh status every 5 seconds (优化：降低轮询频率)
        const interval = setInterval(() => {
            fetchStatus();
        }, 5000);  // 从 2000ms 改为 5000ms
        
        return () => clearInterval(interval);
    }, [activeCharacterId]); // 依赖 activeCharacterId 变化自动刷新

    const fetchData = async () => {
        setLoading(true);
        try {
            // Use activeCharacterId from props
            const res = await fetch(`http://127.0.0.1:8001/debug/brain_dump?character_id=${activeCharacterId}`);
            const json = await res.json();
            if (json.status === 'success') {
                setData(json);
            }
        } catch (err) {
            console.error('Failed to fetch memory data:', err);
        } finally {
            setLoading(false);
        }
    };
    
    const fetchStatus = async () => {
        try {
            const res = await fetch(`http://127.0.0.1:8001/debug/processing_status?character_id=${activeCharacterId}`);
            const json = await res.json();
            if (json.status === 'success') {
                setStatus(json);
            }
        } catch (err) {
            console.error('Failed to fetch processing status:', err);
        }
    };

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

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 9999
        }}>
            <div style={{
                backgroundColor: '#1a1a2e',
                padding: '2rem',
                borderRadius: '12px',
                width: '900px',
                height: '600px',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                color: '#eee'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0, fontSize: '1.5rem' }}>🧠 Memory Inspector</h2>
                    <button onClick={onClose} style={{
                        background: 'none',
                        border: 'none',
                        color: '#eee',
                        fontSize: '1.5rem',
                        cursor: 'pointer'
                    }}>✕</button>
                </div>

                {/* Tabs */}
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', borderBottom: '2px solid #333' }}>
                    <button 
                        onClick={() => setActiveTab('history')}
                        style={{
                            padding: '15px 30px',
                            background: activeTab === 'history' ? '#00ff9d22' : 'transparent',
                            color: activeTab === 'history' ? '#00ff9d' : '#888',
                            border: 'none',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            borderBottom: activeTab === 'history' ? '2px solid #00ff9d' : 'none'
                        }}
                    >
                        📜 Recent History ({data?.history?.length || 0})
                    </button>
                <button 
                    onClick={() => setActiveTab('facts')}
                    style={{
                        padding: '15px 30px',
                        background: activeTab === 'facts' ? '#00ff9d22' : 'transparent',
                        color: activeTab === 'facts' ? '#00ff9d' : '#888',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        borderBottom: activeTab === 'facts' ? '2px solid #00ff9d' : 'none'
                    }}
                >
                    💎 Core Facts ({data?.facts?.length || 0})
                </button>
                <button 
                    onClick={() => setActiveTab('graph')} // Reuse 'graph' state key to mean 'user facts' for simplicity, or rename. Let's start with renaming label.
                    style={{
                        padding: '15px 30px',
                        background: activeTab === 'graph' ? '#00ff9d22' : 'transparent',
                        color: activeTab === 'graph' ? '#00ff9d' : '#888',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        borderBottom: activeTab === 'graph' ? '2px solid #00ff9d' : 'none'
                    }}
                >
                    👤 User Facts ({data?.user_facts?.length || 0})
                </button>
                <button
                    onClick={() => setActiveTab('status')}
                    style={{
                        padding: '15px 30px',
                        background: activeTab === 'status' ? '#00ff9d22' : 'transparent',
                        color: activeTab === 'status' ? '#00ff9d' : '#888',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        borderBottom: activeTab === 'status' ? '2px solid #00ff9d' : 'none'
                    }}
                >
                    ⚙️ Processing Status
                </button>
                <div style={{flex: 1}} />
                <button onClick={fetchData} style={{ padding: '0 20px', background: 'transparent', border: 'none', color: '#00ff9d', cursor: 'pointer' }}>↻ Refresh</button>
            </div>

            {/* Content */}
            <div style={{ height: '430px', overflow: 'auto', padding: '20px' }}>
                {loading && <div style={{textAlign: 'center', padding: 50, color: '#666'}}>Scanning Neural Pathways...</div>}
                
                {!loading && activeTab === 'status' && status && (
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
                                • Status auto-refreshes every 2 seconds
                            </div>
                        </div>
                    </div>
                )}
                
                
                {!loading && data && activeTab === 'history' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {data.history?.map((event, i) => {
                            // Backend now sends { role, name, content, timestamp }
                            // Prioritize backend fields, fallback to old JSON parse logic
                            const role = event.role || getRole(event.content);
                            const text = parseContent(event.content);
                            const parseName = event.name || getName(event.content);
                            
                            // Robust heuristic: Compare role with activeCharacterId
                            // If role matches active char (case-insensitive) or is standard AI roles, treat as AI.
                            const normalizedRole = role?.toLowerCase() || '';
                            const normalizedCharId = activeCharacterId.toLowerCase();
                            
                            const isAI = normalizedRole === normalizedCharId || 
                                         normalizedRole === 'assistant' || 
                                         normalizedRole === 'ai' || 
                                         normalizedRole === 'system' ||
                                         normalizedRole === 'lillian' || // Keep legacy hardcodes just in case
                                         normalizedRole === 'hiyori';
                                         
                            const isUser = !isAI;
                            
                            // Display Name Logic
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
                        {(!data.history || data.history.length === 0) && <div style={{color: '#666', textAlign: 'center'}}>No recent history found.</div>}
                    </div>
                )}

                {!loading && data && activeTab === 'facts' && (
                    <div style={{ display: 'grid', gap: '8px' }}>
                        {data.facts.map((fact, i) => {
                            // 判断记忆来源
                            const isUserMemory = fact.channel === 'user';
                            const channelLabel = isUserMemory ? 'User' : 'Character';
                            const channelColor = isUserMemory ? '#60a5fa' : '#f472b6';
                            
                            // Clean up content (remove metadata prefixes like (uuid) [timestamp])
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
                                        {/* 记忆来源标签 */}
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
                                        {/* 事实内容 */}
                                        <div style={{ fontSize: '0.9em', marginBottom: '4px', lineHeight: '1.4' }}>
                                            {displayContent}
                                        </div>
                                        {/* 时间和情绪 */}
                                        <div style={{ fontSize: '0.7em', color: '#666' }}>
                                            {new Date(fact.created_at).toLocaleString()} • {fact.emotion}
                                        </div>
                                    </div>
                                    {/* 重要性分数 */}
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
                        {data.facts.length === 0 && <div style={{color: '#666', textAlign: 'center'}}>No crystallized facts found yet. Try chatting more!</div>}
                    </div>
                )}

                {!loading && data && activeTab === 'graph' && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '15px' }}>
                        {data.graph.edges.map((edge, i) => (
                            <div key={i} style={{ 
                                padding: '15px', 
                                background: '#111', 
                                border: '1px solid #333',
                                borderRadius: '8px',
                                textAlign: 'center'
                            }}>
                                <div style={{ color: '#aaa', fontSize: '0.9em' }}>{edge.source}</div>
                                <div style={{ color: '#00ff9d', fontWeight: 'bold', margin: '5px 0', fontSize: '0.8em' }}>── {edge.label} ──▶</div>
                                <div style={{ color: '#fff', fontSize: '1.1em' }}>{edge.target}</div>
                            </div>
                        ))}
                         {data.graph.edges.length === 0 && <div style={{color: '#666', textAlign: 'center'}}>No synaptic connections (graph) found yet. Start dreaming to weave the web!</div>}
                    </div>
                )}
            </div>
        </div>
    </div>
    );
};

export default MemoryInspector;
