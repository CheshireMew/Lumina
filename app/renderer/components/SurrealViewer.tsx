/**
 * SurrealViewer - SurrealDB 数据可视化组件
 * 包含：表浏览、数据查看、查询控制台、统计信息
 * 风格：GalGame / 赛博粉紫 (Pink/Purple Cyber-Magic)
 */
import React, { useState, useEffect, useRef } from 'react';
import { 
    X, Database, ScrollText, Network, Braces, RefreshCw, Brain,
    CheckCircle, Clock, Search, Table as TableIcon, Activity, Sparkles, Trash2, Edit, Plus, GitMerge, Filter, ChevronRight, ChevronDown, Eye, Maximize2
} from 'lucide-react';
import { API_CONFIG } from '../config';

interface TableInfo {
    name: string;
    info: string;
}

interface QueryResult {
    status: string;
    result?: any[];
    error?: string;
}

const SurrealViewer: React.FC<{ isOpen: boolean; onClose: () => void; activeCharacterId?: string | null }> = ({ isOpen, onClose, activeCharacterId }) => {
    const [activeTab, setActiveTab] = useState<'tables' | 'query' | 'stats' | 'graph'>('tables');
    const [tables, setTables] = useState<TableInfo[]>([]);
    const [selectedTable, setSelectedTable] = useState<string | null>('conversation_log'); // Default to conversation_log
    const [tableData, setTableData] = useState<any[]>([]);
    const [query, setQuery] = useState('SELECT * FROM fact LIMIT 10;');
    const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [graphData, setGraphData] = useState<{nodes: any[], edges: any[]} | null>(null);
    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [detailEdge, setDetailEdge] = useState<any>(null); // For Knowledge Data detail modal
    
    // 缓存已加载的表数据，避免重复请求
    const [tableCache, setTableCache] = useState<Record<string, any[]>>({});

    useEffect(() => {
        if (isOpen) {
            loadTables();
            loadStats();
            // Load default table if selected
            if (selectedTable) {
                loadTableData(selectedTable);
            }
        }
    }, [isOpen]);

    // Auto-load graph data when switching to 'graph' tab
    useEffect(() => {
        if (activeTab === 'graph' && !graphData) {
            loadGraph();
        }
    }, [activeTab]);

    // Reload when character changes
    useEffect(() => {
        if (activeCharacterId) {
            console.log(`[SurrealViewer] Character switched to ${activeCharacterId}, clearing cache...`);
            setTableCache({}); // Clear cache ALWAYS
            
            // Only reload immediately if open
            if (isOpen && selectedTable) {
                loadTableData(selectedTable, true); // Force refresh
            }
        }
    }, [activeCharacterId]);

    const loadTables = async () => {
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/debug/surreal/tables`);
            if (res.ok) {
                const data = await res.json();
                console.log('[SurrealViewer] Tables response:', data);
                setTables(data.tables || []);
            } else {
                console.error('[SurrealViewer] Tables fetch failed:', res.status);
            }
        } catch (e) {
            console.error('Failed to load tables:', e);
        }
    };

    const loadTableData = async (tableName: string, forceRefresh: boolean = false) => {
        setSelectedTable(tableName);
        
        // Special case for knowledge_facts text view - handled by graph loader
        if (tableName === 'knowledge_facts') {
            setLoading(false);
            return;
        }
        
        // 使用缓存（如果存在且不强制刷新）
        if (!forceRefresh && tableCache[tableName]) {
            setTableData(tableCache[tableName]);
            return;
        }
        
        setLoading(true);
        setTableData([]); // 清空旧数据，防止显示上一个表的数据

        try {
            let url = `${API_CONFIG.BASE_URL}/debug/surreal/table/${tableName}?limit=50`;
            // Apply filtering for character-specific tables
            if (activeCharacterId && (tableName === 'conversation_log' || tableName === 'episodic_memory')) {
                url += `&character_id=${activeCharacterId}`;
            }

            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                const rows = data.data || [];
                setTableData(rows);
                // 更新缓存
                setTableCache(prev => ({ ...prev, [tableName]: rows }));
            }
        } catch (e) {
            setError('加载表数据失败');
        } finally {
            setLoading(false);
        }
    };

    const loadStats = async () => {
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/debug/surreal/stats`);
            if (res.ok) {
                const data = await res.json();
                setStats(data.stats);
            }
        } catch (e) {
            console.error('Failed to load stats:', e);
        }
    };

    const loadGraph = async () => {
        setLoading(true);
        try {
            console.log('[SurrealViewer] Fetching graph data...');
            const res = await fetch(`${API_CONFIG.BASE_URL}/debug/surreal/graph/hiyori`);
            if (res.ok) {
                const data = await res.json();
                console.log('[SurrealViewer] Graph data received:', data);
                if (data.status === 'success') {
                     console.log(`[SurrealViewer] Setting graph data. Nodes: ${data.graph?.nodes?.length}, Edges: ${data.graph?.edges?.length}`);
                     setGraphData(data.graph);
                } else {
                     console.warn('[SurrealViewer] Graph status not success:', data);
                }
            } else {
                 console.error('[SurrealViewer] Graph fetch failed:', res.status, res.statusText);
            }
        } catch (e) {
            console.error('Failed to load graph:', e);
            setError('图谱加载失败');
        } finally {
            setLoading(false);
        }
    };

    const executeQuery = async () => {
        setLoading(true);
        setQueryResult(null);
        setError(null);
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/debug/surreal/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            if (res.ok) {
                setQueryResult(data);
            } else {
                setError(data.detail || '查询失败');
            }
        } catch (e: any) {
            setError(e.message || '查询执行错误');
        } finally {
            setLoading(false);
        }
    };
    
    // --- Render Helpers ---

    const formatCellValue = (key: string, value: any) => {
        if (value === null || value === undefined) return <span style={{color:'rgba(255,255,255,0.3)'}}>-</span>;
        
        // 1. Time formatting
        if (key === 'created_at' || key.includes('time')) {
            try {
                return new Date(value).toLocaleString();
            } catch (e) { return value; }
        }
        
        // 2. ID formatting (strip table prefix)
        if (key === 'id' && typeof value === 'string') {
            return value.includes(':') ? <span title={value} style={{fontFamily:'monospace', color:'#f472b6'}}>{value.split(':')[1]}</span> : value;
        }

        // 3. Boolean/Status formatting
        if (key === 'is_processed') {
            return value ? 
                <span style={{color:'#a7f3d0', background:'rgba(5, 150, 105, 0.2)', padding:'2px 6px', borderRadius:'12px', fontSize:'11px', display:'flex', alignItems:'center', gap:'4px', width:'fit-content', border:'1px solid rgba(5, 150, 105, 0.4)'}}>
                    <CheckCircle size={10} /> Processed
                </span> : 
                <span style={{color:'#fde68a', background:'rgba(180, 83, 9, 0.2)', padding:'2px 6px', borderRadius:'12px', fontSize:'11px', display:'flex', alignItems:'center', gap:'4px', width:'fit-content', border:'1px solid rgba(180, 83, 9, 0.4)'}}>
                    <Clock size={10} /> Pending
                </span>;
        }

        // 4. JSON/Object formatting
        if (typeof value === 'object') {
            return (
                <div style={{maxHeight:'60px', overflowY:'auto', fontSize:'11px', fontFamily:'monospace', whiteSpace:'pre-wrap', color:'rgba(255,255,255,0.7)'}}>
                    {JSON.stringify(value, null, 2)}
                </div>
            );
        }
        
        // 5. Long text formatting (User Input / AI Response)
        if (typeof value === 'string' && value.length > 50) {
            return <div style={{ minWidth: '200px', whiteSpace: 'pre-wrap', color:'#fff' }}>{value}</div>;
        }

        return String(value);
    };

    // Column Ordering Logic
    const getOrderedColumns = (data: any[]) => {
        if (!data || data.length === 0) return [];
        const allKeys = Object.keys(data[0]);
        // Define priority: agent_id, narrative, then others
        const priority = ['agent_id', 'narrative', 'content', 'role', 'timestamp', 'created_at', 'id'];
        
        const ordered: string[] = []; // Explicit type
        // 1. Add priority keys if they exist
        priority.forEach(key => {
            if (allKeys.includes(key)) {
                ordered.push(key);
            }
        });
        // 2. Add remaining keys (excluding hidden ones)
        const hiddenCols = ['id', 'last_hit_at'];
        allKeys.forEach(key => {
            if (!priority.includes(key) && !ordered.includes(key) && !hiddenCols.includes(key)) {
                ordered.push(key);
            }
        });
        // 3. Final cleanup: Remove hidden columns from the result, even if they were in priority
        return ordered.filter(col => !hiddenCols.includes(col));
    };

    const handleDeleteRecord = async (id: string, table: string) => {
        if (!confirm(`Are you sure you want to delete this record?\nID: ${id}`)) return;
        
        try {
            // ID usually comes as "table:id"
            let cleanId = id;
            if (id.includes(':')) {
                cleanId = id.split(':')[1];
            }
            
            const res = await fetch(`${API_CONFIG.BASE_URL}/debug/surreal/record/${table}/${cleanId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                // Optimistic UI Update
                setTableData(prev => prev.filter(row => row.id !== id));
            } else {
                alert(`Error: ${JSON.stringify(data)}`);
            }
        } catch (e) {
            alert(`Delete failed: ${e}`);
        }
    };


    
    const handleMergeEntities = async () => {
        if (!confirm("Confirm Merge?\nThis will merge duplicates based on 'entity_aliases.json'.\n(Edges will be migrated to the canonical entity, aliases deleted.)")) return;

        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/debug/memory/merge_entities`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                const logSummary = data.logs?.slice(-10)?.join('\n') || 'No logs';
                alert(`Merge Complete!\nMerged Aliases: ${data.metrics?.merged_aliases || 0}\n\n--- Last 10 Logs ---\n${logSummary}`);
                loadGraph(); // Refresh graph
            } else {
                alert(`Merge Failed: ${JSON.stringify(data)}`);
            }
        } catch (e) {
            alert(`Error triggering merge: ${e}`);
        }
    };

    // Editor State
    const [editingRecord, setEditingRecord] = useState<any>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [editorForm, setEditorForm] = useState<any>({});

    const handleEditRecord = (record: any) => {
        setEditingRecord(record);
        setIsCreating(false);
        // Deep copy for form
        setEditorForm(JSON.parse(JSON.stringify(record)));
    };
    
    const handleCreateRecord = () => {
        setEditingRecord({}); // Empty object
        setIsCreating(true);
        // Initialize form with current columns as empty string
        const initForm: any = {};
        columns.forEach(col => {
            if (col !== 'id' && col !== 'created_at') initForm[col] = '';
        });
        setEditorForm(initForm);
    };
    
    const handleSaveRecord = async () => {
        try {
            const table = selectedTable!;
            
            if (isCreating) {
                // Remove empty keys if needed, or send as is
                const res = await fetch(`${API_CONFIG.BASE_URL}/debug/surreal/record/${table}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(editorForm)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    setEditingRecord(null); // Close modal
                    loadTableData(table); // Refresh
                } else {
                    alert('Create failed: ' + JSON.stringify(data));
                }
            } else {
                // Update
                const id = editingRecord.id;
                let cleanId = id;
                if (id && id.includes(':')) cleanId = id.split(':')[1];
                
                // Don't send ID in body if merge? Surreal ignores it usually but better safe.
                const { id: _, ...updateData } = editorForm;
                
                const res = await fetch(`${API_CONFIG.BASE_URL}/debug/surreal/record/${table}/${cleanId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(updateData)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    setEditingRecord(null);
                    // Optimistic update
                    setTableData(prev => prev.map(r => r.id === id ? { ...r, ...updateData } : r));
                } else {
                    alert('Update failed: ' + JSON.stringify(data));
                }
            }
        } catch (e) {
            alert(`Error saving: ${e}`);
        }
    };

    if (!isOpen) return null;

    // Define columns based on first row of data or default
    const columns = getOrderedColumns(tableData);

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(20, 10, 30, 0.4)', // Slightly transparent background for focus
            display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1001,
            backdropFilter: 'blur(8px)', // Glassmorphism heavy blur
            transition: 'all 0.3s ease'
        }}>
            <div style={{
                background: 'linear-gradient(145deg, rgba(30, 20, 40, 0.95), rgba(45, 20, 60, 0.98))', 
                borderRadius: '24px',
                width: '900px', height: '650px',
                boxShadow: '0 20px 50px rgba(0,0,0,0.5), 0 0 0 1px rgba(255, 105, 180, 0.1)', // Subtle pink border glow
                display: 'flex', flexDirection: 'column',
                fontFamily: '"Outfit", "Segoe UI", sans-serif',
                color: '#e0e0e0', overflow: 'hidden',
                animation: 'fadeIn 0.3s ease-out'
            }}>
                {/* Header */}
                <div style={{ 
                    padding: '15px 25px', 
                    background: 'rgba(255, 105, 180, 0.05)', 
                    borderBottom: '1px solid rgba(255, 105, 180, 0.15)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '60px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ 
                            width: '36px', height: '36px', 
                            display: 'flex', alignItems: 'center', justifyContent: 'center', 
                            background: 'linear-gradient(135deg, #ec4899, #8b5cf6)', 
                            borderRadius: '10px', boxShadow: '0 4px 12px rgba(236, 72, 153, 0.3)' 
                        }}>
                            <Database size={20} color="white" />
                        </div>
                        <div>
                            <span style={{ fontWeight: '700', fontSize: '18px', color: '#fff', letterSpacing:'0.5px' }}>Memory Core</span>
                            <div style={{ fontSize: '10px', color: '#f472b6', opacity: 0.8, textTransform:'uppercase', letterSpacing:'1px' }}>SurrealDB Explorer</div>
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '10px' }}>
                         <button 
                            onClick={() => onClose && onClose()} 
                            style={{
                                background:'rgba(255, 255, 255, 0.05)', border:'1px solid rgba(255,255,255,0.1)', 
                                color:'#f472b6', width:'32px', height:'32px', borderRadius:'50%', 
                                display:'flex', alignItems:'center', justifyContent:'center',
                                cursor:'pointer', transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 105, 180, 0.2)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Main Content */}
                <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    
                    {/* Custom Sidebar - Glassy */}
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
                            onClick={() => { setActiveTab('tables'); loadTableData('conversation_log'); }}
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
                            onClick={() => { setActiveTab('tables'); loadTableData('episodic_memory'); }}
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
                            onClick={() => { setActiveTab('graph'); }}
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
                            onClick={() => { setActiveTab('tables'); setSelectedTable('knowledge_facts'); }}
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

                    {/* Content Area */}
                    <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', backgroundColor: 'rgba(0,0,0,0.2)' }}>
                        {activeTab === 'tables' && (
                            <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                                {selectedTable === 'knowledge_facts' ? (
                                    // Special View for Knowledge Facts Text
                                    <div style={{flex:1, overflow:'auto', padding:'25px'}}>
                                        <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                                            <h3 style={{display:'flex', alignItems:'center', gap:'10px', margin:0, color:'#93c5fd'}}>
                                                <Braces size={22} /> Knowledge Facts (Text View)
                                            </h3>
                                            <button 
                                                onClick={loadGraph} 
                                                style={{
                                                    padding:'8px 16px', background:'linear-gradient(135deg, #3b82f6, #2563eb)', 
                                                    color:'white', border:'none', borderRadius:'8px', cursor:'pointer', 
                                                    display:'flex', alignItems:'center', gap:'6px',
                                                    boxShadow: '0 4px 10px rgba(37, 99, 235, 0.3)', fontWeight:'600', fontSize:'13px'
                                                }}>
                                                <RefreshCw size={14} /> Refresh Data
                                            </button>
                                        </div>
                                        {/* Reuse graphData to list edges */}
                                        {loading ? (
                                            <div style={{color:'#60a5fa', display:'flex', alignItems:'center', gap:'8px', fontSize:'14px'}}>
                                                <RefreshCw className="spin" size={18} /> Retrieving neural connections...
                                            </div>
                                        ) : (
                                            <div style={{display:'flex', flexDirection:'column', gap:'12px'}}>
                                                {graphData?.edges?.map((edge, idx) => (
                                                    <div 
                                                        key={idx} 
                                                        onClick={() => setDetailEdge(edge)}
                                                        style={{
                                                            display:'flex', alignItems:'center', gap:'15px', 
                                                            padding:'12px 16px', background:'rgba(30, 41, 59, 0.6)', borderRadius:'10px', 
                                                            border:'1px solid rgba(148, 163, 184, 0.1)',
                                                            cursor: 'pointer', transition: 'all 0.2s ease'
                                                        }}
                                                        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'; e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.4)'; }}
                                                        onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)'; e.currentTarget.style.borderColor = 'rgba(148, 163, 184, 0.1)'; }}
                                                    >
                                                        <div style={{fontWeight:'600', color:'#e2e8f0', minWidth:'120px', textAlign:'right'}}>
                                                            {graphData.nodes.find(n => n.id === edge.from)?.label || edge.from}
                                                        </div>
                                                        <div style={{
                                                            padding:'4px 10px', borderRadius:'20px', background:'rgba(59, 130, 246, 0.2)', 
                                                            fontSize:'11px', color:'#93c5fd', textTransform:'uppercase', fontWeight:'700',
                                                            border: '1px solid rgba(59, 130, 246, 0.3)'
                                                        }}>
                                                            {edge.label}
                                                        </div>
                                                        <div style={{fontWeight:'600', color:'#e2e8f0', flex:1}}>
                                                            {graphData.nodes.find(n => n.id === edge.to)?.label || edge.to}
                                                        </div>
                                                        <div style={{color:'rgba(255,255,255,0.4)', fontSize:'12px'}}>›</div>
                                                    </div>
                                                ))}
                                                {(!graphData?.edges || graphData.edges.length === 0) && (
                                                    <div style={{padding:'40px', textAlign:'center', color:'rgba(255,255,255,0.4)', fontSize:'14px'}}>
                                                        <Sparkles size={24} style={{marginBottom:'10px', opacity:0.5}} />
                                                        <br/>
                                                        No relationships found in the current cognitive graph.
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    // Standard Table View (Optimized for Conversation)
                                    <>
                                        <div style={{ 
                                            padding: '15px 25px', borderBottom: '1px solid rgba(255, 105, 180, 0.1)', 
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            background: 'rgba(0,0,0,0.1)'
                                        }}>
                                            <span style={{ fontWeight: '700', color: '#f472b6', display:'flex', alignItems:'center', gap:'10px', fontSize:'16px' }}>
                                                <TableIcon size={18} /> {selectedTable} <span style={{fontSize:'12px', opacity:0.7, fontWeight:'400'}}>({tableData.length} records)</span>
                                            </span>
                                    <button onClick={() => loadTableData(selectedTable!, true)} style={{ cursor: 'pointer', background: 'none', border: 'none', color:'#f472b6', marginRight:'10px' }}>
                                                <RefreshCw size={18} />
                                            </button>
                                            <button 
                                                onClick={handleCreateRecord}
                                                style={{ 
                                                    cursor: 'pointer', background: 'linear-gradient(135deg, #ec4899, #8b5cf6)', border: 'none', color:'white',
                                                    padding:'6px 12px', borderRadius:'6px', display:'flex', alignItems:'center', gap:'6px', fontSize:'12px', fontWeight:'600'
                                                }}>
                                                <Plus size={14} /> New
                                            </button>
                                        </div>
                                        <div style={{ flex: 1, overflow: 'auto' }}>
                                            {loading ? (
                                                <div style={{ padding: '30px', color: '#f472b6', display:'flex', alignItems:'center', gap:'10px', fontSize:'14px' }}>
                                                    <RefreshCw className="spin" size={20} /> Loading data from Core...
                                                </div>
                                            ) : (
                                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                                                    <thead>
                                                        <tr style={{ textAlign: 'left', backgroundColor: 'rgba(0,0,0,0.2)', color: '#a5b4fc', position: 'sticky', top: 0, zIndex: 1, backdropFilter:'blur(4px)' }}>
                                                            <th style={{ padding: '12px 15px', borderBottom: '1px solid rgba(255, 105, 180, 0.1)', width: '40px', textAlign: 'center' }}>#</th>
                                                            <th style={{ padding: '12px 15px', borderBottom: '1px solid rgba(255, 105, 180, 0.1)', width:'90px' }}>Action</th>
                                                            {columns.map(col => (
                                                                <th key={col} style={{ padding: '12px 15px', borderBottom: '1px solid rgba(255, 105, 180, 0.1)', whiteSpace: 'nowrap', fontWeight:'600' }}>{col}</th>
                                                            ))}
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {tableData.map((row, i) => (
                                                            <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', backgroundColor: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                                                                <td style={{ padding: '12px 15px', color: '#e2e8f0', verticalAlign: 'top', textAlign: 'center', opacity: 0.5, fontFamily: 'monospace' }}>{i + 1}</td>
                                                                <td style={{ padding: '12px 15px', color: '#e2e8f0', verticalAlign: 'top', width:'90px', display:'flex', gap:'5px' }}>
                                                                    <button 
                                                                        onClick={() => handleEditRecord(row)}
                                                                        style={{
                                                                            background:'rgba(255, 255, 255, 0.1)', border:'1px solid rgba(255, 255, 255, 0.2)', 
                                                                            color:'#f472b6', borderRadius:'6px', padding:'6px', cursor:'pointer',
                                                                            display:'flex', alignItems:'center', justifyContent:'center'
                                                                        }}
                                                                        title="Edit Record"
                                                                     >
                                                                         <Edit size={14} />
                                                                     </button>
                                                                     <button 
                                                                        onClick={() => handleDeleteRecord(row.id, selectedTable!)}
                                                                        style={{
                                                                            background:'rgba(239, 68, 68, 0.1)', border:'1px solid rgba(239, 68, 68, 0.2)', 
                                                                            color:'#f87171', borderRadius:'6px', padding:'6px', cursor:'pointer',
                                                                            display:'flex', alignItems:'center', justifyContent:'center'
                                                                        }}
                                                                        title="Delete Record"
                                                                     >
                                                                         <Trash2 size={14} />
                                                                     </button>
                                                                </td>
                                                                {columns.map(col => (
                                                                    <td key={col} style={{ padding: '12px 15px', color: '#e2e8f0', verticalAlign: 'top' }}>
                                                                        {formatCellValue(col, row[col])}
                                                                    </td>
                                                                ))}
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>
                        )}
                        {/* Graph Visualization */}
                        {activeTab === 'graph' && (
                            <div style={{ height: '100%', display: 'flex', position: 'relative' }}>
                                {/* Main Graph Area */}
                                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                                    <div style={{ padding: '15px 25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background:'rgba(0,0,0,0.1)' }}>
                                        <h3 style={{display:'flex', alignItems:'center', gap:'10px', margin:0, color:'#c084fc'}}>
                                            <Network size={20} /> Knowledge Graph
                                        </h3>
                                        <div style={{display:'flex', gap:'15px', alignItems:'center'}}>
                                            <div style={{fontSize:'12px', color:'rgba(255,255,255,0.6)', display:'flex', alignItems:'center', gap:'12px'}}>
                                                <div style={{display:'flex', alignItems:'center', gap:'6px'}}><span style={{width:'8px',height:'8px',borderRadius:'50%',background:'#f472b6', boxShadow:'0 0 5px #f472b6'}}></span> Character</div>
                                                <div style={{display:'flex', alignItems:'center', gap:'6px'}}><span style={{width:'8px',height:'8px',borderRadius:'50%',background:'#60a5fa', boxShadow:'0 0 5px #60a5fa'}}></span> Entity</div>
                                            </div>
                                            <button
                                                onClick={handleMergeEntities}
                                                style={{
                                                    padding: '6px 14px', backgroundColor: 'rgba(236, 72, 153, 0.2)', color: '#fbcfe8',
                                                    border: '1px solid rgba(236, 72, 153, 0.4)', borderRadius: '6px', cursor: 'pointer',
                                                    display:'flex', alignItems:'center', gap:'6px', fontSize:'12px', fontWeight:'600'
                                                }}
                                                title="Configured in python_backend/config/entity_aliases.json"
                                            >
                                                <GitMerge size={12} /> Merge & Clean
                                            </button>
                                            <button
                                                onClick={loadGraph}
                                                style={{
                                                    padding: '6px 14px', backgroundColor: 'rgba(139, 92, 246, 0.2)', color: '#ddd6fe',
                                                    border: '1px solid rgba(139, 92, 246, 0.4)', borderRadius: '6px', cursor: 'pointer',
                                                    display:'flex', alignItems:'center', gap:'6px', fontSize:'12px', fontWeight:'600'
                                                }}
                                            >
                                                <RefreshCw size={12} /> Refresh
                                            </button>
                                        </div>
                                    </div>
                                    <div style={{ flex: 1, position: 'relative', overflow: 'hidden', backgroundColor: 'rgba(15, 23, 42, 0.4)', margin: '0' }}>
                                        {loading ? (
                                            <div style={{ color: '#c084fc', padding: '30px', display: 'flex', justifyContent: 'center', alignItems: 'center', height:'100%', gap:'12px' }}>
                                                <RefreshCw className="spin" size={24} /> Visualizing Neural Network...
                                            </div>
                                        ) : (
                                            <SimpleGraph 
                                                nodes={graphData?.nodes || []} 
                                                edges={graphData?.edges || []}
                                                onNodeSelect={setSelectedNode}
                                            />
                                        )}
                                    </div>
                                </div>
                                
                                {/* Details Panel (Slide over) */}
                                {selectedNode && (
                                    <div style={{
                                        width: '280px', borderLeft: '1px solid rgba(255, 105, 180, 0.1)', backgroundColor: 'rgba(20, 10, 30, 0.6)',
                                        display: 'flex', flexDirection: 'column', padding: '20px',
                                        boxShadow: '-10px 0 30px rgba(0,0,0,0.5)', zIndex: 10,
                                        backdropFilter: 'blur(15px)'
                                    }}>
                                        <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                                            <h3 style={{margin:0, color:'#fff', fontSize:'18px'}}>{selectedNode.label}</h3>
                                            <button onClick={() => setSelectedNode(null)} style={{background:'none',border:'none',color:'rgba(255,255,255,0.5)',cursor:'pointer'}}><X size={18} /></button>
                                        </div>
                                        <div style={{fontSize:'11px', color:'rgba(255,255,255,0.4)', marginBottom:'5px', fontFamily:'monospace'}}>ID: {selectedNode.id}</div>
                                        <div style={{fontSize:'12px', color:'#f472b6', marginBottom:'20px', fontWeight:'600', textTransform:'uppercase', letterSpacing:'0.5px'}}>Type: {selectedNode.group}</div>
                                        
                                        <div style={{flex:1, overflowY:'auto'}}>
                                            <h4 style={{fontSize:'13px', color:'#e2e8f0', borderBottom:'1px solid rgba(255,255,255,0.1)', paddingBottom:'8px'}}>Attributes</h4>
                                            <div style={{marginTop:'12px', fontSize:'13px', color:'rgba(255,255,255,0.8)'}}>
                                                <div style={{marginBottom:'8px', display:'flex', justifyContent:'space-between'}}>
                                                    <span style={{color:'rgba(255,255,255,0.5)'}}>Status</span>
                                                    <span>Active</span>
                                                </div>
                                                <div style={{marginBottom:'8px', display:'flex', justifyContent:'space-between'}}>
                                                    <span style={{color:'rgba(255,255,255,0.5)'}}>Weight</span>
                                                    <span>1.0</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Record Editor Modal */}
                {editingRecord && (
                    <div style={{
                        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(5px)',
                        display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 2000
                    }}>
                        <div style={{
                            width: '500px', maxHeight: '90vh', overflowY: 'auto',
                            background: '#1e1e2e', borderRadius: '16px', border: '1px solid rgba(255,105,180,0.3)',
                            padding: '25px', boxShadow: '0 10px 40px rgba(0,0,0,0.5)'
                        }}>
                             <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                                <h3 style={{margin:0, color:'#f472b6'}}>{isCreating ? 'Create New Record' : 'Edit Record'}</h3>
                                <button onClick={() => setEditingRecord(null)} style={{background:'none', border:'none', color:'rgba(255,255,255,0.5)', cursor:'pointer'}}><X size={20}/></button>
                             </div>
                             
                             <div style={{display:'flex', flexDirection:'column', gap:'15px'}}>
                                {Object.keys(isCreating ? editorForm : editingRecord).map(key => (
                                    (key !== 'id' && key !== 'created_at' && key !== 'embedding') && (
                                        <div key={key}>
                                            <label style={{display:'block', fontSize:'12px', color:'rgba(255,255,255,0.6)', marginBottom:'5px'}}>{key}</label>
                                            {key === 'content' || key === 'narrative' ? (
                                                <textarea 
                                                    value={editorForm[key] || ''}
                                                    onChange={e => setEditorForm({...editorForm, [key]: e.target.value})}
                                                    style={{
                                                        width:'100%', background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.1)', 
                                                        color:'#fff', padding:'8px', borderRadius:'6px', minHeight:'80px', fontFamily:'inherit'
                                                    }}
                                                />
                                            ) : (
                                                <input 
                                                    type="text" 
                                                    value={typeof editorForm[key] === 'object' ? JSON.stringify(editorForm[key]) : (editorForm[key] || '')}
                                                    onChange={e => setEditorForm({...editorForm, [key]: e.target.value})}
                                                    style={{
                                                        width:'100%', background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.1)', 
                                                        color:'#fff', padding:'8px', borderRadius:'6px', fontFamily:'inherit'
                                                    }}
                                                />
                                            )}
                                        </div>
                                    )
                                ))}
                                {isCreating && (
                                    <div style={{marginTop:'10px', fontSize:'12px', color:'rgba(255,255,255,0.4)'}}>
                                        * Note: Fields are inferred from current table view. 
                                    </div>
                                )}
                             </div>
                             
                             <div style={{marginTop:'25px', display:'flex', justifyContent:'flex-end', gap:'10px'}}>
                                <button 
                                    onClick={() => setEditingRecord(null)}
                                    style={{
                                        padding:'8px 16px', borderRadius:'8px', background:'transparent', border:'1px solid rgba(255,255,255,0.2)', color:'rgba(255,255,255,0.8)', cursor:'pointer'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button 
                                    onClick={handleSaveRecord}
                                    style={{
                                        padding:'8px 24px', borderRadius:'8px', background:'linear-gradient(135deg, #ec4899, #8b5cf6)', border:'none', color:'white', fontWeight:'600', cursor:'pointer'
                                    }}
                                >
                                    Save
                                </button>
                             </div>
                        </div>
                    </div>
                )}
                {/* Detail Edge Modal */}
                {detailEdge && (
                    <div style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        zIndex: 10000, backdropFilter: 'blur(5px)'
                    }} onClick={() => setDetailEdge(null)}>
                        <div 
                            onClick={(e) => e.stopPropagation()}
                            style={{
                                background: 'linear-gradient(135deg, rgba(30, 20, 50, 0.95), rgba(20, 10, 40, 0.98))',
                                border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '16px',
                                padding: '24px', maxWidth: '600px', width: '90%', maxHeight: '80vh', overflow: 'auto',
                                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                                <h3 style={{ color: '#c084fc', margin: 0, fontSize: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <Braces size={20} /> Edge Detail
                                </h3>
                                <button 
                                    onClick={() => setDetailEdge(null)}
                                    style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', fontSize: '24px' }}
                                >×</button>
                            </div>
                            <pre style={{
                                background: 'rgba(0,0,0,0.3)', borderRadius: '10px', padding: '16px',
                                color: '#e2e8f0', fontSize: '12px', lineHeight: '1.6', overflow: 'auto',
                                fontFamily: 'Consolas, Monaco, monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-all'
                            }}>
                                {JSON.stringify(detailEdge, null, 2)}
                            </pre>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

// 核心图谱引擎 (v2: 支持缩放/平移/物理稳定)
// Remove 'containerSize' from props, handle it internally
const SimpleGraph: React.FC<{ nodes: any[], edges: any[], onNodeSelect: (node: any) => void }> = ({ nodes, edges, onNodeSelect }) => {
    const parentRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const simulationRef = useRef<any[]>([]);
    
    // Canvas Size Management
    const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 });
    
    // Resize Observer
    useEffect(() => {
        if (!parentRef.current) return;
        
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                setCanvasSize({ width, height });
            }
        });
        
        resizeObserver.observe(parentRef.current);
        return () => resizeObserver.disconnect();
    }, []);

    // 视口状态 (Viewport)
    const [transform, setTransform] = useState({ x: 0, y: 0, k: 0.8 }); // k is scale
    
    const [isDraggingCanvas, setIsDraggingCanvas] = useState(false);
    const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 });
    
    // 交互状态
    const [draggingNode, setDraggingNode] = useState<any>(null);
    const [hoverNode, setHoverNode] = useState<any>(null);

    // 物理引擎状态
    const alphaRef = useRef(1.0); // 模拟热度，随时间衰减

    // 初始化/更新节点
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        
        // 增量更新：保留已有节点的位置，只为新节点随机位置
        const newNodes = nodes.map(n => {
            const existing = simulationRef.current.find(en => en.id === n.id);
            if (existing) {
                // 更新属性但保留物理状态
                return { ...existing, ...n, radius: n.group === 'character' ? 20 : (n.group === 'implicit' ? 6 : 12) };
            } else {
                return {
                    ...n,
                    x: Math.random() * canvasSize.width, 
                    y: Math.random() * canvasSize.height,
                    vx: 0,
                    vy: 0,
                    radius: n.group === 'character' ? 20 : (n.group === 'implicit' ? 6 : 12)
                };
            }
        });
        
        simulationRef.current = newNodes;
        alphaRef.current = 1.0; // 数据更新时重置热度，重新布局
    }, [nodes, canvasSize]); // 依赖 nodes 和 canvasSize 变化

    // 动画与物理循环
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;

        const animate = () => {
            if (!canvas) return;
            
            // 物理计算步进 (当热度 alpha > 0.01 或 正在拖拽时计算)
            if (alphaRef.current > 0.01 || draggingNode) {
                simulationRef.current.forEach(node => {
                    if (node === draggingNode) return;

                    // 1. 向心力 (Centering) - 弱
                    const cx = canvasSize.width / 2;
                    const cy = canvasSize.height / 2;
                    node.vx += (cx - node.x) * 0.002 * alphaRef.current;
                    node.vy += (cy - node.y) * 0.002 * alphaRef.current;

                    // 2. 斥力 (Many-Body Repulsion) - 强
                    simulationRef.current.forEach(other => {
                        if (node === other) return;
                        const dx = node.x - other.x;
                        const dy = node.y - other.y;
                        let dist = Math.sqrt(dx*dx + dy*dy);
                        if (dist < 1) dist = 1; 
                        
                        // 距离越近斥力越大
                        if (dist < 300) {
                            const force = (200 * alphaRef.current) / (dist * 0.8);
                            node.vx += (dx / dist) * force;
                            node.vy += (dy / dist) * force;
                        }
                    });

                    // 3. 连接力 (Link Spring)
                    edges.forEach(edge => {
                         // 查找端点对象
                        const src = simulationRef.current.find(n => n.id === edge.from);
                        const dst = simulationRef.current.find(n => n.id === edge.to);
                        
                        if (src && dst) {
                            if (src === node) {
                                const dx = dst.x - node.x;
                                const dy = dst.y - node.y;
                                node.vx += dx * 0.015 * alphaRef.current;
                                node.vy += dy * 0.015 * alphaRef.current;
                            } else if (dst === node) {
                                const dx = src.x - node.x;
                                const dy = src.y - node.y;
                                node.vx += dx * 0.015 * alphaRef.current;
                                node.vy += dy * 0.015 * alphaRef.current;
                            }
                        }
                    });

                    // 速度限制与阻尼
                    node.vx *= 0.9 + (0.05 * (1 - alphaRef.current)); // 随着稳定阻尼增加
                    node.vy *= 0.9 + (0.05 * (1 - alphaRef.current));
                    
                    node.x += node.vx;
                    node.y += node.vy;
                });
                
                // 热度衰减
                if (!draggingNode) {
                    alphaRef.current *= 0.99; // 每一帧衰减
                } else {
                    alphaRef.current = 0.3; // 拖拽时保持一定热度以响应变化
                }
            }

            // --- 渲染阶段 ---
            ctx.save();
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // Transparent background for Graph (handled by parent container color)
            
            // 应用视口变换 (Pan/Zoom)
            ctx.translate(transform.x, transform.y);
            ctx.scale(transform.k, transform.k);

            // 绘制连线
            ctx.lineWidth = 1;
            edges.forEach(edge => {
                const src = simulationRef.current.find(n => n.id === edge.from);
                const dst = simulationRef.current.find(n => n.id === edge.to);
                if (src && dst) {
                    const isFocus = (src === hoverNode || dst === hoverNode);
                    
                    ctx.beginPath();
                    ctx.moveTo(src.x, src.y);
                    ctx.lineTo(dst.x, dst.y);
                    
                    // Neon lines
                    ctx.strokeStyle = isFocus ? '#fff' : 'rgba(139, 92, 246, 0.3)';
                    ctx.lineWidth = isFocus ? 2 / transform.k : 1 / transform.k;
                    ctx.stroke();

                     // 标签
                    if (isFocus || transform.k > 1.2) {
                        ctx.fillStyle = isFocus ? '#fff' : 'rgba(255,255,255,0.6)';
                        ctx.font = `${10/transform.k}px Arial`;
                        ctx.fillText(edge.label || '', (src.x + dst.x)/2, (src.y + dst.y)/2);
                    }
                }
            });

            // 绘制节点
            simulationRef.current.forEach(node => {
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
                
                // Neon Nodes
                let color = '#94a3b8';
                let glow = 'transparent';
                
                if (node.group === 'character') { color = '#f472b6'; glow = 'rgba(244, 114, 182, 0.5)'; }
                else if (node.group === 'knowledge') { color = '#60a5fa'; glow = 'rgba(96, 165, 250, 0.5)'; }
                else if (node.group === 'agent') { color = '#a78bfa'; glow = 'rgba(167, 139, 250, 0.5)'; }
                
                ctx.shadowBlur = 10;
                ctx.shadowColor = glow;
                ctx.fillStyle = color;
                ctx.fill();
                ctx.shadowBlur = 0; // reset
                
                if (node === hoverNode || node === draggingNode) {
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 2 / transform.k;
                    ctx.stroke();
                }

                if (transform.k > 0.6 || node.group === 'character') {
                     ctx.fillStyle = '#f1f5f9';
                     ctx.font = `${12/transform.k}px "Segoe UI", sans-serif`;
                     ctx.fillText(node.label || node.id, node.x + node.radius + 4, node.y + (4/transform.k));
                }
            });

            ctx.restore();
            animationFrameId = requestAnimationFrame(animate);
        };
        
        animate();
        return () => cancelAnimationFrame(animationFrameId);
    }, [nodes, edges, draggingNode, hoverNode, transform, canvasSize]);

    // --- 事件处理 (坐标映射逻辑) ---
    const toWorldPos = (clientX: number, clientY: number) => {
        if (!canvasRef.current) return {x:0,y:0};
        const rect = canvasRef.current.getBoundingClientRect();
        return {
            x: (clientX - rect.left - transform.x) / transform.k,
            y: (clientY - rect.top - transform.y) / transform.k
        };
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        const worldPos = toWorldPos(e.clientX, e.clientY);
        
        const clickedNode = simulationRef.current.find(node => {
            const dx = node.x - worldPos.x;
            const dy = node.y - worldPos.y;
            return Math.sqrt(dx*dx + dy*dy) < (node.radius + 5 / transform.k);
        });

        if (clickedNode) {
            setDraggingNode(clickedNode);
            onNodeSelect(clickedNode);
            alphaRef.current = 0.5;
        } else {
            setIsDraggingCanvas(true);
            setLastMousePos({ x: e.clientX, y: e.clientY });
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (draggingNode) {
             const worldPos = toWorldPos(e.clientX, e.clientY);
             draggingNode.x = worldPos.x;
             draggingNode.y = worldPos.y;
             draggingNode.vx = 0; 
             draggingNode.vy = 0;
             return;
        }
        if (isDraggingCanvas) {
            const dx = e.clientX - lastMousePos.x;
            const dy = e.clientY - lastMousePos.y;
            setTransform(t => ({ ...t, x: t.x + dx, y: t.y + dy }));
            setLastMousePos({ x: e.clientX, y: e.clientY });
            return;
        }
        const worldPos = toWorldPos(e.clientX, e.clientY);
        const hovered = simulationRef.current.find(node => {
            const dx = node.x - worldPos.x;
            const dy = node.y - worldPos.y;
            return Math.sqrt(dx*dx + dy*dy) < (node.radius + 5 / transform.k);
        });
        setHoverNode(hovered || null);
    };

    const handleMouseUp = () => {
        setDraggingNode(null);
        setIsDraggingCanvas(false);
    };

    const handleWheel = (e: React.WheelEvent) => {
        const zoomIntensity = 0.1;
        const delta = e.deltaY > 0 ? -zoomIntensity : zoomIntensity;
        let newK = transform.k * (1 + delta);
        if (newK < 0.1) newK = 0.1;
        if (newK > 5) newK = 5;
        setTransform(t => ({ ...t, k: newK }));
    };

    return (
        <div ref={parentRef} style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
            <canvas 
                ref={canvasRef} 
                width={canvasSize.width} 
                height={canvasSize.height}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onWheel={handleWheel}
                style={{ width: '100%', height: '100%', cursor: isDraggingCanvas ? 'grabbing' : (hoverNode ? 'pointer' : 'default') }}
            />
            {/* HUD Overlay - Minimalist */}
            <div style={{
                position: 'absolute', bottom: '15px', right: '15px',
                display: 'flex', gap: '10px'
            }}>
                 <button 
                    onClick={() => setTransform({ x: 0, y: 0, k: 0.8 })}
                    style={{
                        padding: '6px 12px', background: 'rgba(255,255,255,0.1)',
                        border: '1px solid rgba(255,255,255,0.2)', borderRadius: '20px',
                        color: '#fff', fontSize: '11px', cursor: 'pointer',
                        backdropFilter: 'blur(5px)'
                    }}
                >
                    Reset View
                </button>
            </div>
        </div>
    );
}

export default SurrealViewer;
