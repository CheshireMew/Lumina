/**
 * DataViewer - 通用数据可视化组件 (Refactored)
 * 包含：表浏览、数据查看、查询控制台
 */
import React, { useState, useEffect } from 'react';
import { Database, X, RefreshCw, GitMerge, Network } from 'lucide-react';
import { API_CONFIG } from '../../config';

import { Sidebar } from './Sidebar';
import { TableSection } from './TableSection';
import { SimpleGraph } from './SimpleGraph';
import { RecordEditor } from './RecordEditor';
import { EdgeDetailModal } from './EdgeDetailModal';
import { TableInfo, QueryResult, DataViewerProps } from './types';

const DataViewer: React.FC<DataViewerProps> = ({ 
    isOpen, 
    onClose, 
    activeCharacterId, 
    dataSource = 'surreal' 
}) => {
    const [activeTab, setActiveTab] = useState<'tables' | 'query' | 'stats' | 'graph'>('tables');
    const [tables, setTables] = useState<TableInfo[]>([]);
    const [selectedTable, setSelectedTable] = useState<string | null>('conversation_log');
    const [tableData, setTableData] = useState<any[]>([]);
    const [query, setQuery] = useState('SELECT * FROM episodic_memory ORDER BY created_at DESC LIMIT 10;'); 
    const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [graphData, setGraphData] = useState<{nodes: any[], edges: any[]} | null>(null);
    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [detailEdge, setDetailEdge] = useState<any>(null); 
    
    const [tableCache, setTableCache] = useState<Record<string, any[]>>({});

    useEffect(() => {
        if (isOpen) {
            loadTables();
            if (selectedTable) {
                loadTableData(selectedTable);
            }
        }
    }, [isOpen]);

    useEffect(() => {
        if (activeTab === 'graph' && !graphData) {
            loadGraph();
        }
    }, [activeTab]);

    useEffect(() => {
        if (activeCharacterId) {
            setTableCache({});
            if (isOpen && selectedTable) {
                loadTableData(selectedTable, true);
            }
        }
    }, [activeCharacterId]);

    const loadTables = async () => {
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/admin/tables`);
            if (res.ok) {
                const data = await res.json();
                setTables(data.tables || []);
            }
        } catch (e) {
            console.error('Failed to load tables:', e);
        }
    };

    const loadTableData = async (tableName: string, forceRefresh: boolean = false) => {
        setSelectedTable(tableName);
        if (tableName === 'knowledge_facts') {
            setLoading(false);
            return;
        }
        if (!forceRefresh && tableCache[tableName]) {
            setTableData(tableCache[tableName]);
            return;
        }
        setLoading(true);
        setTableData([]);
        try {
            let url = `${API_CONFIG.BASE_URL}/admin/table/${tableName}?limit=50`;
            if (activeCharacterId && (tableName === 'conversation_log' || tableName === 'episodic_memory')) {
                url += `&character_id=${activeCharacterId}`;
            }
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                const rows = data.data || [];
                setTableData(rows);
                setTableCache(prev => ({ ...prev, [tableName]: rows }));
            }
        } catch (e) {
            setError('Failed to load table data');
        } finally {
            setLoading(false);
        }
    };

    const loadGraph = async () => {
        setLoading(true);
        try {
             const res = await fetch(`${API_CONFIG.BASE_URL}/debug/brain_dump?character_id=${activeCharacterId || 'hiyori'}`);
             if (res.ok) {
                 const data = await res.json();
                 if (data.status === 'success' && data.graph) {
                     setGraphData(data.graph);
                 }
             }
        } catch (e) {
            console.error('Graph load failed');
        } finally {
            setLoading(false);
        }
    };

    const executeQuery = async () => {
        setLoading(true);
        setQueryResult(null);
        setError(null);
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/admin/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            if (res.ok) {
                setQueryResult({ status: 'success', result: data.result || [] });
            } else {
                setError(data.detail || 'Query failed');
            }
        } catch (e: any) {
            setError(e.message || 'Execution error');
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteRecord = async (idOfRow: any) => {
        let rawId = idOfRow;
        if (typeof idOfRow === 'object' && idOfRow !== null && idOfRow.id) rawId = idOfRow.id; 
        const idStr = String(rawId);
        
        if (!confirm(`Are you sure you want to delete this record?\nID: ${idStr}`)) return;
        
        try {
            const encodedId = encodeURIComponent(idStr);
            const res = await fetch(`${API_CONFIG.BASE_URL}/admin/record/${selectedTable}/${encodedId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (data.status === 'success') {
                setTableData(prev => prev.filter(row => row.id !== idOfRow));
            } else {
                alert(`Error: ${JSON.stringify(data)}`);
            }
        } catch (e) {
            alert(`Delete failed: ${e}`);
        }
    };

    const handleMergeEntities = async () => {
        if (!confirm("Confirm Merge?")) return;
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/debug/memory/merge_entities`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                alert(`Merge Complete!`);
                loadGraph();
            }
        } catch (e) {
            alert(`Error: ${e}`);
        }
    };

    // Editor Logic
    const [editingRecord, setEditingRecord] = useState<any>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [editorForm, setEditorForm] = useState<any>({});

    const handleEditRecord = (record: any) => {
        setEditingRecord(record);
        setIsCreating(false);
        setEditorForm(JSON.parse(JSON.stringify(record)));
    };
    
    const handleCreateRecord = () => {
        setEditingRecord({});
        setIsCreating(true);
        const initForm: any = {};
        if (tableData.length > 0) {
            Object.keys(tableData[0]).forEach(col => {
                if (col !== 'id' && col !== 'created_at') initForm[col] = '';
            });
        }
        setEditorForm(initForm);
    };
    
    const handleSaveRecord = async () => {
        try {
            const table = selectedTable!;
            if (!isCreating) {
                let id = editingRecord.id;
                if (typeof id === 'object' && id?.id) id = id.id;
                const cleanId = String(id).includes(':') ? String(id).split(':')[1] : String(id);
                const { id: _, ...updateData } = editorForm;
                const res = await fetch(`${API_CONFIG.BASE_URL}/admin/record/${table}/${encodeURIComponent(cleanId)}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ data: updateData })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    setEditingRecord(null);
                    setTableData(prev => prev.map(r => r.id === editingRecord.id ? { ...r, ...updateData } : r));
                }
            }
        } catch (e) {
            alert(`Error saving: ${e}`);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(20, 10, 30, 0.4)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1001,
            backdropFilter: 'blur(8px)', transition: 'all 0.3s ease'
        }}>
            <div style={{
                background: 'linear-gradient(145deg, rgba(30, 20, 40, 0.95), rgba(45, 20, 60, 0.98))', 
                borderRadius: '24px', width: '900px', height: '650px',
                boxShadow: '0 20px 50px rgba(0,0,0,0.5), 0 0 0 1px rgba(255, 105, 180, 0.1)',
                display: 'flex', flexDirection: 'column',
                fontFamily: '"Outfit", "Segoe UI", sans-serif', color: '#e0e0e0', overflow: 'hidden'
            }}>
                {/* Header */}
                <div style={{ 
                    padding: '15px 25px', background: 'rgba(255, 105, 180, 0.05)', 
                    borderBottom: '1px solid rgba(255, 105, 180, 0.15)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '60px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ 
                            width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', 
                            background: 'linear-gradient(135deg, #ec4899, #8b5cf6)', borderRadius: '10px'
                        }}>
                            <Database size={20} color="white" />
                        </div>
                        <div>
                            <span style={{ fontWeight: '700', fontSize: '18px', color: '#fff' }}>Memory Core</span>
                        </div>
                    </div>
                    <button onClick={onClose} style={{ background:'none', border:'none', color:'#f472b6', cursor:'pointer' }}>
                        <X size={24} />
                    </button>
                </div>

                <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    <Sidebar 
                        activeTab={activeTab} 
                        selectedTable={selectedTable}
                        onTabChange={setActiveTab}
                        onTableSelect={loadTableData}
                    />

                    <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', backgroundColor: 'rgba(0,0,0,0.2)' }}>
                        {activeTab === 'tables' && (
                            <TableSection 
                                selectedTable={selectedTable}
                                tableData={tableData}
                                loading={loading}
                                graphData={graphData}
                                onRefreshTable={() => loadTableData(selectedTable!, true)}
                                onRefreshGraph={loadGraph}
                                onCreateRecord={handleCreateRecord}
                                onEditRecord={handleEditRecord}
                                onDeleteRecord={handleDeleteRecord}
                                onEdgeClick={setDetailEdge}
                            />
                        )}
                        {activeTab === 'graph' && (
                            <div style={{ height: '100%', display: 'flex', position: 'relative' }}>
                                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                                    <div style={{ padding: '15px 25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background:'rgba(0,0,0,0.1)' }}>
                                        <h3 style={{display:'flex', alignItems:'center', gap:'10px', margin:0, color:'#c084fc'}}>
                                            <Network size={20} /> Knowledge Graph
                                        </h3>
                                        <div style={{display:'flex', gap:'15px'}}>
                                            <button onClick={handleMergeEntities} style={{ padding: '6px 14px', backgroundColor: 'rgba(236, 72, 153, 0.2)', color: '#fbcfe8', border: '1px solid rgba(236, 72, 153, 0.4)', borderRadius: '6px', cursor: 'pointer' }}>
                                                <GitMerge size={12} /> Merge & Clean
                                            </button>
                                            <button onClick={loadGraph} style={{ padding: '6px 14px', backgroundColor: 'rgba(139, 92, 246, 0.2)', color: '#ddd6fe', border: '1px solid rgba(139, 92, 246, 0.4)', borderRadius: '6px', cursor: 'pointer' }}>
                                                <RefreshCw size={12} /> Refresh
                                            </button>
                                        </div>
                                    </div>
                                    <div style={{ flex: 1, position: 'relative', overflow: 'hidden', backgroundColor: 'rgba(15, 23, 42, 0.4)' }}>
                                        <SimpleGraph 
                                            nodes={graphData?.nodes || []} 
                                            edges={graphData?.edges || []}
                                            onNodeSelect={setSelectedNode}
                                        />
                                    </div>
                                </div>
                                {selectedNode && (
                                    <div style={{
                                        width: '280px', borderLeft: '1px solid rgba(255, 105, 180, 0.1)', backgroundColor: 'rgba(20, 10, 30, 0.6)',
                                        display: 'flex', flexDirection: 'column', padding: '20px', backdropFilter: 'blur(15px)'
                                    }}>
                                        <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                                            <h3 style={{margin:0, color:'#fff'}}>{selectedNode.label}</h3>
                                            <button onClick={() => setSelectedNode(null)} style={{background:'none',border:'none',color:'rgba(255,255,255,0.5)',cursor:'pointer'}}><X size={18} /></button>
                                        </div>
                                        <div style={{fontSize:'11px', color:'rgba(255,255,255,0.4)'}}>ID: {selectedNode.id}</div>
                                        <div style={{fontSize:'12px', color:'#f472b6', fontWeight:'600'}}>Type: {selectedNode.group}</div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                <RecordEditor 
                    editingRecord={editingRecord}
                    isCreating={isCreating}
                    editorForm={editorForm}
                    setEditorForm={setEditorForm}
                    onCancel={() => setEditingRecord(null)}
                    onSave={handleSaveRecord}
                />

                <EdgeDetailModal 
                    detailEdge={detailEdge}
                    onClose={() => setDetailEdge(null)}
                />
            </div>
        </div>
    );
};

export default DataViewer;
