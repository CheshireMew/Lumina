import React from "react";
import { CheckCircle, Clock } from "lucide-react";

export interface TableViewMeta {
    title: string;
    sidebarLabel: string;
    sidebarHint: string;
    singular: string;
    subtitle: string;
    countLabel: string;
    technicalName: string;
}

const fallbackTableMeta: TableViewMeta = {
    title: "Data Records",
    sidebarLabel: "Data Records",
    sidebarHint: "Stored rows",
    singular: "Record",
    subtitle: "Inspectable storage rows.",
    countLabel: "records",
    technicalName: "table",
};

export const tableViewMeta: Record<string, TableViewMeta> = {
    conversation_turns: {
        title: "History Log",
        sidebarLabel: "History Log",
        sidebarHint: "Raw conversations",
        singular: "History Turn",
        subtitle: "Complete conversation turns before memory extraction.",
        countLabel: "turns",
        technicalName: "conversation_turns",
    },
    memory_items: {
        title: "Long-term Memory",
        sidebarLabel: "Long-term Memory",
        sidebarHint: "AI recall source",
        singular: "Memory Item",
        subtitle: "Durable facts and preferences available for AI recall.",
        countLabel: "items",
        technicalName: "memory_items",
    },
    memory_consolidation_jobs: {
        title: "Consolidation Queue",
        sidebarLabel: "Consolidation",
        sidebarHint: "History to memory",
        singular: "Consolidation Job",
        subtitle: "Extraction work that turns history into memory items.",
        countLabel: "jobs",
        technicalName: "memory_consolidation_jobs",
    },
};

const tableColumnOrder: Record<string, string[]> = {
    conversation_turns: [
        "narrative",
        "user_message",
        "assistant_message",
        "processed_at",
        "created_at",
        "session_id",
        "user_id",
        "character_id",
    ],
    memory_items: [
        "content",
        "summary",
        "memory_type",
        "scope",
        "status",
        "importance",
        "confidence",
        "source_turn_ids",
        "created_at",
        "updated_at",
        "last_used_at",
        "user_id",
        "character_id",
    ],
    memory_consolidation_jobs: [
        "status",
        "turn_ids",
        "error",
        "created_at",
        "updated_at",
        "user_id",
        "character_id",
    ],
};

const columnLabels: Record<string, string> = {
    id: "ID",
    narrative: "Conversation",
    user_message: "User Said",
    assistant_message: "Assistant Said",
    processed_at: "Memory Status",
    created_at: "Created",
    updated_at: "Updated",
    last_used_at: "Last Used",
    session_id: "Session",
    user_id: "User",
    character_id: "Character",
    content: "Memory",
    summary: "Summary",
    memory_type: "Type",
    scope: "Scope",
    status: "Status",
    importance: "Importance",
    confidence: "Confidence",
    source_turn_ids: "Source Turns",
    turn_ids: "Turns",
    error: "Error",
    name: "Name",
    type: "Type",
};

const hiddenColumns = new Set(["id", "embedding", "vector", "metadata"]);

const statusColors: Record<string, { color: string; background: string; border: string }> = {
    active: {
        color: "#a7f3d0",
        background: "rgba(5, 150, 105, 0.18)",
        border: "rgba(5, 150, 105, 0.35)",
    },
    pending: {
        color: "#fde68a",
        background: "rgba(180, 83, 9, 0.18)",
        border: "rgba(180, 83, 9, 0.35)",
    },
    completed: {
        color: "#a7f3d0",
        background: "rgba(5, 150, 105, 0.18)",
        border: "rgba(5, 150, 105, 0.35)",
    },
    failed: {
        color: "#fecaca",
        background: "rgba(220, 38, 38, 0.18)",
        border: "rgba(220, 38, 38, 0.35)",
    },
};

export const getTableViewMeta = (tableName: string | null | undefined): TableViewMeta => {
    if (!tableName) {
        return fallbackTableMeta;
    }

    return tableViewMeta[tableName] || {
        ...fallbackTableMeta,
        title: tableName,
        sidebarLabel: tableName,
        technicalName: tableName,
    };
};

