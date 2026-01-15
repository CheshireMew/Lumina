
import React from 'react';
import { GraphEdge } from './types';

interface MemoryGraphProps {
    edges: GraphEdge[];
}

const MemoryGraph: React.FC<MemoryGraphProps> = ({ edges }) => {
    if (!edges || edges.length === 0) {
        return <div style={{color: '#666', textAlign: 'center'}}>No synaptic connections (graph) found yet. Start dreaming to weave the web!</div>;
    }

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '15px' }}>
            {edges.map((edge, i) => (
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
        </div>
    );
};

export default MemoryGraph;
