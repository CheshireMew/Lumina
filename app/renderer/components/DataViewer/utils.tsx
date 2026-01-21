import React from 'react';
import { CheckCircle, Clock } from 'lucide-react';

export const formatCellValue = (key: string, value: any) => {
    if (value === null || value === undefined) return <span style={{color:'rgba(255,255,255,0.3)'}}>-</span>;
    
    // 1. Time formatting
    // 1. Time formatting - STRICTER check
    const isLikelyDate = key === 'created_at' || key === 'updated_at' || key === 'timestamp' || key === 'date' || (key.endsWith('_at') && !key.includes('hit_at'));
    if (isLikelyDate) {
        try {
            return <span style={{fontSize:'12px', color:'#9ca3af'}}>{new Date(value).toLocaleString()}</span>;
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

export const getOrderedColumns = (data: any[]) => {
    if (!data || data.length === 0) return [];
    
    // Collect ALL unique keys from ALL rows (NoSQL schema flexibility)
    const keySet = new Set<string>();
    data.forEach(row => {
        if (row && typeof row === 'object') {
            Object.keys(row).forEach(k => keySet.add(k));
        }
    });
    const allKeys = Array.from(keySet);

    // Define priority: agent_id, narrative, then others
    const priority = ['agent_id', 'narrative', 'content', 'role', 'timestamp', 'created_at', 'id'];
    
    const ordered: string[] = [];
    // 1. Add priority keys if they exist
    priority.forEach(key => {
        if (allKeys.includes(key)) {
            ordered.push(key);
        }
    });
    // 2. Add remaining keys (excluding hidden ones)
    const hiddenCols = ['id', 'last_hit_at', 'embedding', 'vector'];
    allKeys.forEach(key => {
        if (!priority.includes(key) && !ordered.includes(key) && !hiddenCols.includes(key)) {
            ordered.push(key);
        }
    });
    // 3. Final cleanup: Remove hidden columns from the result, even if they were in priority
    return ordered.filter(col => !hiddenCols.includes(col));
};
