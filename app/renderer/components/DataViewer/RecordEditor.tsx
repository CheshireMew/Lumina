import React from 'react';
import { X } from 'lucide-react';

interface RecordEditorProps {
    editingRecord: any;
    isCreating: boolean;
    editorForm: any;
    setEditorForm: (val: any) => void;
    onCancel: () => void;
    onSave: () => void;
}

export const RecordEditor: React.FC<RecordEditorProps> = ({
    editingRecord,
    isCreating,
    editorForm,
    setEditorForm,
    onCancel,
    onSave
}) => {
    if (!editingRecord) return null;

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
                    <h3 style={{margin:0, color:'#f472b6'}}>{isCreating ? 'Create New Record' : 'Edit Record'}</h3>
                    <button onClick={onCancel} style={{background:'none', border:'none', color:'rgba(255,255,255,0.5)', cursor:'pointer'}}><X size={20}/></button>
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
                        onClick={onCancel}
                        style={{
                            padding:'8px 16px', borderRadius:'8px', background:'transparent', border:'1px solid rgba(255,255,255,0.2)', color:'rgba(255,255,255,0.8)', cursor:'pointer'
                        }}
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={onSave}
                        style={{
                            padding:'8px 24px', borderRadius:'8px', background:'linear-gradient(135deg, #ec4899, #8b5cf6)', border:'none', color:'white', fontWeight:'600', cursor:'pointer'
                        }}
                    >
                        Save
                    </button>
                </div>
            </div>
        </div>
    );
};
