
import React, { useEffect, useState } from 'react';
import { MemoryData, ProcessingStatus } from './types';
import MemoryStatus from './MemoryStatus';
import { HistoryList, FactList } from './MemoryList';
import MemoryGraph from './MemoryGraph';

const MemoryInspector: React.FC<{ onClose: () => void, activeCharacterId: string }> = ({ onClose, activeCharacterId }) => {
    const [activeTab, setActiveTab] = useState<'history' | 'facts' | 'status' | 'graph'>('history');
    const [data, setData] = useState<MemoryData | null>(null);
    const [status, setStatus] = useState<ProcessingStatus | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchData();
        fetchStatus();
        
        const interval = setInterval(() => {
            fetchStatus();
        }, 5000);
        
        return () => clearInterval(interval);
    }, [activeCharacterId]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await fetch(`http://127.0.0.1:8010/debug/brain_dump?character_id=${activeCharacterId}`);
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
            const res = await fetch(`http://127.0.0.1:8010/debug/processing_status?character_id=${activeCharacterId}`);
            const json = await res.json();
            if (json.status === 'success') {
                setStatus(json);
            }
        } catch (err) {
            console.error('Failed to fetch processing status:', err);
        }
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
                        onClick={() => setActiveTab('graph')}
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
                        🕸️ Knowledge Graph ({data?.graph?.edges?.length || 0})
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
                    
                    {!loading && activeTab === 'status' && (
                        <MemoryStatus status={status} />
                    )}
                    
                    {!loading && data && activeTab === 'history' && (
                        <HistoryList history={data.history} activeCharacterId={activeCharacterId} />
                    )}

                    {!loading && data && activeTab === 'facts' && (
                        <FactList facts={data.facts} />
                    )}

                    {!loading && data && activeTab === 'graph' && (
                        <MemoryGraph edges={data.graph.edges} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default MemoryInspector;
