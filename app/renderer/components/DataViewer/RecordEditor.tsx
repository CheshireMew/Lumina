import React from 'react';
import { X } from 'lucide-react';

import { getColumnLabel, getTableViewMeta } from './utils';

interface RecordEditorProps {
    selectedTable: string | null;
    editingRecord: any;
    isCreating: boolean;
    editorForm: any;
    setEditorForm: (val: any) => void;
    onCancel: () => void;
    onSave: () => void | Promise<void>;
    isSaving: boolean;
}

export const RecordEditor: React.FC<RecordEditorProps> = ({
    selectedTable,
    editingRecord,
    isCreating,
    editorForm,
    setEditorForm,
    onCancel,
    onSave,
    isSaving,
}) => {
    if (!editingRecord) return null;

    const meta = getTableViewMeta(selectedTable);
    const textAreaFields = new Set([
        'content',
        'summary',
        'narrative',
        'user_message',
        'assistant_message',
        'error',
    ]);

    return (
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
                    <div>
                        <h3 style={{margin:0, color:'#f472b6'}}>
                            {isCreating ? `Create ${meta.singular}` : `Edit ${meta.singular}`}
                        </h3>
                        <div style={{fontSize:'12px', color:'rgba(255,255,255,0.45)', marginTop:'4px'}}>
                            {meta.technicalName}
                        </div>
                    </div>
                    <button onClick={onCancel} style={{background:'none', border:'none', color:'rgba(255,255,255,0.5)', cursor:'pointer'}}><X size={20}/></button>
                </div>
                
                <div style={{display:'flex', flexDirection:'column', gap:'15px'}}>
                    {Object.keys(isCreating ? editorForm : editingRecord).map(key => (
                        (key !== 'id' && key !== 'created_at' && key !== 'embedding' && key !== 'vector') && (
                            <div key={key}>
                                <label style={{display:'block', fontSize:'12px', color:'rgba(255,255,255,0.6)', marginBottom:'5px'}}>
                                    {getColumnLabel(key)}
                                </label>
                                {textAreaFields.has(key) ? (
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
                                        onChange={e => {
                                            let val: any = e.target.value;
                                            if (editingRecord && typeof editingRecord[key] === 'object') {
                                                try { val = JSON.parse(e.target.value); } catch {}
                                            }
                                            setEditorForm({...editorForm, [key]: val})
                                        }}
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
                        onClick={onCancel}
                        disabled={isSaving}
                        style={{
                            padding:'8px 16px', borderRadius:'8px', background:'transparent', border:'1px solid rgba(255,255,255,0.2)', color:'rgba(255,255,255,0.8)', cursor: isSaving ? 'wait' : 'pointer', opacity: isSaving ? 0.7 : 1
                        }}
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={() => {
                            void onSave();
                        }}
                        disabled={isSaving}
                        style={{
                            padding:'8px 24px', borderRadius:'8px', background:'linear-gradient(135deg, #ec4899, #8b5cf6)', border:'none', color:'white', fontWeight:'600', cursor: isSaving ? 'wait' : 'pointer', opacity: isSaving ? 0.72 : 1
                        }}
                    >
                        {isSaving ? 'Saving...' : 'Save'}
                    </button>
                </div>
            </div>
        </div>
    );
};
