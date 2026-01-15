export interface HistoryEvent {
    id: string;
    event_type?: string;
    content: string;
    timestamp: string;
    role?: string;
    name?: string;
}

export interface Fact {
    id: string;
    content: string;
    importance: number;
    emotion: string;
    created_at: string;
    channel?: string;
    source_name?: string;
}

export interface GraphEdge {
    source: string;
    target: string;
    label: string;
}

export interface MemoryData {
    facts: Fact[];
    graph: {
        nodes: any[];
        edges: GraphEdge[];
    };
    user_facts?: Fact[];
    history?: HistoryEvent[];
}

export interface ProcessingStatus {
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