export const getColumnLabel = (key: string) => {
    return columnLabels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const renderStatusPill = (label: string, palette = statusColors.pending) => (
    <span
        style={{
            color: palette.color,
            background: palette.background,
            padding: "2px 7px",
            borderRadius: "12px",
            fontSize: "11px",
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            width: "fit-content",
            border: `1px solid ${palette.border}`,
            whiteSpace: "nowrap",
        }}
    >
        {label}
    </span>
);

export const formatCellValue = (key: string, value: any) => {
    if (key === "processed_at") {
        return value ?
            <span style={{color:"#a7f3d0", background:"rgba(5, 150, 105, 0.2)", padding:"2px 6px", borderRadius:"12px", fontSize:"11px", display:"flex", alignItems:"center", gap:"4px", width:"fit-content", border:"1px solid rgba(5, 150, 105, 0.4)", whiteSpace: "nowrap"}}>
                <CheckCircle size={10} /> Extracted
            </span> :
            <span style={{color:"#fde68a", background:"rgba(180, 83, 9, 0.2)", padding:"2px 6px", borderRadius:"12px", fontSize:"11px", display:"flex", alignItems:"center", gap:"4px", width:"fit-content", border:"1px solid rgba(180, 83, 9, 0.4)", whiteSpace: "nowrap"}}>
                <Clock size={10} /> Raw
            </span>;
    }

    if (value === null || value === undefined || value === "") return <span style={{color:"rgba(255,255,255,0.3)"}}>-</span>;

    const isLikelyDate = key === "created_at" || key === "updated_at" || key === "timestamp" || key === "date" || key.endsWith("_at");
    if (isLikelyDate) {
        try {
            return <span style={{fontSize:"12px", color:"#9ca3af", whiteSpace: "nowrap"}}>{new Date(value).toLocaleString()}</span>;
        } catch (e) { return value; }
    }

    if (key === "status" && typeof value === "string") {
        const normalized = value.toLowerCase();
        return renderStatusPill(value, statusColors[normalized] || statusColors.pending);
    }

    if ((key === "importance" || key === "confidence" || key === "weight") && typeof value === "number") {
        return <span style={{ color: "#e9d5ff", fontVariantNumeric: "tabular-nums" }}>{value.toFixed(2)}</span>;
    }

    if (Array.isArray(value)) {
        return (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px", minWidth: "140px" }}>
                {value.length === 0 ? (
                    <span style={{color:"rgba(255,255,255,0.3)"}}>-</span>
                ) : value.map((item, index) => (
                    <span
                        key={`${String(item)}-${index}`}
                        title={String(item)}
                        style={{
                            border: "1px solid rgba(165, 180, 252, 0.22)",
                            color: "#c7d2fe",
                            background: "rgba(99, 102, 241, 0.12)",
                            borderRadius: "10px",
                            padding: "2px 6px",
                            fontSize: "11px",
                            maxWidth: "120px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                        }}
                    >
                        {String(item)}
                    </span>
                ))}
            </div>
        );
    }

    if (key === "id" && typeof value === "string") {
        return value.includes(":") ? <span title={value} style={{fontFamily:"monospace", color:"#f472b6"}}>{value.split(":")[1]}</span> : value;
    }

    if (typeof value === "object") {
        return (
            <div style={{maxHeight:"72px", overflowY:"auto", fontSize:"11px", fontFamily:"monospace", whiteSpace:"pre-wrap", color:"rgba(255,255,255,0.7)", minWidth: "180px"}}>
                {JSON.stringify(value, null, 2)}
            </div>
        );
    }

    if (typeof value === "string" && value.length > 50) {
        return <div style={{ minWidth: "240px", maxWidth: "420px", whiteSpace: "pre-wrap", color:"#fff", lineHeight: 1.55 }}>{value}</div>;
    }

    return String(value);
};

export const getOrderedColumns = (data: any[], tableName?: string | null) => {
    if (!data || data.length === 0) return [];

    const keySet = new Set<string>();
    data.forEach(row => {
        if (row && typeof row === "object") {
            Object.keys(row).forEach(k => keySet.add(k));
        }
    });
    const allKeys = Array.from(keySet);
    const priority = tableName ? tableColumnOrder[tableName] || [] : [];
    
    const ordered: string[] = [];
    priority.forEach(key => {
        if (allKeys.includes(key)) {
            ordered.push(key);
        }
    });

    allKeys.forEach(key => {
        if (!ordered.includes(key) && !hiddenColumns.has(key)) {
            ordered.push(key);
        }
    });

    return ordered.filter(col => !hiddenColumns.has(col));
};
