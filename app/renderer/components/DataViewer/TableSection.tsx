import React from 'react';
import { Braces, RefreshCw, Table as TableIcon, Plus, Edit, Trash2, Sparkles } from 'lucide-react';
import { formatCellValue, getOrderedColumns } from './utils';

interface TableSectionProps {
    selectedTable: string | null;
    tableData: any[];
    loading: boolean;
    graphData: any;
    onRefreshTable: () => void;
    onRefreshGraph: () => void;
    onCreateRecord: () => void;
    onEditRecord: (row: any) => void;
    onDeleteRecord: (id: any) => void;
    onEdgeClick: (edge: any) => void;
}

export const TableSection: React.FC<TableSectionProps> = ({
    selectedTable,
    tableData,
    loading,
    graphData,
    onRefreshTable,
    onRefreshGraph,
    onCreateRecord,
    onEditRecord,
    onDeleteRecord,
    onEdgeClick
}) => {
    const columns = getOrderedColumns(tableData);

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {selectedTable === 'knowledge_facts' ? (
                // Special View for Knowledge Facts Text
                <div style={{flex:1, overflow:'auto', padding:'25px'}}>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <h3 style={{display:'flex', alignItems:'center', gap:'10px', margin:0, color:'#93c5fd'}}>
                            <Braces size={22} /> Knowledge Facts (Text View)
                        </h3>
                        <button 
                            onClick={onRefreshGraph} 
                            style={{
                                padding:'8px 16px', background:'linear-gradient(135deg, #3b82f6, #2563eb)', 
                                color:'white', border:'none', borderRadius:'8px', cursor:'pointer', 
                                display:'flex', alignItems:'center', gap:'6px',
                                boxShadow: '0 4px 10px rgba(37, 99, 235, 0.3)', fontWeight:'600', fontSize:'13px'
                            }}>
                            <RefreshCw size={14} /> Refresh Data
                        </button>
                    </div>
                    {loading ? (
                        <div style={{color:'#60a5fa', display:'flex', alignItems:'center', gap:'8px', fontSize:'14px'}}>
                            <RefreshCw className="spin" size={18} /> Retrieving neural connections...
                        </div>
                    ) : (
                        <div style={{display:'flex', flexDirection:'column', gap:'12px'}}>
                            {graphData?.edges?.map((edge: any, idx: number) => (
                                <div 
                                    key={idx} 
                                    onClick={() => onEdgeClick(edge)}
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
                                        {graphData.nodes.find((n: any) => n.id === edge.from)?.label || edge.from}
                                    </div>
                                    <div style={{
                                        padding:'4px 10px', borderRadius:'20px', background:'rgba(59, 130, 246, 0.2)', 
                                        fontSize:'11px', color:'#93c5fd', textTransform:'uppercase', fontWeight:'700',
                                        border: '1px solid rgba(59, 130, 246, 0.3)'
                                    }}>
                                        {edge.label}
                                    </div>
                                    <div style={{fontWeight:'600', color:'#e2e8f0', flex:1}}>
                                        {graphData.nodes.find((n: any) => n.id === edge.to)?.label || edge.to}
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
                <button onClick={onRefreshTable} style={{ cursor: 'pointer', background: 'none', border: 'none', color:'#f472b6', marginRight:'10px' }}>
                            <RefreshCw size={18} />
                        </button>
                        <button 
                            onClick={onCreateRecord}
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
                                                    onClick={() => onEditRecord(row)}
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
                                                    onClick={() => onDeleteRecord(row.id)}
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
    );
};
