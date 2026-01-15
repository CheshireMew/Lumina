export interface TableInfo {
    name: string;
    info: string;
}

export interface QueryResult {
    status: string;
    result?: any[];
    error?: string;
}

export interface TableRow {
    id: any;
    [key: string]: any;
}

export interface DataViewerProps {
    isOpen: boolean;
    onClose: () => void;
    activeCharacterId?: string | null;
    dataSource?: string;
}
